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
        self.semaphore = asyncio.Semaphore(5)  # ✅ 병렬 처리 제한 (Semaphore) 추가
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
            
            # 최신 안정 모델 (사용자 환경에서 2.0 이상 지원 확인됨)
            GEMINI_MODEL_NAME = 'models/gemini-2.0-flash'
            
            # 시스템 지시사항 (사용자 제안 반영)
            SYSTEM_INSTRUCTION = """
            당신은 물류 문서(B/L, Invoice) 전문 데이터 추출 엔진입니다. 
            JSON으로만 응답하며, 날짜 형식(YYYY-MM-DD), 통화 코드 준수 등 데이터 정규화 규칙을 엄격히 따릅니다.
            수량과 금액은 반드시 숫자 형식으로 추출하고, 쉼표 등은 제거하세요.
            """
            
            try:
                self.gemini_model = genai.GenerativeModel(
                    model_name=GEMINI_MODEL_NAME,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                # 간단한 테스트
                test_response = self.gemini_model.generate_content("Hello")
                if test_response and test_response.text:
                    print(f"✅ Gemini API 초기화 완료 (모델: {GEMINI_MODEL_NAME})")
                else:
                    raise Exception("테스트 응답 없음")
            except Exception as e:
                print(f"⚠️ {GEMINI_MODEL_NAME} 실패: {e}")
                # 대체 모델 목록 (최신 버전 우선 순위)
                fallback_models = [
                    'models/gemini-2.5-flash',       # 최신 2.5 버전
                    'models/gemini-2.5-flash-lite',  # 2.5 경량 버전
                    'models/gemini-3-flash',         # 차세대 3 버전
                    'models/gemini-1.5-flash',       # 기존 안정 버전
                    'models/gemini-1.5-pro'          # 고성능 (비용↑)
                ]
                model_loaded = False
                
                for fallback_model in fallback_models:
                    try:
                        print(f"   시도 중: {fallback_model}")
                        self.gemini_model = genai.GenerativeModel(
                            model_name=fallback_model,
                            system_instruction=SYSTEM_INSTRUCTION
                        )
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

        # ✅ TextPreprocessor 초기화
        try:
            from Modules.Parser.text_preprocessor import TextPreprocessor
            self.text_preprocessor = TextPreprocessor()
            print("✅ TextPreprocessor 초기화 완료")
        except Exception as e:
            print(f"⚠️ TextPreprocessor 초기화 실패: {e}")
            self.text_preprocessor = None
            
        # ✅ CombinationFinder 초기화
        try:
            from Modules.Parser.combination_finder import CombinationFinder
            self.combination_finder = CombinationFinder()
            print("✅ CombinationFinder 초기화 완료")
        except Exception as e:
            print(f"⚠️ CombinationFinder 초기화 실패: {e}")
            self.combination_finder = None
    
    
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
    
    

    def high_quality_ocr(self, pdf_path: str, page_num: int) -> str:
        """
        고품질 OCR (전체 페이지) - 스캔 문서용
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            # 고해상도 이미지 생성 (300 DPI 이상 권장, zoom=2.0)
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            
            # 전체 OCR 실행 (한글+영어)
            text = pytesseract.image_to_string(img, lang='eng+kor')
            return text
            
        except Exception as e:
            print(f"❌ 고품질 OCR 오류: {e}")
            return ""

    async def extract_with_gemini_async(self, ocr_text: str, doc_type: str, extraction_fields: List[Dict], expected_values: Dict = None) -> Dict:
        """
        Gemini API로 필드 추출 (비동기) with 구조화된 요청
        """
        if not self.gemini_model:
            raise Exception("Gemini API가 초기화되지 않았습니다")
        
        # 문서 타입별 지시사항
        doc_instruction = ""
        if doc_type == "BL":
            doc_instruction = "이 문서는 선하증권(Bill of Lading)입니다. 선박 정보, 운송 정보, Incoterms, 그리고 **중량 정보(Net Weight, Gross Weight)**를 주의 깊게 찾아 추출하세요."
        elif doc_type == "INVOICE":
            doc_instruction = "이 문서는 상업송장(Commercial Invoice)입니다. 금액과 거래 정보를 중심으로 추출하세요."
        
        # 기대 값(Expected Values) 힌트 추가
        hint_instruction = ""
        if expected_values:
            hint_instruction = "\n**[중요 힌트]** 다음은 이 문서에서 기대되는 값들입니다. 문서 내에서 이 값들과 일치하는 항목을 우선적으로 찾아보세요:\n"
            if 'total_amount' in expected_values:
                hint_instruction += f"- 기대 총 금액: {expected_values['total_amount']}\n"
            if 'total_quantity' in expected_values:
                hint_instruction += f"- 기대 총 수량: {expected_values['total_quantity']}\n"
            hint_instruction += "만약 기대 값과 문서상의 값이 다르다면, 문서상의 값을 추출하고 그 이유를 'notes' 필드에 기록하세요.\n"

        # 필드별 프롬프트 및 예상 응답 구조 생성
        field_prompts = ""
        expected_fields_example = {}
        
        for field in extraction_fields:
            output_format = field.get('output_format', {})
            field_prompt = field['prompt']
            
            # Incoterms 필드에 대한 추가 힌트
            if 'incoterms' in field['name'].lower():
                field_prompt += " (예: FOB, CIF, EXW, DDP 등)"
            
            field_prompts += f"- {field['label']} ({field['name']}): {field_prompt}\n"
            
            # 예상 응답 형태 생성
            if 'currency' in output_format:
                expected_fields_example[field['name']] = {"value": 0.0, "currency": "USD", "coordinates": [0, 0, 0, 0]}
            elif 'unit' in output_format:
                expected_fields_example[field['name']] = {"value": 0.0, "unit": "MT", "coordinates": [0, 0, 0, 0]}
            elif output_format.get('format') == 'date':
                expected_fields_example[field['name']] = {"value": "YYYY-MM-DD", "format": "date", "coordinates": [0, 0, 0, 0]}
            else:
                expected_fields_example[field['name']] = {"value": "추출된 값", "format": "text", "coordinates": [0, 0, 0, 0]}
        
        # ✅ Text Preprocessing (Token Optimization)
        if self.text_preprocessor:
            print(f"   🧹 Preprocessing text... (Original: {len(ocr_text)} chars)")
            ocr_text = self.text_preprocessor.preprocess(ocr_text, doc_type)
            print(f"   ✨ Preprocessed: {len(ocr_text)} chars")

        # ✅ N:1 Combination Finder (Python Logic)
        combo_hint = ""
        if self.combination_finder and expected_values:
            # 1. Check Amount
            exp_amount = expected_values.get('total_amount')
            if exp_amount:
                try:
                    # Remove commas if string
                    target_amt = float(str(exp_amount).replace(',', ''))
                    combo = self.combination_finder.find_combination(ocr_text, target_amt)
                    if combo:
                        combo_str = " + ".join([f"{n:,.2f}" for n in combo])
                        combo_hint += f"- 💡 Found combination for Amount: {combo_str} = {target_amt:,.2f}\n"
                except:
                    pass

            # 2. Check Quantity
            exp_qty = expected_values.get('total_quantity')
            if exp_qty:
                try:
                    target_qty = float(str(exp_qty).replace(',', ''))
                    combo = self.combination_finder.find_combination(ocr_text, target_qty)
                    if combo:
                        combo_str = " + ".join([f"{n:,.2f}" for n in combo])
                        combo_hint += f"- 💡 Found combination for Quantity: {combo_str} = {target_qty:,.2f}\n"
                except:
                    pass
        
        if combo_hint:
            hint_instruction += "\n**[N:1 MATCHING HINTS]**\n" + combo_hint
            hint_instruction += "Use these combinations to verify the total amount/quantity. If they match, extract the individual items as evidence.\n"

        prompt = f"""
다음 {doc_type} 문서의 OCR 텍스트를 분석하세요:

{doc_instruction}
{hint_instruction}

{ocr_text}

**추출할 필드:**
{field_prompts}

**응답 형식 (JSON only):**
{{
  "document_type": "{doc_type}",
  "confidence": 0.95,
  "fields": {json.dumps(expected_fields_example, ensure_ascii=False, indent=2)},
  "field_confidence": {{
    {', '.join([f'"{f["name"]}": 0.95' for f in extraction_fields])}
  }},
  "evidence": [
    {{
      "field": "total_amount",
      "values": [100.00, 200.00],
      "coordinates": [[ymin, xmin, ymax, xmax], [ymin, xmin, ymax, xmax]],
      "reason": "Sum of line items matches expected total"
    }}
  ],
  "notes": "추출 과정에서 특이사항이나 불확실한 부분"
}}
"""
        
        # ★ FIX: 재시도 횟수 축소 (사용자 요청: 3 -> 1)
        max_retries = 1
        retry_delay = 2
        
        for attempt in range(max_retries + 1):
            try:
                # 비동기 호출 (JSON 모드 적용)
                response = await self.gemini_model.generate_content_async(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
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
                
                # JSON 모드이므로 바로 파싱 가능
                raw_result = json.loads(response.text)
                raw_result['token_usage'] = token_info
                
                # ✅ DataNormalizer 적용
                if self.data_normalizer:
                    normalized_result = self.data_normalizer.normalize_extraction_result(raw_result)
                    normalized_result['token_usage'] = token_info
                else:
                    normalized_result = raw_result
                
                # ✅ 결과 검증 (Validation)
                is_valid = True
                validation_note = ""
                
                critical_fields = []
                if doc_type == "INVOICE":
                    critical_fields = ['total_amount']
                elif doc_type == "BL":
                    critical_fields = ['bl_number']
                
                fields = normalized_result.get('fields', {})
                
                for field_name in critical_fields:
                    field_data = fields.get(field_name, {})
                    if not field_data or field_data.get('value') in [None, "", 0]:
                        is_valid = False
                        validation_note = f"Critical field missing: {field_name}"
                        break
                
                # ✅ N:1 매칭 검증 추가 (Amount/Quantity Mismatch)
                if is_valid and doc_type == "INVOICE" and expected_values:
                    def normalize_val(v):
                        if v is None: return None
                        if isinstance(v, (int, float)): return float(v)
                        try:
                            # 콤마 제거 후 float 변환
                            return float(str(v).replace(',', '').strip())
                        except:
                            return None

                    ext_amount = normalize_val(fields.get('total_amount', {}).get('value'))
                    ext_qty = normalize_val(fields.get('total_quantity', {}).get('value'))
                    
                    exp_amount = normalize_val(expected_values.get('total_amount'))
                    exp_qty = normalize_val(expected_values.get('total_quantity'))
                    
                    # 기대값이 있고 추출값이 다를 경우 (N:1 상황 의심)
                    if (exp_amount is not None and ext_amount != exp_amount) or \
                       (exp_qty is not None and ext_qty != exp_qty):
                        is_valid = False
                        validation_note = f"N:1 Mismatch (Ext: {ext_amount}/{ext_qty}, Exp: {exp_amount}/{exp_qty})"
                        
                        # 다음 재시도를 위한 프롬프트 보강 (라인 아이템 정밀 분석 지시)
                        prompt += f"""
                            **OUTPUT REQUIREMENT:**
                            - **CRITICAL**: Set the `total_amount` field to the **SUMMED VALUE** ({exp_amount}), NOT the document total.
                            - In the 'evidence' field, you MUST explain the combination: e.g., "Sum of Line Item 1 (100.00) and Line Item 3 (200.00) matches expected {exp_amount}".
                            - In the 'notes' field, state clearly: "Found via N:1 combination".
                            """
                
                if is_valid or len(ocr_text) < 50:
                    return normalized_result
                else:
                    print(f"   ⚠️ 검증 실패 ({attempt+1}/{max_retries}): {validation_note}")
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        normalized_result['notes'] = f"{normalized_result.get('notes', '')} [Validation Failed: {validation_note}]"
                        return normalized_result
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Gemini API 오류 ({attempt+1}/{max_retries}): {error_msg}")
                
                # 429 오류 처리 (할당량 초과)
                if "429" in error_msg or "quota" in error_msg.lower():
                    # 일일 할당량 소진 시 즉시 중단
                    if "daily" in error_msg.lower():
                        print("🚨 일일 할당량이 모두 소진되었습니다. 작업을 중단합니다.")
                        raise Exception("Gemini API 일일 할당량 초과")
                    
                    # 재시도 대기 시간 파싱 (예: "Wait 49s")
                    wait_match = re.search(r'wait\s*(\d+)s', error_msg.lower())
                    wait_time = int(wait_match.group(1)) if wait_match else 60
                    
                    print(f"   ⏳ 할당량 초과. {wait_time}초 대기 후 재시도합니다...")
                    await asyncio.sleep(wait_time)
                    continue

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    return {
                        "document_type": doc_type,
                        "confidence": 0.0,
                        "fields": {},
                        "field_confidence": {},
                        "notes": f"API 오류 (Max Retries): {e}"
                    }

    def _generate_search_variations(self, text: str) -> List[str]:
        """Generate variations of text for robust searching (numbers, dates)"""
        variations = [str(text)]
        text_str = str(text).strip()
        
        # 1. Handle Numbers (remove/add commas, spaces)
        clean_text = text_str.replace(',', '').replace(' ', '').strip()
        if clean_text:
            variations.append(clean_text)
            try:
                # Try to format as number with commas
                float_val = float(clean_text)
                variations.extend([
                    f"{float_val:,.2f}",  # 1,234.56
                    f"{float_val:,.0f}",  # 1,234
                    f"{float_val:.2f}",   # 1234.56 (no comma)
                    f"{float_val:.0f}",   # 1234 (no comma)
                ])
                if float_val.is_integer():
                    variations.append(f"{int(float_val)}")  # 1234
                    variations.append(f"{int(float_val):,}") # 1,234
            except:
                pass

        # 2. Handle Dates (YYYY-MM-DD -> various formats)
        # ISO format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', text_str):
            try:
                from datetime import datetime
                dt = datetime.strptime(text_str, "%Y-%m-%d")
                variations.extend([
                    # Common international formats
                    dt.strftime("%d-%b-%y"),      # 24-Dec-24
                    dt.strftime("%d-%b-%Y"),      # 24-Dec-2024
                    dt.strftime("%b %d, %Y"),     # Dec 24, 2024
                    dt.strftime("%d %b %Y"),      # 24 Dec 2024
                    dt.strftime("%Y. %m. %d"),    # 2024. 12. 24
                    dt.strftime("%Y/%m/%d"),      # 2024/12/24
                    dt.strftime("%d/%m/%Y"),      # 24/12/2024
                    dt.strftime("%m/%d/%Y"),      # 12/24/2024
                    # With uppercase month
                    dt.strftime("%d-%b-%Y").upper(),  # 24-DEC-2024
                    dt.strftime("%d %b %Y").upper(),  # 24 DEC 2024
                    # Without leading zeros
                    f"{dt.day}-{dt.strftime('%b')}-{dt.year}",  # 8-Dec-2024
                    f"{dt.day} {dt.strftime('%b')} {dt.year}",  # 8 Dec 2024
                    # Dot separators
                    dt.strftime("%d.%m.%Y"),      # 24.12.2024
                    # Space variations
                    dt.strftime("%Y %m %d"),      # 2024 12 24
                ])
            except:
                pass
                
        # Remove duplicates and empty strings
        return list(set([v for v in variations if v]))

    def _find_text_coordinates(self, pdf_path: str, text_to_find: str) -> List[int]:
        """
        PDF에서 텍스트 좌표 찾기 (Robust)
        Returns: [ymin, xmin, ymax, xmax] (0~1000 normalized)
        """
        if not text_to_find:
            return [0, 0, 0, 0]
            
        try:
            variations = self._generate_search_variations(text_to_find)
            
            doc = fitz.open(pdf_path)
            # 첫 3페이지만 검색
            for i in range(min(len(doc), 3)):
                page = doc[i]
                width = page.rect.width
                height = page.rect.height
                
                for variant in variations:
                    rects = page.search_for(variant)
                    if rects:
                        rect = rects[0]
                        xmin = int((rect.x0 / width) * 1000)
                        ymin = int((rect.y0 / height) * 1000)
                        xmax = int((rect.x1 / width) * 1000)
                        ymax = int((rect.y1 / height) * 1000)
                        doc.close()
                        return [ymin, xmin, ymax, xmax]
            
            doc.close()
            return [0, 0, 0, 0]
            
        except Exception as e:
            print(f"⚠️ 좌표 검색 오류: {e}")
            return [0, 0, 0, 0]

    def _find_multiple_text_coordinates(self, pdf_path: str, text_list: List[str]) -> List[List[int]]:
        """
        여러 텍스트의 좌표를 한 번에 검색 (최적화)
        """
        if not text_list:
            return []
        
        results = []
        try:
            doc = fitz.open(pdf_path)
            
            for text_to_find in text_list:
                found = False
                variations = self._generate_search_variations(text_to_find)
                
                for i in range(min(len(doc), 3)):
                    page = doc[i]
                    width = page.rect.width
                    height = page.rect.height
                    
                    for variant in variations:
                        rects = page.search_for(variant)
                        if rects:
                            rect = rects[0]
                            xmin = int((rect.x0 / width) * 1000)
                            ymin = int((rect.y0 / height) * 1000)
                            xmax = int((rect.x1 / width) * 1000)
                            ymax = int((rect.y1 / height) * 1000)
                            results.append([ymin, xmin, ymax, xmax])
                            found = True
                            break
                    if found: break
                
                if not found:
                    results.append([0, 0, 0, 0])
            
            doc.close()
            return results
        except Exception as e:
            print(f"⚠️ 다중 좌표 검색 오류: {e}")
            return [[0, 0, 0, 0]] * len(text_list)

    async def process_single_pdf_async(self, pdf_path: str, slip_id: str, extraction_mode: str = 'basic', expected_values: Dict = None) -> Dict:
        """
        단일 PDF 파일 비동기 처리
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
                full_text += f"\n\n{text}"
            
            doc.close()
            
            # 3. Gemini API 비동기 호출
            print(f"   🤖 API 요청: {os.path.basename(pdf_path)}")
            extraction_result = await self.extract_with_gemini_async(full_text, doc_type, extraction_fields, expected_values)
            
            # ✅ Post-processing: 좌표 찾기 (Highlighting)
            print(f"   🔍 좌표 검색 중: {os.path.basename(pdf_path)}")
            fields = extraction_result.get('fields', {})
            for field_name, field_data in fields.items():
                if isinstance(field_data, dict):
                    value = field_data.get('value')
                    # 값이 있고 좌표가 없거나 [0,0,0,0]인 경우 검색
                    if value and (not field_data.get('coordinates') or field_data.get('coordinates') == [0, 0, 0, 0]):
                        coords = self._find_text_coordinates(pdf_path, str(value))
                        field_data['coordinates'] = coords
            
            # Evidence 좌표 찾기 (N:1)
            evidence = extraction_result.get('evidence')
            if evidence and isinstance(evidence, list):
                print(f"   🔍 Evidence 좌표 검색 중 ({len(evidence)} items)")
                for item in evidence:
                    # AI가 좌표를 주지 않았거나 비어있는 경우
                    if not item.get('coordinates') or not any(item.get('coordinates', [])):
                        values = item.get('values', [])
                        
                        if values:
                            # Optimized: Find all coordinates at once
                            found_coords = self._find_multiple_text_coordinates(pdf_path, [str(v) for v in values])
                            
                            # Filter out [0,0,0,0]
                            valid_coords = [c for c in found_coords if c != [0, 0, 0, 0]]
                            
                            if valid_coords:
                                item['coordinates'] = valid_coords
                                print(f"     - Evidence coords found: {len(valid_coords)} boxes")
                            else:
                                item['coordinates'] = []
                        else:
                            item['coordinates'] = []

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

    async def process_project_pdfs_async(self, project_id: str, split_dir: str, extraction_mode: str = 'basic', target_ids: List[str] = None, progress_callback=None, expected_values_map: Dict = None) -> List[Dict]:
        """
        프로젝트 전체 PDF 비동기 병렬 처리
        OPTIMIZED: Only scans extraction_targets/ subfolder (BL & Invoice)
        Falls back to root folder for backward compatibility
        
        Args:
            project_id: 프로젝트 ID
            split_dir: split_documents 폴더 경로
            extraction_mode: 'basic' 또는 'detailed'
            target_ids: 처리할 전표 ID 리스트 (None이면 전체 처리)
            progress_callback: 진행률 콜백 함수 (current, total, doc_number, message)
            expected_values_map: 전표별 기대 금액/수량 힌트 맵 {slip_id: {total_amount: X, total_quantity: Y}}
        """
        from datetime import datetime
        
        print(f"🚀 프로젝트 {project_id} 비동기 처리 시작 (모드: {extraction_mode}, 대상: {'전체' if not target_ids else len(target_ids)})")
        slip_folders = [f for f in os.listdir(split_dir) if os.path.isdir(os.path.join(split_dir, f))]
        total_slips = len([s for s in slip_folders if target_ids is None or s in target_ids])
        current_slip = 0
        
        if progress_callback:
            progress_callback(0, total_slips, "", "추출 시작...")

        # ✅ 세마포어를 이용한 비동기 작업 정의
        async def sem_task(pdf_path, slip_id):
            async with self.semaphore:
                # 해당 전표의 기대 값 가져오기
                expected_values = expected_values_map.get(slip_id) if expected_values_map else None
                return await self.process_single_pdf_async(pdf_path, slip_id, extraction_mode, expected_values)

        tasks = []
        for slip_folder in slip_folders:
            slip_path = os.path.join(split_dir, slip_folder)
            if not os.path.isdir(slip_path):
                continue
                
            slip_id = slip_folder
            
            # 필터링: target_ids가 있고, 현재 slip_id가 그 안에 없으면 스킵
            if target_ids is not None and slip_id not in target_ids:
                continue
            
            # ★ 진행률 업데이트
            current_slip += 1
            if progress_callback:
                progress_callback(current_slip - 1, total_slips, slip_id, f"추출 중: {slip_id}")
            
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
        
        return list(slip_results_map.values())
