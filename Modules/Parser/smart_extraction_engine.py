# -*- coding: utf-8 -*-
"""
Smart Extraction Engine - Hybrid OCR + Gemini API
하이브리드 방식으로 PDF에서 데이터 추출:
1. PyMuPDF로 텍스트 PDF 빠른 처리
2. 스캔 PDF는 Tesseract OCR
3. BL, Invoice만 선택적 처리
4. Gemini API로 필드 추출 + 신뢰도 계산
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

# Tesseract 경로 설정
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except:
    print("⚠️ Tesseract 경로 설정 오류")

# OCR 임계값
OCR_THRESHOLD = 100  # 텍스트가 이 값보다 적으면 스캔 PDF로 간주

# 문서 타입 검출 패턴 (pdf_splitter.py에서 가져옴)
DOCUMENT_PATTERNS = {
    'BL': [  # Bill of Lading
        (r'BILL\s*OF\s*LADING', 100),
        (r'WAYBILL', 100),
        (r'MULTIMODAL\s*TRANSPORT', 100),
        (r'SURRENDER', 95),
        (r'TELEX\s*RELEASE', 95),
        (r'PORT\s*OF\s*LOADING', 60),
        (r'PORT\s*OF\s*DISCHARGE', 60),
        (r'CLEAN\s*ON\s*BOARD', 70),
        (r'FREIGHT\s*PREPAID', 60),
    ],
    'INVOICE': [  # Commercial Invoice
        (r'COMMERCIAL\s*INVOICE', 100),
        (r'PROFORMA\s*INVOICE', 100),
        (r'INVOICE\s*NO', 80),
    ],
    'PACKING_LIST': [  # Packing List (필터링용)
        (r'PACKING\s*LIST', 100),
        (r'DETAIL\s*OF\s*PACKING', 90),
    ],
}


class SmartExtractionEngine:
    def __init__(self):
        """초기화"""
        self.gemini_model = None
        self.extraction_config = None
        self.data_normalizer = None
        self._load_configs()
    
    def _load_configs(self):
        """설정 파일 로드"""
        try:
            # 프로젝트 루트를 Python 경로에 추가
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # Gemini API 키 로드
            from Config.api_config import GEMINI_API_KEY
            genai.configure(api_key=GEMINI_API_KEY)
            
            # 모델 선택 (사용 가능한 모델 확인됨)
            GEMINI_MODEL_NAME = 'models/gemini-2.5-flash'
            
            try:
                self.gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
                # 간단한 테스트
                test_response = self.gemini_model.generate_content("Hello")
                if test_response and test_response.text:
                    print(f"✅ Gemini API 초기화 완료 (모델: {GEMINI_MODEL_NAME})")
                else:
                    raise Exception("테스트 응답 없음")
            except Exception as e:
                print(f"⚠️ {GEMINI_MODEL_NAME} 실패: {e}")
                # 대체 모델 시도 (실제 사용 가능한 모델들)
                fallback_models = [
                    'models/gemini-2.0-flash',
                    'models/gemini-2.5-pro',
                    'models/gemini-2.0-flash-exp'
                ]
                model_loaded = False
                
                for fallback_model in fallback_models:
                    try:
                        print(f"   시도 중: {fallback_model}")
                        self.gemini_model = genai.GenerativeModel(fallback_model)
                        test_response = self.gemini_model.generate_content("Hello")
                        if test_response and test_response.text:
                            print(f"✅ Gemini API 초기화 완료 (대체 모델: {fallback_model})")
                            model_loaded = True
                            break
                    except Exception as fb_error:
                        print(f"   ❌ {fallback_model} 실패: {fb_error}")
                        continue
                
                if not model_loaded:
                    print("\n💡 해결 방법:")
                    print("   1. Google Cloud Console에서 'Generative Language API' 활성화")
                    print("   2. https://console.cloud.google.com/apis/library")
                    print("   3. API 키 확인: Config/api_config.py")
                    raise Exception("모든 Gemini 모델 로드 실패")
        except ImportError:
            print("❌ Config/api_config.py 파일이 없습니다. api_config.example.py를 복사하여 API 키를 설정하세요.")
            raise
        except Exception as e:
            print(f"❌ Gemini API 초기화 실패: {e}")
            raise
        
        # 추출 필드 설정 로드
        try:
            config_path = Path(__file__).parent.parent.parent / 'Config' / 'extraction_config.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                self.extraction_config = json.load(f)
            print("✅ Extraction Config 로드 완료")
        except Exception as e:
            print(f"⚠️ extraction_config.json 로드 실패: {e}")
            self.extraction_config = {"default_fields": [], "optional_fields": [], "document_types": {}}
        
        # DataNormalizer 초기화
        try:
            from backend.logic.data_normalizer import DataNormalizer
            self.data_normalizer = DataNormalizer()
            print("✅ DataNormalizer 초기화 완료")
        except Exception as e:
            print(f"⚠️ DataNormalizer 초기화 실패: {e}")
            self.data_normalizer = None
    
    
    def detect_document_type(self, pdf_path: str, page_num: int) -> Tuple[str, str]:
        """
        문서 타입 감지 (파일명 절대 우선)
        """
        filename = os.path.basename(pdf_path).upper()
        
        # 1. 파일명 기반 분류 (가장 강력한 규칙)
        if "BILL_OF_LADING" in filename or "WAYBILL" in filename:
            print(f"   🎯 파일명 규칙 적용: BL ({filename})")
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            text = page.get_text()
            doc.close()
            return "BL", text
            
        if "COMMERCIAL_INVOICE" in filename or "INVOICE" in filename:
            # PACKING LIST는 제외
            if "PACKING" not in filename:
                print(f"   🎯 파일명 규칙 적용: INVOICE ({filename})")
                doc = fitz.open(pdf_path)
                page = doc[page_num]
                text = page.get_text()
                doc.close()
                return "INVOICE", text
        
        # 2. 파일명으로 식별 불가한 경우에만 내용 분석
        print(f"   ⚠️ 파일명 규칙 실패, 내용 분석 시도: {filename}")
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            text = page.get_text()
            doc.close()
            
            # 텍스트가 거의 없으면 스캔 문서
            if len(text.strip()) < OCR_THRESHOLD:
                return "SCAN_REQUIRED", text
            
            # Regex 패턴으로 문서 타입 검출 (점수 기반)
            text_upper = text.upper()
            best_type = None
            best_conf = 0.0
            
            for doc_type, patterns in DOCUMENT_PATTERNS.items():
                for pattern, score in patterns:
                    if re.search(pattern, text_upper):
                        if score > best_conf:
                            best_conf = score
                            best_type = doc_type
            
            # 신뢰도가 50 미만이면 UNKNOWN
            if best_conf < 50:
                return "UNKNOWN", text
            
            return best_type, text
                
        except Exception as e:
            print(f"⚠️ 문서 타입 검출 오류: {e}")
            return "UNKNOWN", ""
    
    
    def quick_ocr_for_keyword(self, pdf_path: str, page_num: int) -> Tuple[str, str]:
        """
        저해상도 OCR + Regex 패턴 검출 (1초)
        스캔 문서의 타입 빠르게 판별
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            # 저해상도 이미지 생성
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            
            # 빠른 OCR (첫 1000자)
            text = pytesseract.image_to_string(img, config='--psm 3')[:1000]
            
            # 패턴 매칭
            text_upper = text.upper()
            best_type = None
            best_conf = 0.0
            
            for doc_type, patterns in DOCUMENT_PATTERNS.items():
                for pattern, score in patterns:
                    if re.search(pattern, text_upper):
                        if score > best_conf:
                            best_conf = score
                            best_type = doc_type
            
            if best_conf < 50:
                return "UNKNOWN", text
            
            return best_type, text
            text = pytesseract.image_to_string(img, lang='eng+kor')
            
            return text
            
        except Exception as e:
            print(f"❌ 고품질 OCR 오류: {e}")
            return ""
    def high_quality_ocr(self, pdf_path: str, page_num: int) -> str:
        """
        고품질 OCR (전체 페이지) - 스캔 문서용
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            # 고해상도 이미지 생성 (300 DPI 이상 권장, zoom=2.0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            
            # 전체 OCR 실행 (한글+영어)
            text = pytesseract.image_to_string(img, lang='eng+kor')
            return text
            
        except Exception as e:
            print(f"❌ 고품질 OCR 오류: {e}")
            return ""

    async def extract_with_gemini_async(self, ocr_text: str, doc_type: str, extraction_fields: List[Dict]) -> Dict:
        """
        Gemini API로 필드 추출 (비동기) with 구조화된 요청
        """
        if not self.gemini_model:
            raise Exception("Gemini API가 초기화되지 않았습니다")
        
        # 문서 타입별 지시사항
        doc_instruction = ""
        if doc_type == "BL":
            doc_instruction = "이 문서는 선하증권(Bill of Lading)입니다. 선박 정보와 운송 정보를 중심으로 추출하세요."
        elif doc_type == "INVOICE":
            doc_instruction = "이 문서는 상업송장(Commercial Invoice)입니다. 금액과 거래 정보를 중심으로 추출하세요."
        
        # 필드별 프롬프트 및 예상 응답 구조 생성
        field_prompts = ""
        expected_fields_example = {}
        
        for field in extraction_fields:
            output_format = field.get('output_format', {})
            field_prompts += f"- {field['label']} ({field['name']}): {field['prompt']}\n"
            
            # 예상 응답 형태 생성
            if 'currency' in output_format:
                expected_fields_example[field['name']] = {"value": 50000, "currency": "USD"}
            elif 'unit' in output_format:
                expected_fields_example[field['name']] = {"value": 1000, "unit": "MT"}
            elif output_format.get('format') == 'date':
                expected_fields_example[field['name']] = {"value": "2025-06-30", "format": "date"}
            else:
                expected_fields_example[field['name']] = {"value": "추출된 값", "format": "text"}
        
        prompt = f"""
다음 {doc_type} 문서의 OCR 텍스트를 분석하세요:

{doc_instruction}

{ocr_text}

**추출할 필드:**
{field_prompts}

**응답 형식 (JSON only, 정확히 아래 구조를 따르세요):**
{{
  "document_type": "{doc_type}",
  "confidence": 0.95,
  "fields": {json.dumps(expected_fields_example, ensure_ascii=False, indent=2)},
  "field_confidence": {{
    {', '.join([f'"{f["name"]}": 0.95' for f in extraction_fields])}
  }},
  "notes": "추출 과정에서 특이사항이나 불확실한 부분"
}}

**중요 규칙:**
1. 모든 숫자에서 쉼표 제거 (예: "1,000" → 1000)
2. 날짜는 반드시 YYYY-MM-DD 형식으로 변환
3. 통화는 ISO 4217 코드 (USD, JPY, KRW) 사용
4. 단위는 표준 약어 (MT, KG, PCS) 사용
5. 값을 찾지 못하면 null 반환
6. 수량/금액은 반드시 {{"value": 숫자, "unit": "단위"}} 또는 {{"value": 숫자, "currency": "통화"}} 형식으로
7. 응답은 JSON만 반환 (다른 텍스트 없이)
8. 신뢰도(confidence)는 0.0 ~ 1.0 사이의 소수로 기재하세요. (0.0은 데이터가 아예 없을 때만 사용)
   - 매우 확실함: 0.9 ~ 1.0
   - 확실함: 0.7 ~ 0.9
   - 불확실함: 0.5 ~ 0.7
   - 추측: 0.1 ~ 0.5
"""
        
        try:
            # 비동기 호출
            response = await self.gemini_model.generate_content_async(prompt)
            
            # 토큰 사용량 계산
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count
            output_tokens = usage.candidates_token_count
            total_tokens = usage.total_token_count
            
            # 예상 비용 계산 (Gemini 1.5 Flash 기준)
            input_cost = (input_tokens / 1_000_000) * 0.075 * 1400
            output_cost = (output_tokens / 1_000_000) * 0.30 * 1400
            total_cost = input_cost + output_cost
            
            token_info = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_krw": round(total_cost, 2)
            }
            
            raw_text = response.text.strip()
            
            # Markdown JSON 블록 제거
            raw_text = raw_text.replace('```json', '').replace('```', '').strip()
            if raw_text.lower().startswith('json'):
                raw_text = raw_text[4:].strip()
            
            raw_result = json.loads(raw_text)
            raw_result['token_usage'] = token_info
            
            # ✅ DataNormalizer 적용
            if self.data_normalizer:
                normalized_result = self.data_normalizer.normalize_extraction_result(raw_result)
                normalized_result['token_usage'] = token_info
                return normalized_result
            else:
                return raw_result
            
        except Exception as e:
            print(f"❌ Gemini API 비동기 호출 오류: {e}")
            return {
                "document_type": doc_type,
                "confidence": 0.0,
                "fields": {},
                "field_confidence": {},
                "notes": f"API 오류: {e}"
            }

    async def process_single_pdf_async(self, pdf_path: str, slip_id: str, extraction_mode: str = 'basic') -> Dict:
        """
        단일 PDF 파일 비동기 처리
        
        Args:
            pdf_path: PDF 파일 경로
            slip_id: 전표 ID
            extraction_mode: 'basic' 또는 'detailed'
        """
        filename = os.path.basename(pdf_path).upper()
        
        # 0. 파일명 기반 1차 필터링
        is_target = False
        if "BILL_OF_LADING" in filename or "WAYBILL" in filename:
            is_target = True
        elif ("COMMERCIAL_INVOICE" in filename or "INVOICE" in filename) and "PACKING" not in filename:
            is_target = True
            
        if not is_target:
            return {
                "slip_id": slip_id,
                "documents": [],
                "source": "pdf_ocr"
            }

        print(f"📄 처리 시작: {os.path.basename(pdf_path)}")
        
        # 문서 타입 결정 (파일명 기반)
        doc_type = "UNKNOWN"
        if "BILL_OF_LADING" in filename or "WAYBILL" in filename:
            doc_type = "BL"
        elif "COMMERCIAL_INVOICE" in filename or "INVOICE" in filename:
            doc_type = "INVOICE"
        
        print(f"   ✅ 타입 확정: {os.path.basename(pdf_path)} -> {doc_type}")
        
        # ✅ extraction_mode에 따라 필드 선택
        extraction_modes = self.extraction_config.get('extraction_modes', {})
        mode_config = extraction_modes.get(extraction_mode, extraction_modes.get('basic'))  # fallback to basic
        
        if mode_config and 'document_types' in mode_config:
            document_types = mode_config['document_types']
            if doc_type in document_types:
                extraction_fields = document_types[doc_type].get('fields', [])
                print(f"   📋 {extraction_mode} 모드 - {doc_type} 필드: {len(extraction_fields)}개")
            else:
                print(f"   ⚠️ {doc_type} 설정 없음, 스킵")
                return {
                    "slip_id": slip_id,
                    "documents": [],
                    "source": "pdf_ocr"
                }
        else:
            print(f"   ⚠️ extraction_mode '{extraction_mode}' 설정 없음")
            return {
                "slip_id": slip_id,
                "documents": [],
                "source": "pdf_ocr"
            }
        
        documents = []
        
        try:
            full_text = ""
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            pages_to_read = min(num_pages, 3)
            
            for i in range(pages_to_read):
                page = doc[i]
                text = page.get_text()
                if len(text.strip()) < OCR_THRESHOLD:
                    text = self.high_quality_ocr(pdf_path, i)
                full_text += f"\n--- Page {i+1} ---\n{text}"
            
            doc.close()
            
            # 3. Gemini API 비동기 호출
            print(f"   🤖 API 요청: {os.path.basename(pdf_path)}")
            extraction_result = await self.extract_with_gemini_async(full_text, doc_type, extraction_fields)
            
            extraction_result['page'] = 1
            extraction_result['type'] = doc_type
            extraction_result['file_name'] = os.path.basename(pdf_path)
            
            documents.append(extraction_result)
            print(f"   ✨ 완료: {os.path.basename(pdf_path)}")
            
            return {
                "slip_id": slip_id,
                "documents": documents,
                "source": "pdf_ocr"
            }
            
        except Exception as e:
            print(f"❌ 오류 ({os.path.basename(pdf_path)}): {e}")
            return {
                "slip_id": slip_id,
                "documents": [],
                "error": str(e)
            }


    async def process_project_pdfs_async(self, project_id: str, split_dir: str, extraction_mode: str = 'basic', target_ids: List[str] = None) -> List[Dict]:
        """
        프로젝트 전체 PDF 비동기 병렬 처리
        OPTIMIZED: Only scans extraction_targets/ subfolder (BL & Invoice)
        Falls back to root folder for backward compatibility
        
        Args:
            project_id: 프로젝트 ID
            split_dir: split_documents 폴더 경로
            extraction_mode: 'basic' 또는 'detailed'
            target_ids: 처리할 전표 ID 리스트 (None이면 전체 처리)
        """
        print(f"🚀 프로젝트 {project_id} 비동기 처리 시작 (모드: {extraction_mode}, 대상: {'전체' if not target_ids else len(target_ids)})")
        
        if not os.path.exists(split_dir):
            print(f"❌ 폴더 없음: {split_dir}")
            return []
        
        # 모든 PDF 파일 수집 (extraction_targets만 스캔하여 속도 향상)
        tasks = []
        semaphore = asyncio.Semaphore(3)  # 동시에 3개까지만 처리 (메모리 보호)
        
        async def sem_task(pdf_path, slip_id):
            async with semaphore:
                return await self.process_single_pdf_async(pdf_path, slip_id, extraction_mode)

        for slip_folder in os.listdir(split_dir):
            slip_path = os.path.join(split_dir, slip_folder)
            if not os.path.isdir(slip_path):
                continue
                
            slip_id = slip_folder
            
            # 필터링: target_ids가 있고, 현재 slip_id가 그 안에 없으면 스킵
            if target_ids is not None and slip_id not in target_ids:
                continue
            
            # ✅ OPTIMIZED: Check extraction_targets/ subfolder first
            extraction_targets_path = os.path.join(slip_path, 'extraction_targets')
            
            if os.path.exists(extraction_targets_path) and os.path.isdir(extraction_targets_path):
                # New structure: only scan extraction_targets/
                pdf_files = [f for f in os.listdir(extraction_targets_path) if f.lower().endswith('.pdf')]
                print(f"  ✅ {slip_id}: {len(pdf_files)} extraction target(s) found")
                
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(extraction_targets_path, pdf_file)
                    tasks.append(sem_task(pdf_path, slip_id))
            else:
                # Fallback: Old structure - scan root folder
                # (This ensures backward compatibility with existing projects)
                pdf_files = [f for f in os.listdir(slip_path) if f.lower().endswith('.pdf')]
                print(f"  ⚠️  {slip_id}: Using old structure, {len(pdf_files)} file(s) found")
                
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(slip_path, pdf_file)
                    tasks.append(sem_task(pdf_path, slip_id))
        
        print(f"📊 총 {len(tasks)}개 파일 병렬 처리 시작... (extraction_targets만 스캔)")
        
        # 병렬 실행
        try:
            results = await asyncio.gather(*tasks)
        except Exception as e:
            print(f"[CRITICAL ERROR] asyncio.gather failed: {e}")
            import traceback
            traceback.print_exc()
            with open("crash_log_engine.txt", "a") as f:
                f.write(f"[{datetime.now()}] Crash in smart_extraction_engine gather: {e}\n")
                f.write(traceback.format_exc())
            raise e
        
        # 결과 집계 (전표별로 묶기)
        slip_results_map = {}
        
        for res in results:
            slip_id = res.get('slip_id')
            if not slip_id: continue
            
            if slip_id not in slip_results_map:
                slip_results_map[slip_id] = {
                    "slip_id": slip_id,
                    "documents": [],
                    "source": "pdf_ocr"
                }
            
            if 'documents' in res:
                slip_results_map[slip_id]['documents'].extend(res['documents'])
        
        final_results = list(slip_results_map.values())
        print(f"✅ 총 {len(final_results)}개 전표 처리 완료")
        return final_results

    # 동기 메서드 유지 (하위 호환성)
    def process_single_pdf(self, pdf_path: str, slip_id: str, extraction_mode: str = 'basic', ocr_json_dir: str = None) -> Dict:
        return asyncio.run(self.process_single_pdf_async(pdf_path, slip_id, extraction_mode))



if __name__ == "__main__":
    # 테스트 코드
    engine = SmartExtractionEngine()
    print("SmartExtractionEngine 초기화 완료")
