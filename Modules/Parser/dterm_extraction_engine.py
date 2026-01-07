# -*- coding: utf-8 -*-
"""
D-Term Extraction Engine - Hybrid OCR + Gemini API
D조건(도착 기준) 증빙 문서에서 '도착일(Arrival Date)'과 '문서 유형'을 추출하는 전용 엔진
기존 SmartExtractionEngine을 기반으로 하되, D조건 요구사항에 맞춰 독립적으로 동작함.
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai

# Tesseract 경로 설정 (환경에 따라 수정 가능)
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except:
    print("⚠️ D-Term Engine: Tesseract 경로 설정 오류")

# OCR 임계값
OCR_THRESHOLD = 50  # 텍스트가 이 값보다 적으면 스캔 PDF로 간주

class DtermExtractionEngine:
    def __init__(self):
        """초기화"""
        self.gemini_model = None
        self.semaphore = asyncio.Semaphore(5)  # 병렬 처리 제한
        self._load_configs()
    
    def _load_configs(self):
        """설정 로드 및 Gemini 모델 초기화"""
        try:
            # 프로젝트 루트를 Python 경로에 추가
            import sys
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # Gemini API 키 로드
            from Config.api_config import GEMINI_API_KEY
            genai.configure(api_key=GEMINI_API_KEY)
            
            # 최신 시스템 지시사항
            SYSTEM_INSTRUCTION = """
            You are an expert in Logistics and Trade Finance documents.
            Your specialization is identifying "Proof of Arrival" or "Proof of Delivery" for D-Term (DAP, DDP, DAT) transactions.
            Your goal is to find the EXACT date when the cargo arrived at the destination or was received by the consignee.
            Output must be in pure JSON format.
            """
            
            try:
                # SmartExtractionEngine과 동일하게 Gemini 2.0 모델 사용
                self.gemini_model = genai.GenerativeModel(
                    model_name='models/gemini-2.0-flash',
                    system_instruction=SYSTEM_INSTRUCTION
                )
            except Exception as e:
                print(f"❌ Model initialization error: {e}")
                raise
            
            print("✅ D-Term Engine: Gemini API initialized")
            
        except Exception as e:
            print(f"❌ D-Term Engine initialization failed: {e}")
            raise

    def high_quality_ocr(self, pdf_path: str, page_num: int) -> str:
        """고품질 OCR (전체 페이지) - 스캔 문서용"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            text = pytesseract.image_to_string(img, lang='eng+kor')
            return text
        except Exception as e:
            print(f"❌ OCR Error: {e}")
            return ""

    async def extract_with_gemini_vision_async(self, pdf_path: str, filename: str, context: Dict = None) -> Dict:
        """Gemini Vision API (이미지 분석) - 텍스트 추출 실패 시 Fallback"""
        print(f"👁️ Vision Fallback Triggered for {filename}")
        try:
            # 1. PDF 첫 페이지를 이미지로 변환
            doc = fitz.open(pdf_path)
            if len(doc) < 1: return {}
            
            # 중요: 물류 문서는 1~2페이지에 핵심 정보가 있음 (특히 2페이지 스케줄)
            images = []
            pages_to_check = min(len(doc), 2)
            
            for i in range(pages_to_check):
                page = doc[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)) # 고해상도
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
            
            doc.close()
            
            # Context Prep (Directive A: Flexible Matching)
            context_str = ""
            if context:
                context_str = f"""
                **Context Validation Keys:**
                - Primary: TC No ({context.get('tc', 'N/A')}), SO No ({context.get('so', 'N/A')}), Invoice ({context.get('invoice', 'N/A')})
                - Secondary (Use if Primary missing): 
                  - Registrant Name: {context.get('registrant', 'N/A')}
                  - Sales Person: {context.get('sales_person', 'N/A')} 
                  - Customer: {context.get('customer_desc', 'N/A')}
                """

            prompt = [
                f"""
                Analyze these document images (Logistics Documents).
                Filename: {filename}
                
                {context_str}
                
                **Objective**: Identify the **FINAL ARRIVAL DATE** of the cargo at the Ultimate Destination.
                
                **Rule 1: Flexible Matching (Directive A)**
                - If TC/SO/Invoice are not found, check the "Secondary" keys (Registrant, Customer). 
                - If the filename ({filename}) contains the Slip ID or partial TC, consider it a MATCH.
                
                **Rule 2: Final Port Rule (Directive B)**
                - **Crucial**: In a Vessel Schedule or Tracking Report, look for the **List of Ports**.
                - Select the date for the **LAST Port of Discharge** (Ultimate POD) in the sequence.
                - Ignore "Pol (Port of Loading)" or intermediate transshipment ports. 
                - If multiple "Discharging" dates exist, pick the LATEST one.
                
                **Rule 3: Robust Parsing (Directive C)**
                - Extract ONLY the date part (YYYY-MM-DD).
                - STRIP extraneous text like "1000LT", "BERTHED", "Completed", "ATA".
                - Example: "2025/11/22 0642LT" -> "2025-11-22"
                - DO NOT return "null" if a valid date exists in a messy format.
                
                **Rule 4: Reasoning (Directive D - Korean Output)**
                - You MUST list ALL ports found in the schedule and explain selection logic in **KOREAN**.
                - Format: "발견된 항구: [Port List]. [Reason for Selection]에 따라 [Date]를 선택함."
                - Example: "스케줄상 부산, 싱가포르, 로테르담 발견. 최종 목적지인 로테르담의 하역일(12/02)을 선택함."
                
                **Output JSON**:
                {{
                    "verification_status": "Perfect Match" | "Match - Date Only" | "Mismatch" | "Unidentified",
                    "matched_identifiers": ["List found keys"],
                    "extracted_arrival_date": "YYYY-MM-DD",
                    "date_confidence": 0.0 to 1.0,
                    "doc_category": "Document Type",
                    "reasoning": "Reasoning in Korean (Simple & Clear)."
                }}
                """
            ]
            
            response = await self.gemini_model.generate_content_async(
                prompt + images, 
                generation_config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            if isinstance(result, list): result = result[0]
            
            return result
            
        except Exception as e:
            print(f"❌ Vision API Error: {e}")
            return {
                "verification_status": "Error",
                "reasoning": f"Vision Error: {str(e)}"
            }

    async def extract_with_gemini_async(self, ocr_text: str, filename: str, context: Dict = None) -> Dict:
        """Gemini API로 도착일 및 문서 유형 추출 (Context-Aware)"""
        if not self.gemini_model:
            raise Exception("Gemini API not initialized")
            
        # Context Injection (Directive A)
        context_str = ""
        if context:
            context_str = f"""
            **Context Validation Keys:**
            - Primary: TC No ({context.get('tc', 'N/A')}), SO No ({context.get('so', 'N/A')}), Invoice ({context.get('invoice', 'N/A')})
            - Secondary (Backup): Registrant ({context.get('registrant', 'N/A')}), Customer ({context.get('customer_desc', 'N/A')})
            """

        prompt = f"""
        Analyze the following text extracted from a logistics document ("{filename}").
        
        {context_str}
        
        **Objective**: Identify the **FINAL ARRIVAL DATE** of the cargo at the Ultimate Destination.
        
        **Advanced Parsing Rules (Directives)**:
        
        1.  **Flexible Matching (Directive A)**:
            - If Primary Keys (TC/SO) are missing, validate using Secondary Keys or the Filename itself.
            - If matching is ambiguous but the document clearly shows arrival info, mark as "Match - Date Only".
            
        2.  **Final Port Rule (Directive B)**:
            - **CRITICAL**: For Sea Freight, find the **Vessel Schedule**.
            - Identify the sequence of ports. The Arrival Date is the 'Discharged' or 'ATA' at the **LAST Port**.
            - IGNORE dates for 'Port of Loading' or 'Transshipment'.
            - Reference: "Commenced Discharging" > "ATA".
            
        3.  **Robust Parsing (Directive C)**:
            - Output format: YYYY-MM-DD
            - Clean up noise: Remove "1000LT", "BERTHED", time, or codes from the date string.
            - If the text says "22-Nov-2025", convert to "2025-11-22".
            
        4.  **Reasoning (Directive D - Korean Output)**:
            - Write the reasoning in **KOREAN**.
            - Be concise and clear. List found ports/dates and why the final date was chosen.
            - Example: "문서에서 부산, LA, 뉴욕 항구 발견. 최종 도착지인 뉴욕의 ATA(12/25)를 추출함."

        **JSON Output Format**:
        {{
            "verification_status": "Perfect Match" | "Match - Date Only" | "Mismatch" | "Unidentified",
            "matched_identifiers": ["List found keys"],
            "extracted_arrival_date": "YYYY-MM-DD",
            "date_confidence": 0.0 to 1.0,
            "doc_category": "Category Name",
            "evidence_text": "Quote the text that proves the date.",
            "reasoning": "Reasoning in Korean (Simple & Clear)."
        }}
        
        **Input Text:**
        {ocr_text[:14000]}
        """
        
        try:
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            
            if isinstance(result, list):
                result = result[0] if result else {}
                
            return result
            
        except Exception as e:
            print(f"❌ API Error: {e}")
            return {
                "verification_status": "Error",
                "extracted_arrival_date": None,
                "reasoning": str(e)
            }

    async def process_single_pdf_async(self, pdf_path: str, slip_id: str, context: Dict = None) -> Dict:
        """단일 PDF 처리 (Text -> Low Confidence -> Vision Fallback)"""
        filename = os.path.basename(pdf_path)
        print(f"📄 D-Term Processing: {filename}")
        
        try:
            # 1. 문서 텍스트 추출 (OCR)
            doc = fitz.open(pdf_path)
            pages_to_read = min(len(doc), 3) # 첫 3페이지 분석 (스케줄 등 확인)
            full_text = ""
            
            for i in range(pages_to_read):
                page = doc[i]
                text = page.get_text()
                if len(text.strip()) < OCR_THRESHOLD:
                    text = self.high_quality_ocr(pdf_path, i)
                full_text += f"\n--- Page {i+1} ---\n{text}"
            
            doc.close()
            
            # 2. Text-based Gemini Analysis
            extraction = await self.extract_with_gemini_async(full_text, filename, context)
            
            # 3. Vision Fallback Check
            # 조건: 날짜가 없거나(Unidentified), 신뢰도가 낮거나(0.8 미만), 문서 유형이 Unknown인 경우
            security_check = extraction.get("verification_status", "Unidentified")
            confidence = extraction.get("date_confidence", 0.0)
            
            if security_check == "Unidentified" or confidence < 0.8:
                print(f"⚠️ Low confidence ({confidence}) for {filename}. Attempting Vision Fallback...")
                vision_result = await self.extract_with_gemini_vision_async(pdf_path, filename, context)
                
                # Vision 결과가 더 좋으면(날짜가 있거나 신뢰도가 높으면) 교체
                v_date = vision_result.get("extracted_arrival_date")
                v_conf = vision_result.get("date_confidence", 0.0)
                
                if v_date and v_conf >= confidence:
                    print(f"✅ Vision Result Accepted for {filename} (Date: {v_date}, Conf: {v_conf})")
                    extraction = vision_result
                    extraction['method'] = 'vision'
                else:
                    print(f"ℹ️ Vision result not better. Keeping text result.")
            
            # 4. 결과 포맷팅
            return {
                "slip_id": slip_id,
                "file_name": filename,
                "document_type": extraction.get("doc_category", "Unknown"),
                "arrival_date": extraction.get("extracted_arrival_date"),
                "date_confidence": extraction.get("date_confidence", 0.0),
                "reasoning": extraction.get("reasoning", ""),
                "evidence_text": extraction.get("evidence_text", ""),
                "verification_status": extraction.get("verification_status", "Unidentified"),
                "matched_identifiers": extraction.get("matched_identifiers", []),
                "method": extraction.get("method", "text")
            }
            
        except Exception as e:
            print(f"❌ File Processing Error: {e}")
            return {
                "slip_id": slip_id, 
                "file_name": filename, 
                "error": str(e)
            }

    async def process_project_dterm_async(self, project_id: str, split_dir: str, target_ids: List[str] = None, progress_callback=None, context_map: Dict = None) -> List[Dict]:
        """프로젝트 전체 D조건 증빙 처리"""
        # split_dir 구조: slip_id 폴더 하위 파일들
        
        tasks = []
        files_to_process = []
        
        # 1. 파일 수집
        if os.path.exists(split_dir):
            for item in os.listdir(split_dir):
                item_path = os.path.join(split_dir, item)
                
                # 폴더인 경우 (slip_id)
                if os.path.isdir(item_path):
                    slip_id = item
                    if target_ids and slip_id not in target_ids:
                        continue
                        
                    for f in os.listdir(item_path):
                        if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                            files_to_process.append((os.path.join(item_path, f), slip_id))
                            
                # 파일인 경우 (파일명 매칭)
                elif os.path.isfile(item_path) and item.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    # 파일명에서 slip_id 유추 시도
                    # 로직 개선: 여기서는 단순히 파일명 매칭만 시도하지만, 
                    # Step 3 Loop에서 context map을 순회하며 파일을 찾는 방식이 더 정확할 수 있음.
                    # 현재 구조 유지하되 context 전달.
                    match = re.match(r'^(\d{8,})_', item)
                    slip_id = match.group(1) if match else "Unknown"
                    
                    # context_map에 slip_id가 있다면 유효한 것으로 간주
                    if slip_id == "Unknown" and context_map:
                         # 파일명 전체에서 SID 검색 (보완)
                         for known_sid in context_map.keys():
                             if known_sid in item:
                                 slip_id = known_sid
                                 break
                    
                    if target_ids and slip_id not in target_ids:
                        continue
                        
                    files_to_process.append((item_path, slip_id))

        total_files = len(files_to_process)
        print(f"🚀 D-Term Engine: Found {total_files} files to process with Context-Aware Logic")
        
        for idx, (fpath, slip_id) in enumerate(files_to_process):
            if progress_callback:
                progress_callback(idx, total_files, slip_id, f"Queued {os.path.basename(fpath)}")
            
            # Context Lookup
            ctx = context_map.get(slip_id) if context_map else None
            tasks.append(self.process_single_pdf_async(fpath, slip_id, context=ctx))
            
        # 2. 병렬 실행
        results = []
        chunk_size = 5 # Semaphore 제한과 별도로 청크 처리
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i+chunk_size]
            chunk_results = await asyncio.gather(*chunk)
            results.extend(chunk_results)
            
            # Progress Update
            if progress_callback:
                progress_callback(min(i+chunk_size, total_files), total_files, "Batch", "Processing...")
                
        return results
