# -*- coding: utf-8 -*-
import pandas as pd
import os
import json
import time # API 호출 간 지연을 위해
import openpyxl # .xlsx 파일 처리를 위해 필요합니다. (pip install openpyxl)
import xlrd     # .xls 파일 처리를 위해 필요합니다. (pip install xlrd >= 2.0.1 권장)
from zipfile import BadZipFile # 특정 오류 처리를 위해 필요합니다.
import sys

# 즉시 출력으로 GUI에서 프로세스 시작 확인
print("[시작] Auto_reconcile_byGemini.py 모듈 진입", flush=True)
print(f"[시간] {pd.Timestamp.now().strftime('%H:%M:%S')}", flush=True)
print(f"[인수] sys.argv: {sys.argv}", flush=True)
print(f"[경로] 현재 작업 디렉토리: {os.getcwd()}", flush=True)

# Google Gemini API 연동을 위한 라이브러리 (pip install google-generativeai)
import google.generativeai as genai
import requests
from datetime import datetime, timedelta

# Config 파일에서 인코텀즈 설정 가져오기
try:
    from Config.config import AI_RECONCILIATION_CONFIG
    INCOTERMS_CONFIG = AI_RECONCILIATION_CONFIG.get("incoterms_revenue_recognition", {})
except ImportError:
    # Config 파일이 없을 경우 기본값 사용
    INCOTERMS_CONFIG = {
        "CFR": {"revenue_date": "shipment_date", "description": "선적일 기준"},
        "CIF": {"revenue_date": "shipment_date", "description": "선적일 기준"},
        "FOB": {"revenue_date": "shipment_date", "description": "선적일 기준"},
        "EXW": {"revenue_date": "factory_release_date", "description": "공장출고일 기준"},
        "DAP": {"revenue_date": "arrival_date", "description": "도착일 기준"},
        "DDP": {"revenue_date": "arrival_date", "description": "도착일 기준"}
    }

# --- 설정값 ---
# 기본값들은 None으로 설정하여 GUI에서 전달받은 경로를 우선 사용
DEFAULT_INPUT_EXCEL_PATH = None
DEFAULT_OUTPUT_DIR = None
DEFAULT_OCR_JSON_DIR = None

# 체크포인트 설정
CHECKPOINT_INTERVAL = 20  # 20건마다 체크포인트 저장

# AI 대사 결과 컬럼 정의
RECONCILIATION_COLUMNS = [
    "amount_match",      # 금액 대사
    "quantity_match",    # 수량 대사
    "date_match",        # 매출일자 대사
    "customer_match",    # 고객/구매처 대사
    "overall_status",    # 전체 상태 (영어)
    "전체결과",          # 전체 상태 (한글)
    "notes"             # 비고 (특이사항)
]

# 증빙에서 읽어온 실제 값들을 표시할 컬럼들
EVIDENCE_VALUE_COLUMNS = [
    "evidence_amount",   # 증빙에서 읽어온 금액
    "evidence_quantity", # 증빙에서 읽어온 수량
    "evidence_date",     # 증빙에서 읽어온 날짜
    "evidence_customer"  # 증빙에서 읽어온 고객사
]

# --- Gemini API 설정 ---
# !!! 중요: 여기에 사용자님의 실제 Gemini API 키를 입력하세요 !!!
GEMINI_API_KEY = "your_api_key" # <--- 사용자님의 정확한 API 키

def initialize_gemini_api():
    """Gemini API 초기화"""
    print(f"🔍 Gemini API 초기화 시작: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    
    # API 키 유효성 초기 확인
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY" or not GEMINI_API_KEY.strip() or len(GEMINI_API_KEY) < 39:
        print("❌ 오류: Gemini API 키가 설정되지 않았거나 유효하지 않은 형식입니다. 'GEMINI_API_KEY' 변수에 실제 키를 정확히 입력해주세요.", flush=True)
        return None

    try:
        print(f"🔍 API 키 설정 중... (키 길이: {len(GEMINI_API_KEY)})", flush=True)
        genai.configure(api_key=GEMINI_API_KEY)
        print(f"🔍 API 키 설정 완료: {datetime.now().strftime('%H:%M:%S')}", flush=True)
        
        # 모델 목록 조회 건너뛰고 직접 모델 시도
        print(f"🔍 모델 목록 조회 건너뛰고 직접 모델 시도: {datetime.now().strftime('%H:%M:%S')}", flush=True)
        
        # 모델 선택 로직 단순화
        GEMINI_MODEL_NAME = 'gemini-1.5-flash'  # 기본 모델로 설정
        
        try:
            gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            
            # 간단한 테스트 요청으로 API 키 유효성 확인
            print(f"🔍 API 키 유효성 테스트 중...", flush=True)
            test_response = gemini_model.generate_content("Hello")
            if test_response and test_response.text:
                print(f"✅ Gemini API 설정 및 모델 초기화 완료. 사용 모델: {GEMINI_MODEL_NAME}", flush=True)
                return gemini_model
            else:
                print(f"⚠️ API 테스트 응답이 비어있습니다.", flush=True)
                return None
                
        except Exception as e:
            print(f"⚠️ 기본 모델 '{GEMINI_MODEL_NAME}' 로드 실패: {e}", flush=True)
            
            # 대체 모델 시도
            fallback_models = ['gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
            for fallback_model in fallback_models:
                try:
                    print(f"🔍 대체 모델 시도: {fallback_model}", flush=True)
                    gemini_model = genai.GenerativeModel(fallback_model)
                    
                    # 간단한 테스트 요청
                    test_response = gemini_model.generate_content("Hello")
                    if test_response and test_response.text:
                        print(f"✅ 대체 모델 로드 성공: {fallback_model}", flush=True)
                        return gemini_model
                    else:
                        print(f"⚠️ 대체 모델 '{fallback_model}' 테스트 응답이 비어있습니다.", flush=True)
                        continue
                        
                except Exception as fallback_error:
                    print(f"❌ 대체 모델 '{fallback_model}' 실패: {fallback_error}", flush=True)
                    continue
            
            print("❌ 모든 모델 로드 실패. API 키나 네트워크 연결을 확인해주세요.", flush=True)
            return None
        
    except Exception as e:
        print(f"❌ Gemini API 초기화 중 오류 발생: {e}", flush=True)
        print("API 키가 유효한지, Google Cloud 프로젝트에서 Generative Language API가 활성화되어 있고 결제 계정이 연결되었는지 확인해주세요 (`pip install google-generativeai`).", flush=True)
        return None

def get_gemini_usage_info():
    """Gemini API 월별 사용량 정보 가져오기"""
    try:
        # Google AI Studio API를 통한 사용량 정보 가져오기
        # 참고: 실제 구현에서는 Google Cloud Billing API나 다른 방법을 사용해야 할 수 있습니다
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        headers = {
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # 실제 사용량 정보는 별도 API 엔드포인트에서 가져와야 합니다
            # 현재는 모의 데이터를 반환
            current_month = datetime.now().strftime("%Y-%m")
            return {
                "current_month": current_month,
                "total_input_tokens": 0,  # 실제 API에서 가져와야 함
                "total_output_tokens": 0,  # 실제 API에서 가져와야 함
                "quota_limit": 15000000,  # Gemini Pro 무료 할당량 (월 15M 토큰)
                "quota_remaining": 15000000  # 실제 API에서 가져와야 함
            }
        else:
            print(f"⚠️ 사용량 정보 가져오기 실패: {response.status_code}", flush=True)
            return None
            
    except Exception as e:
        print(f"⚠️ 사용량 정보 조회 중 오류: {e}", flush=True)
        return None

# --- 엑셀 파일 로딩 함수 (견고하게) ---
def load_excel_robustly(file_path, sheet_name=None):
    """
    엑셀 파일을 로드하는 견고한 함수입니다.
    .xlsx 파일을 openpyxl로 먼저 시도하고, 실패 시 xlrd로 .xls 파일처럼 시도합니다.
    """
    print(f"▶️ 엑셀 파일 로딩 시도: {file_path}", flush=True)

    try:
        if sheet_name:
            df = pd.read_excel(file_path, engine='openpyxl', sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
        print(f"✅ 'openpyxl' 엔진으로 엑셀 파일 로딩 성공!", flush=True)
        return df
    except (BadZipFile, KeyError, FileNotFoundError, ValueError) as e:
        print(f" - 'openpyxl' 시도 실패 (오류 유형: {type(e).__name__}): {e}", flush=True)
    except Exception as e:
        print(f" - 'openpyxl' 시도 중 예상치 못한 오류 발생: {e}", flush=True)

    try:
        if sheet_name:
            df = pd.read_excel(file_path, engine='xlrd', sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path, engine='xlrd')
        print(f"✅ 'xlrd' 엔진으로 엑셀 파일 로딩 성공!", flush=True)
        return df
    except ImportError:
        print(" - 'xlrd' 라이브러리가 설치되지 않았거나 버전이 낮습니다. 'pip install xlrd'를 실행해 주세요.", flush=True)
    except Exception as e:
        print(f" - 'xlrd' 시도 중 예상치 못한 오류 발생: {e}", flush=True)

    print(f"❌ 엑셀 파일 로딩 최종 실패: {file_path}", flush=True)
    print("💡 **해결 팁:**", flush=True)
    print("   1. 해당 엑셀 파일을 Microsoft Excel에서 직접 열어 '다른 이름으로 저장'을 통해 **'Excel 통합 문서(*.xlsx)'** 또는 **'Excel 97-2003 통합 문서(*.xls)'** 형식으로 **새 파일로 다시 저장**한 후, 해당 새 파일로 스크립트를 시도해 보세요.", flush=True)
    print("   2. `pandas`, `openpyxl`, `xlrd` 라이브러리가 모두 최신 버전인지 확인해 보세요 (`pip install --upgrade pandas openpyxl xlrd`).", flush=True)
    return None

def save_checkpoint(df_results, output_dir, completed_count, total_count, timestamp):
    """체크포인트 파일을 저장합니다."""
    try:
        checkpoint_file = os.path.join(output_dir, f"checkpoint_Gemini_{timestamp}.json")
        checkpoint_data = {
            "timestamp": timestamp,
            "completed_count": completed_count,
            "total_count": total_count,
            "completed_docs": df_results[df_results['전체결과'].notna()]['Doc_No'].tolist(),
            "last_updated": datetime.now().isoformat()
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 체크포인트 저장 완료: {checkpoint_file}", flush=True)
        return checkpoint_file
    except Exception as e:
        print(f"⚠️ 체크포인트 저장 실패: {e}", flush=True)
        return None

def load_checkpoint(output_dir, timestamp):
    """체크포인트 파일을 로드합니다."""
    try:
        checkpoint_file = os.path.join(output_dir, f"checkpoint_Gemini_{timestamp}.json")
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            print(f"📂 체크포인트 로드 완료: {checkpoint_file}", flush=True)
            return checkpoint_data
        else:
            print(f"📂 체크포인트 파일이 없습니다: {checkpoint_file}", flush=True)
            return None
    except Exception as e:
        print(f"⚠️ 체크포인트 로드 실패: {e}", flush=True)
        return None

def save_intermediate_results(df_results, output_dir, timestamp, suffix=""):
    """중간 결과를 엑셀 파일로 저장합니다."""
    try:
        if suffix:
            filename = f"매출증빙대사결과_Gemini_{timestamp}_{suffix}.xlsx"
        else:
            filename = f"매출증빙대사결과_Gemini_{timestamp}_진행중.xlsx"
        
        output_path = os.path.join(output_dir, filename)
        
        # 완료된 결과만 필터링하여 저장
        completed_results = df_results[df_results['전체결과'].notna()].copy()
        
        if not completed_results.empty:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                completed_results.to_excel(writer, sheet_name='AI_대사결과', index=False)
            
            print(f"💾 중간 결과 저장 완료: {output_path} ({len(completed_results)}건)", flush=True)
            return output_path
        else:
            print(f"⚠️ 저장할 완료된 결과가 없습니다.", flush=True)
            return None
    except Exception as e:
        print(f"⚠️ 중간 결과 저장 실패: {e}", flush=True)
        return None

def find_original_pdf_files(doc_no, original_pdf_dir):
    """전표번호에 해당하는 원본 PDF 파일들을 찾습니다."""
    pdf_files = []
    try:
        for filename in os.listdir(original_pdf_dir):
            if filename.lower().endswith('.pdf'):
                # 전표번호_문서명 형식으로 저장된 파일들에서 해당 전표번호 찾기
                if filename.startswith(f"{doc_no}_") or filename.startswith(doc_no):
                    pdf_files.append(os.path.join(original_pdf_dir, filename))
    except Exception as e:
        print(f"⚠️ 증빙원본 폴더 스캔 중 오류: {e}", flush=True)
    
    return pdf_files

def reconcile_with_pdf_original(erp_info, pdf_files, gemini_model):
    """PDF 원본을 사용하여 대사를 수행합니다."""
    if not pdf_files:
        return {"overall_status": "NO_EVIDENCE", "notes": "PDF 원본 파일 없음"}
    
    try:
        # PDF 파일들을 Gemini에 업로드
        uploaded_files = []
        for pdf_path in pdf_files:
            try:
                uploaded_file = genai.upload_file(pdf_path)
                uploaded_files.append(uploaded_file)
                print(f"✅ PDF 업로드 완료: {os.path.basename(pdf_path)}", flush=True)
            except Exception as e:
                print(f"⚠️ PDF 업로드 실패: {os.path.basename(pdf_path)} - {e}", flush=True)
        
        if not uploaded_files:
            return {"overall_status": "NEEDS_REVIEW", "notes": "PDF 파일 업로드 실패"}
        
        # ERP 데이터 직렬화 처리
        serializable_erp_info = {}
        for key, value in erp_info.items():
            try:
                if pd.isna(value) or value is pd.NaT:
                    serializable_erp_info[key] = ""
                elif isinstance(value, pd.Timestamp):
                    serializable_erp_info[key] = value.isoformat()
                else:
                    serializable_erp_info[key] = value
            except Exception as e:
                serializable_erp_info[key] = str(value) if value is not None else ""
        
        # PDF 대사용 프롬프트 (날짜 매칭 로직 개선)
        pdf_prompt = f"""
        이 PDF 증빙 문서들을 분석하여 ERP 데이터와 대사해주세요.
        
        **ERP 데이터:**
        {json.dumps(serializable_erp_info, indent=2, ensure_ascii=False)}
        
        **날짜 매칭 우선순위 (매출일자 기준):**
        1. **매출일자 (P_Date)**: ERP의 매출일자와 정확히 일치하는 날짜를 우선 찾기
        2. **수출신고일**: 수출신고필증의 날짜는 참고용이므로, 매출일자와 다르면 무시
        3. **기타 날짜**: 송장일자, 배송일자 등은 매출일자와 일치할 때만 사용
        4. **날짜 형식**: YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD 등 다양한 형식 확인
        5. **일치 판단**: ERP 매출일자와 증빙의 날짜가 정확히 일치하면 MATCHED
        6. **불일치 판단**: 매출일자와 다른 날짜만 있으면 MISMATCHED
        
        **인코텀즈별 매출인식일 기준:**
        """
        
        # 인코텀즈 설정을 PDF 프롬프트에도 추가
        for incoterm, config in INCOTERMS_CONFIG.items():
            pdf_prompt += f"- {incoterm}: {config['description']}\n"
        
        pdf_prompt += f"""
        
        **분석 요청사항:**
        1. 금액 (Amount) - ERP 금액과 증빙 금액 비교 (절대값 사용)
        2. 수량 (Quantity) - ERP 수량과 증빙 수량 비교 (정확히 일치)
        3. 날짜 (Date) - ERP 매출일자와 증빙 날짜 비교 (위 우선순위 적용)
        4. 고객사명 (Customer) - ERP 고객사와 증빙 고객사 비교
        
        **중요 사항:**
        - 수출신고필증의 날짜는 수출신고일이므로 매출일자와 다를 수 있음
        - ERP 매출일자와 일치하는 날짜를 찾아야 함
        - 여러 날짜가 있을 때는 매출일자와 일치하는 것을 우선 선택
        
        **응답 형식 (JSON):**
        {{
            "amount_match": "MATCHED/MISMATCHED/NEEDS_REVIEW",
            "quantity_match": "MATCHED/MISMATCHED/NEEDS_REVIEW", 
            "date_match": "MATCHED/MISMATCHED/NEEDS_REVIEW",
            "customer_match": "MATCHED/MISMATCHED/NEEDS_REVIEW",
            "overall_status": "MATCHED/MISMATCHED/NEEDS_REVIEW",
            "evidence_amount": "증빙에서 읽은 금액",
            "evidence_quantity": "증빙에서 읽은 수량",
            "evidence_date": "증빙에서 읽은 날짜",
            "evidence_customer": "증빙에서 읽은 고객사",
            "notes": "상세 분석 결과 및 특이사항"
        }}
        """
        
        # Gemini API 호출 (PDF 파일 포함)
        response = gemini_model.generate_content([pdf_prompt] + uploaded_files)
        
        if not response.text:
            return {"overall_status": "NEEDS_REVIEW", "notes": "PDF 분석 응답 없음"}
        
        # JSON 파싱
        raw_text = response.text.strip()
        raw_text = raw_text.replace('```json', '').replace('```', '').strip()
        
        if raw_text.lower().startswith('json\n'):
            raw_text = raw_text[len('json\n'):].strip()
        elif raw_text.lower().startswith('json'):
            raw_text = raw_text[len('json'):].strip()
        
        result = json.loads(raw_text)
        result["notes"] = f"[PDF 원본 분석] {result.get('notes', '')}"
        return result
        
    except Exception as e:
        print(f"❌ PDF 원본 대사 실패: {e}", flush=True)
        return {"overall_status": "NEEDS_REVIEW", "notes": f"PDF 원본 대사 오류: {e}"}

def save_results_to_excel(df_results, output_path, sheet_name='AI_대사결과'):
    """결과를 엑셀 파일로 저장"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_results.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"✅ 결과 저장 완료: {output_path}", flush=True)
        return True
    except Exception as e:
        print(f"❌ 결과 저장 실패: {e}", flush=True)
        return False

# 엑셀 알파벳 → 인덱스 변환 함수
def column_to_index(column_str):
    column_str = column_str.upper()
    result = 0
    for char in column_str:
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1

# 엑셀 헤더-알파벳 매핑 진단 함수
# config_columns: config에서 사용하는 컬럼 알파벳 dict
# file_path: 진단할 엑셀 파일 경로
# sheet_name: 시트명(기본값 None)
def debug_excel_header(file_path, config_columns, sheet_name=None):
    import pandas as pd
    try:
        df = pd.read_excel(file_path, nrows=1, sheet_name=sheet_name)  # 헤더만 읽기
        if isinstance(df, dict):  # 여러 시트 반환시 첫 시트 사용
            df = list(df.values())[0]
        headers = list(df.columns)
        print("\n[엑셀 헤더 진단 결과]")
        print("엑셀 파일 헤더:", headers)
        for key, col_alpha in config_columns.items():
            idx = column_to_index(col_alpha)
            if idx < len(headers):
                actual_header = headers[idx]
                print(f"[{key}] config: {col_alpha} → 엑셀 헤더: '{actual_header}'")
            else:
                print(f"[{key}] config: {col_alpha} → ❌ 엑셀에 해당 열 없음 (인덱스 {idx})")
    except Exception as e:
        print(f"[진단 오류] 엑셀 헤더 진단 중 오류 발생: {e}")

def run_ai_reconciliation_gemini(
    input_excel_path=None,
    output_dir=None,
    ocr_json_dir=None,
    original_pdf_dir=None,  # 증빙원본 폴더 추가
    doc_no_column_name='Doc_No',
    progress_callback=None,
    stop_flag=None
):
    print(f"[함수] run_ai_reconciliation_gemini 시작", flush=True)
    print(f"[매개변수] input_excel_path: {input_excel_path}", flush=True)
    print(f"[매개변수] ocr_json_dir: {ocr_json_dir}", flush=True)
    print(f"[매개변수] original_pdf_dir: {original_pdf_dir}", flush=True)
    print(f"[매개변수] output_dir: {output_dir}", flush=True)
    print(f"[매개변수] doc_no_column_name: {doc_no_column_name}", flush=True)
    """
    Gemini AI 대사 실행 함수
    
    Args:
        input_excel_path: 입력 엑셀 파일 경로
        output_dir: 결과 저장 디렉토리
        ocr_json_dir: OCR JSON 파일 디렉토리
        doc_no_column_name: 전표번호 컬럼명
        progress_callback: 진행률 콜백 함수
        stop_flag: 중단 플래그
    """
    # 필수 경로 검증
    if input_excel_path is None:
        print("❌ 오류: 입력 엑셀 파일 경로가 지정되지 않았습니다.", flush=True)
        return False
    if output_dir is None:
        print("❌ 오류: 출력 디렉토리가 지정되지 않았습니다.", flush=True)
        return False
    if ocr_json_dir is None:
        print("❌ 오류: OCR JSON 디렉토리가 지정되지 않았습니다.", flush=True)
        return False
    if original_pdf_dir is None:
        print("❌ 오류: 증빙원본 디렉토리가 지정되지 않았습니다.", flush=True)
        return False
    
    # 출력 파일 경로 설정 (타임스탬프 포함)
    timestamp = datetime.now().strftime('%Y%m%d%H%M')  # YYYYMMDDHHMM 형식
    output_excel_filename = f'매출증빙대사결과_Gemini_{timestamp}.xlsx'
    output_excel_path = os.path.join(output_dir, output_excel_filename)
    
    # 기존 체크포인트 자동 감지 (프로그램 재시작 시에도 감지)
    existing_checkpoints = []
    try:
        for file in os.listdir(output_dir):
            if file.startswith("checkpoint_Gemini_") and file.endswith(".json"):
                file_path = os.path.join(output_dir, file)
                file_time = os.path.getmtime(file_path)
                existing_checkpoints.append((file, file_time))
    except Exception as e:
        print(f"⚠️ 체크포인트 파일 스캔 중 오류: {e}", flush=True)
    
    checkpoint_data = None
    resume_from_index = 0
    completed_docs = []
    
    # 가장 최근 체크포인트 찾기
    if existing_checkpoints:
        # 파일 수정 시간 기준으로 가장 최근 체크포인트 선택
        latest_checkpoint = max(existing_checkpoints, key=lambda x: x[1])
        checkpoint_filename = latest_checkpoint[0]
        
        # 타임스탬프 추출 (checkpoint_Gemini_202501171430.json → 202501171430)
        timestamp_from_file = checkpoint_filename.replace("checkpoint_Gemini_", "").replace(".json", "")
        
        print(f"📂 기존 체크포인트 발견: {checkpoint_filename}", flush=True)
        checkpoint_data = load_checkpoint(output_dir, timestamp_from_file)
        
        if checkpoint_data:
            print(f"📂 체크포인트 정보: {checkpoint_data['completed_count']}/{checkpoint_data['total_count']} 완료", flush=True)
            resume_from_index = checkpoint_data['completed_count']
            completed_docs = checkpoint_data['completed_docs']
            print(f"🔄 {resume_from_index}번째 전표부터 이어서 진행합니다.", flush=True)
            
            # 현재 타임스탬프를 기존 체크포인트의 타임스탬프로 설정
            timestamp = timestamp_from_file
        else:
            print(f"⚠️ 체크포인트 파일 로드 실패, 새로 시작합니다.", flush=True)
    else:
        print(f"📂 기존 체크포인트가 없습니다. 새로 시작합니다.", flush=True)
    
    print(f"[시작] 매출 증빙 대사 시작 (Gemini) - 2단계 프로세스 - {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print(f"[파일] 입력 파일: {input_excel_path}", flush=True)
    print(f"[폴더] OCR 폴더: {ocr_json_dir}", flush=True)
    print(f"[폴더] 증빙원본 폴더: {original_pdf_dir}", flush=True)
    print(f"[폴더] 출력 폴더: {output_dir}", flush=True)

    # 1. Gemini API 초기화
    print(f"🔍 Gemini API 초기화 시작: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    gemini_model = initialize_gemini_api()
    if gemini_model is None:
        print(f"❌ Gemini API 초기화 실패: {datetime.now().strftime('%H:%M:%S')}", flush=True)
        return False
    print(f"✅ Gemini API 초기화 완료: {datetime.now().strftime('%H:%M:%S')}", flush=True)

    # 2. 원본 엑셀 파일 로드
    df_original = load_excel_robustly(input_excel_path)

    if df_original is None:
        print("엑셀 파일을 로드하지 못하여 스크립트를 종료합니다.", flush=True)
        return False

    # 3. 전표번호 컬럼 확인 및 필터링
    if doc_no_column_name in df_original.columns:
        # 필터링할 Doc_No 값들을 문자열 리스트로 정의 (엑셀의 '총합계'와 같은 값). 대소문자 무시를 위해 .lower() 사용
        doc_nos_to_exclude = ['총합계', '합계', 'summary', 'total'] # 실제 엑셀에 있는 집계 값들을 추가하세요.
        
        # Doc_No 컬럼을 문자열로 변환하고 소문자로 만든 후 필터링
        df_original_filtered = df_original[~df_original[doc_no_column_name].astype(str).str.lower().isin(doc_nos_to_exclude)].copy()
        
        if len(df_original_filtered) < len(df_original):
            print(f"✅ 유효하지 않은 Doc_No (총합계 등) 필터링 완료. {len(df_original) - len(df_original_filtered)}건 제외됨.", flush=True)
            df_original = df_original_filtered # 필터링된 DataFrame으로 교체
        else:
            print("ℹ️ Doc_No 필터링 결과, 제외된 건수가 없습니다.", flush=True)
    else:
        print(f"⚠️ 경고: '{doc_no_column_name}' 컬럼을 찾을 수 없어 Doc_No 필터링을 건너뜝니다.", flush=True)

    print(f"✅ 원본 엑셀 로딩 완료: {input_excel_path} / 처리 대상 건수: {len(df_original)}", flush=True)

    # 4. 결과 DataFrame 준비 (원본 데이터를 복사하여 시작)
    df_results = df_original.copy()

    # 5. AI 대사 결과 컬럼 추가 (마지막 열 다음부터)
    for col in RECONCILIATION_COLUMNS:
        df_results[col] = ''
    
    # 증빙에서 읽어온 실제 값들을 표시할 컬럼들 추가
    for col in EVIDENCE_VALUE_COLUMNS:
        df_results[col] = ''
    
    # 체크포인트가 있으면 기존 결과 파일에서 복원
    if checkpoint_data:
        try:
            # 기존 결과 파일 찾기
            existing_result_files = [f for f in os.listdir(output_dir) 
                                   if f.startswith(f"매출증빙대사결과_Gemini_{timestamp}") and f.endswith('.xlsx')]
            
            if existing_result_files:
                # 가장 최근 파일 사용
                latest_file = max(existing_result_files, key=lambda x: os.path.getmtime(os.path.join(output_dir, x)))
                existing_result_path = os.path.join(output_dir, latest_file)
                
                print(f"📂 기존 결과 파일 로드: {existing_result_path}", flush=True)
                existing_df = load_excel_robustly(existing_result_path)
                
                if existing_df is not None:
                    # 기존 결과를 현재 DataFrame에 병합
                    for col in RECONCILIATION_COLUMNS + EVIDENCE_VALUE_COLUMNS:
                        if col in existing_df.columns:
                            df_results[col] = existing_df[col]
                    
                    print(f"✅ 기존 결과 복원 완료: {len(completed_docs)}건", flush=True)
                else:
                    print(f"⚠️ 기존 결과 파일 로드 실패, 새로 시작합니다.", flush=True)
        except Exception as e:
            print(f"⚠️ 기존 결과 복원 중 오류: {e}, 새로 시작합니다.", flush=True)

    # 6. 각 전표(Doc_No) 처리 루프 (OCR JSON 파일 연동 및 실제 Gemini API 호출)
    total_docs = len(df_original)
    no_evidence_docs = []  # 증빙이 없는 전표번호들을 수집
    processed_docs = 0     # 실제 처리된 전표 수
    
    for index, row_data in df_original.iterrows(): # 필터링된 df_original을 순회합니다.
        # 체크포인트에서 이어서 진행하는 경우, 이미 완료된 전표는 건너뛰기
        if index < resume_from_index:
            continue
            
        # 중단 플래그 확인
        if stop_flag and stop_flag.get():
            print("⏹️ AI 대사가 중단되었습니다.", flush=True)
            break
            
        current_doc_no = str(row_data[doc_no_column_name]) # 전표번호는 문자열로 처리하는 것이 안전합니다.

        # 진행률 콜백 호출 (시작 시)
        if progress_callback:
            progress_callback(index + 1, total_docs, current_doc_no)

        # 전체 전표 처리 과정을 try-except로 감싸서 오류 발생 시 다음 전표로 진행
        try:
            # 7. 해당 전표에 맞는 OCR 결과 JSON 파일 로드
            ocr_json_file_path = os.path.join(ocr_json_dir, f"{current_doc_no}.json") # 전표번호.json 파일명 가정

            ocr_data = None
            gemini_result = {} # Gemini 결과 초기화 (API 호출 실패 시 기본값)
            
            try:
                with open(ocr_json_file_path, 'r', encoding='utf-8') as f:
                    ocr_data = json.load(f)
                # 증빙이 있는 경우에만 상세 로그 출력
                print(f"\n[AI] Gemini 호출 중: Doc_No {current_doc_no} ({index + 1}/{total_docs})", flush=True)
                print(f"✅ OCR JSON 파일 로딩 완료: {ocr_json_file_path}", flush=True)
            except FileNotFoundError:
                # 증빙이 없는 경우 개별 로그 대신 수집만
                no_evidence_docs.append(current_doc_no)
                gemini_result = {"overall_status": "NO_EVIDENCE", "notes": "OCR 데이터 파일 없음"}
                ocr_data = None # OCR 데이터가 없음을 명시
                # 다음 전표로 넘어가기 위해 continue 대신 DataFrame 업데이트 후 계속
            except json.JSONDecodeError:
                print(f"❌ 오류: OCR JSON 파일 '{ocr_json_file_path}'의 형식이 올바르지 않습니다. 이 전표는 건너뜁니다.", flush=True)
                gemini_result = {"overall_status": "NEEDS_REVIEW", "notes": "OCR 데이터 JSON 형식 오류"}
                ocr_data = None
            except Exception as e:
                print(f"❌ OCR JSON 파일 로딩 중 예상치 못한 오류: {e}", flush=True)
                gemini_result = {"overall_status": "NEEDS_REVIEW", "notes": f"OCR 데이터 로딩 오류: {e}"}
                ocr_data = None

            # 8. Gemini API에 보낼 프롬프트 구성 및 실제 호출
            if ocr_data is not None: # OCR 데이터가 성공적으로 로드된 경우에만 Gemini 호출 시도
                processed_docs += 1  # 실제 처리된 전표 수 증가
                erp_info = row_data.to_dict() # 엑셀 한 줄의 모든 ERP 정보를 딕셔너리로
                
                # Pandas Timestamp 객체를 JSON 직렬화 가능한 문자열로 변환 (TypeError 해결)
                serializable_erp_info = {}
                for key, value in erp_info.items():
                    try:
                        if pd.isna(value) or value is pd.NaT:
                            # NaT 또는 NaN 값은 빈 문자열로 처리
                            serializable_erp_info[key] = ""
                        elif isinstance(value, pd.Timestamp):
                            serializable_erp_info[key] = value.isoformat() # ISO 8601 형식 문자열로 변환
                        else:
                            serializable_erp_info[key] = value
                    except Exception as e:
                        # 기타 직렬화 불가능한 값들은 문자열로 변환
                        print(f"⚠️ 직렬화 오류 (Doc_No: {current_doc_no}, 컬럼: {key}): {e}", flush=True)
                        serializable_erp_info[key] = str(value) if value is not None else ""

                all_parsed_texts = []
                if 'documents' in ocr_data and isinstance(ocr_data['documents'], list):
                    for doc in ocr_data['documents']:
                        if 'parsed_text' in doc and isinstance(doc['parsed_text'], str):
                            all_parsed_texts.append(doc['parsed_text'])
                
                combined_ocr_text = "\n\n--- OCR Evidence Documents ---\n\n" + "\n\n".join(all_parsed_texts)

                # English prompt to reduce token usage
                json_response_example = json.dumps({
                  "amount_match": "MATCHED",
                  "quantity_match": "MATCHED", 
                  "date_match": "MATCHED",
                  "customer_match": "MATCHED",
                  "overall_status": "MATCHED",
                  "evidence_amount": "1,000,000 KRW",
                  "evidence_quantity": "100 units",
                  "evidence_date": "2024-01-15",
                  "evidence_customer": "ABC Company Ltd.",
                  "notes": "All data matches with evidence documents"
                }, indent=2)

                gemini_prompt = (
                    f"Compare ERP transaction data with OCR evidence documents.\n\n"
                    f"**Reconciliation Rules:**\n"
                    f"- Amount: Compare absolute values (ERP negative amounts = positive in evidence for sales specification)\n"
                    f"- Quantity: Exact match required\n"
                    f"- Date: Check revenue recognition date based on Incoterms\n"
                    f"- Customer: Compare customer/supplier name\n"
                    f"- Overall: Overall assessment\n"
                    f"- Notes: Key findings, discrepancies, and special comments\n\n"
                    f"**Date Matching Priority (매출일자 기준):**\n"
                    f"1. **매출일자 (P_Date)**: ERP의 매출일자와 정확히 일치하는 날짜를 우선 찾기\n"
                    f"2. **수출신고일**: 수출신고필증의 날짜는 참고용이므로, 매출일자와 다르면 무시\n"
                    f"3. **기타 날짜**: 송장일자, 배송일자 등은 매출일자와 일치할 때만 사용\n"
                    f"4. **날짜 형식**: YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD 등 다양한 형식 확인\n"
                    f"5. **일치 판단**: ERP 매출일자와 증빙의 날짜가 정확히 일치하면 MATCHED\n"
                    f"6. **불일치 판단**: 매출일자와 다른 날짜만 있으면 MISMATCHED\n\n"
                    f"**Revenue Recognition Date (Incoterms 기준):**\n"
                    f"- C/F 조건 (CFR, CIF, CPT, CIP): 선적일 기준 매출인식\n"
                    f"- EXW 조건: 공장출고일 기준 매출인식 (공장출고증/이메일)\n"
                    f"- F 조건 (FCA, FAS, FOB): 선적일 또는 운송인인도일 기준\n"
                    f"- D 조건 (DAP, DPU, DDP): 도착일 또는 하역완료일 기준\n\n"
                    f"**인코텀즈별 매출인식일 상세 기준:**\n"
                )
                
                # 인코텀즈 설정을 프롬프트에 추가
                for incoterm, config in INCOTERMS_CONFIG.items():
                    gemini_prompt += f"- {incoterm}: {config['description']}\n"
                
                gemini_prompt += (
                    f"**Important Notes:**\n"
                    f"- For sales specification: ERP amounts are debit-based (negative = positive actual amount)\n"
                    f"- Use absolute values for amount comparison\n"
                    f"- **날짜 매칭 시 주의**: 수출신고필증의 날짜는 수출신고일이므로 매출일자와 다를 수 있음\n"
                    f"- **올바른 날짜 선택**: ERP 매출일자와 일치하는 날짜를 찾아야 함\n"
                    f"- Check for date format variations (YYYY-MM-DD, YYYY.MM.DD, etc.)\n"
                    f"- Customer names may have slight variations (abbreviations, spacing)\n\n"
                    f"**Status Options:**\n"
                    f"- MATCHED: Data matches exactly or within acceptable tolerance\n"
                    f"- MISMATCHED: Clear discrepancy found\n"
                    f"- NEEDS_REVIEW: Requires manual review\n"
                    f"- NO_EVIDENCE: No supporting evidence found\n\n"
                    f"**Required Response Format:**\n"
                    f"You MUST include the actual values found in evidence documents:\n"
                    f"- evidence_amount: The actual amount found in evidence (e.g., '1,000,000 KRW')\n"
                    f"- evidence_quantity: The actual quantity found in evidence (e.g., '100 units')\n"
                    f"- evidence_date: The actual date found in evidence (e.g., '2024-01-15')\n"
                    f"- evidence_customer: The actual customer name found in evidence (e.g., 'ABC Company Ltd.')\n\n"
                    f"**Date Matching Instructions:**\n"
                    f"- ERP 매출일자(P_Date)를 기준으로 증빙에서 일치하는 날짜를 찾기\n"
                    f"- 수출신고필증의 날짜는 수출신고일이므로 매출일자와 다를 수 있음\n"
                    f"- 여러 날짜가 있을 때는 매출일자와 일치하는 것을 우선 선택\n"
                    f"- 매출일자와 일치하는 날짜가 없으면 MISMATCHED로 판단\n\n"
                    f"For MISMATCHED items, provide detailed notes explaining:\n"
                    f"- What specific differences were found\n"
                    f"- Which values need to be checked\n"
                    f"- What actions should be taken for verification\n\n"
                    f"--- ERP Data ---\n{json.dumps(serializable_erp_info, indent=2, ensure_ascii=False)}\n\n"
                    f"--- Evidence Documents ---\n{combined_ocr_text}\n\n"
                    f"Return JSON with status for each category and evidence values.\n"
                    f"Example format:\n{json_response_example}\n"
                )
                
                # 9. 실제 Gemini API 호출
                try:
                    response = gemini_model.generate_content(gemini_prompt)
                    
                    # 응답이 비어있거나, 텍스트가 없을 경우에 대한 처리
                    if not response.text:
                        raise ValueError("Gemini API가 빈 응답을 반환했습니다.")
                        
                    raw_gemini_text = response.text.strip() # 응답 텍스트의 앞뒤 공백 제거
                    
                    # Gemini가 응답을 Markdown JSON 블록으로 감싸는 경우 처리 (더 강력한 처리)
                    raw_gemini_text = raw_gemini_text.replace('```json', '').replace('```', '').strip()
                    if raw_gemini_text.lower().startswith('json\n'):
                        raw_gemini_text = raw_gemini_text[len('json\n'):].strip()
                    elif raw_gemini_text.lower().startswith('json'):
                         raw_gemini_text = raw_gemini_text[len('json'):].strip()
                    
                    # Gemini 응답 텍스트를 JSON으로 파싱
                    gemini_result = json.loads(raw_gemini_text)
                    
                    print(f"[완료] Gemini OCR 응답 완료 (Doc_No: {current_doc_no})", flush=True)
                    
                    # 진행률 콜백 호출 (OCR 완료 시)
                    if progress_callback:
                        progress_callback(index + 1, total_docs, f"{current_doc_no} (OCR 완료)")
                    
                    # 토큰 사용량 로그 출력 (응답 메타데이터가 있을 경우)
                    if hasattr(response, 'usage_metadata') and response.usage_metadata:
                        print(f"   - 입력 토큰: {response.usage_metadata.prompt_token_count}, 출력 토큰: {response.usage_metadata.candidates_token_count}", flush=True)
                    else:
                        print("   - 토큰 사용량 정보 없음 (응답 메타데이터 부재).", flush=True)

                    # 2단계: OCR 결과가 불확실한 경우 PDF 원본으로 재검증
                    if gemini_result.get("overall_status") in ["NEEDS_REVIEW", "MISMATCHED"]:
                        print(f"🔄 OCR 결과 불확실 - PDF 원본으로 재검증 시작 (Doc_No: {current_doc_no})", flush=True)
                        
                        try:
                            # 해당 전표번호의 PDF 원본 파일들 찾기
                            pdf_files = find_original_pdf_files(current_doc_no, original_pdf_dir)
                            
                            if pdf_files:
                                print(f"   - PDF 원본 파일 발견: {len(pdf_files)}개", flush=True)
                                for pdf_file in pdf_files:
                                    print(f"     • {os.path.basename(pdf_file)}", flush=True)
                                
                                # PDF 원본으로 재검증
                                pdf_result = reconcile_with_pdf_original(serializable_erp_info, pdf_files, gemini_model)
                                
                                # PDF 결과가 더 확실한 경우 OCR 결과를 대체
                                if pdf_result.get("overall_status") in ["MATCHED", "MISMATCHED"]:
                                    print(f"   ✅ PDF 원본 분석 완료 - OCR 결과 대체", flush=True)
                                    gemini_result = pdf_result
                                    
                                    # 진행률 콜백 호출 (PDF 분석 완료 시)
                                    if progress_callback:
                                        progress_callback(index + 1, total_docs, f"{current_doc_no} (PDF 분석 완료)")
                                else:
                                    print(f"   ⚠️ PDF 원본 분석도 불확실 - OCR 결과 유지", flush=True)
                            else:
                                print(f"   ⚠️ PDF 원본 파일 없음 - OCR 결과 유지", flush=True)
                        except Exception as pdf_error:
                            print(f"   ⚠️ PDF 원본 재검증 중 오류 (Doc_No: {current_doc_no}): {pdf_error}", flush=True)
                            # PDF 재검증 실패 시 OCR 결과 유지

                    # API 호출 간 잠시 대기 (무료 사용량 한도 초과 방지 및 안정적인 호출을 위함)
                    time.sleep(1) # 1초 대기 (필요에 따라 조절)

                except json.JSONDecodeError as json_error:
                    print(f"❌ Gemini 응답 파싱 오류 (Doc_No: {current_doc_no}): Gemini가 유효한 JSON을 반환하지 않았습니다. 원본 텍스트 시작: '{raw_gemini_text[:200]}'...", flush=True)
                    gemini_result = {"overall_status": "NEEDS_REVIEW", "notes": f"Gemini 응답 JSON 파싱 오류: {json_error}"}
                except Exception as e:
                    print(f"❌ Gemini API 호출 실패 (Doc_No: {current_doc_no}): {e}", flush=True)
                    gemini_result = {"overall_status": "NEEDS_REVIEW", "notes": f"API 호출 오류: {e}"}
            else:
                # OCR 데이터 로딩 자체가 실패한 경우 (gemini_result는 이미 위에서 설정됨)
                print(f"⚠️ Doc_No {current_doc_no}: OCR 데이터 문제로 Gemini 호출 건너뜀.", flush=True)

            # 10. df_results DataFrame의 현재 처리 중인 행을 업데이트합니다.
            row_idx_in_results = index

            # 각 대사 항목 결과 업데이트
            for col in RECONCILIATION_COLUMNS:
                if col == "전체결과":
                    # 전체결과 컬럼은 overall_status의 한글 버전
                    if "overall_status" in gemini_result:
                        status = gemini_result["overall_status"]
                        
                        # 영어 상태를 한글로 변환
                        korean_status = ""
                        if status == "MATCHED":
                            korean_status = "일치"
                        elif status == "MISMATCHED":
                            korean_status = "불일치"
                        elif status == "NEEDS_REVIEW":
                            korean_status = "확인필요"
                        elif status == "NO_EVIDENCE":
                            korean_status = "증빙없음"
                        else: # 기타 상태
                            korean_status = "확인필요"

                        df_results.loc[row_idx_in_results, col] = korean_status
                    else:
                        df_results.loc[row_idx_in_results, col] = '데이터없음'
                elif col in gemini_result:
                    status = gemini_result[col]
                    
                    # 영어 상태를 한글로 변환
                    korean_status = ""
                    if status == "MATCHED":
                        korean_status = "일치"
                    elif status == "MISMATCHED":
                        korean_status = "불일치"
                    elif status == "NEEDS_REVIEW":
                        korean_status = "확인필요"
                    elif status == "NO_EVIDENCE":
                        korean_status = "증빙없음"
                    else: # 기타 상태
                        korean_status = "확인필요"

                    df_results.loc[row_idx_in_results, col] = korean_status
                else:
                    # Gemini 결과에 해당 카테고리가 없는 경우
                    df_results.loc[row_idx_in_results, col] = '데이터없음'
            
            # 증빙에서 읽어온 실제 값들 업데이트
            for col in EVIDENCE_VALUE_COLUMNS:
                if col in gemini_result:
                    evidence_value = gemini_result[col]
                    df_results.loc[row_idx_in_results, col] = evidence_value
                else:
                    # Gemini 결과에 해당 증빙 값이 없는 경우
                    df_results.loc[row_idx_in_results, col] = ''

            print(f"✅ Doc_No {current_doc_no} 결과 DataFrame 업데이트 완료.", flush=True)
            
            # 체크포인트 저장 (CHECKPOINT_INTERVAL마다)
            processed_docs += 1
            
            # 실시간 진행 중인 결과 파일 저장 (매번 업데이트)
            save_intermediate_results(df_results, output_dir, timestamp, "")
            
            # 주기적 체크포인트 저장 (CHECKPOINT_INTERVAL마다)
            if processed_docs % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(df_results, output_dir, processed_docs, total_docs, timestamp)
                save_intermediate_results(df_results, output_dir, timestamp, f"{processed_docs}건완료")
                print(f"💾 체크포인트 및 중간 결과 저장 완료 ({processed_docs}/{total_docs})", flush=True)
            
        except Exception as e:
            # 전체 전표 처리 과정에서 예상치 못한 오류 발생 시
            print(f"❌ 전표 처리 중 예상치 못한 오류 (Doc_No: {current_doc_no}): {e}", flush=True)
            print(f"⚠️ 해당 전표를 건너뛰고 다음 전표로 진행합니다.", flush=True)
            
            # 오류 발생 시 기본 결과 설정
            gemini_result = {"overall_status": "NEEDS_REVIEW", "notes": f"처리 중 오류 발생: {e}"}
            
            # DataFrame 업데이트 (오류가 발생해도 결과는 기록)
            row_idx_in_results = index
            for col in RECONCILIATION_COLUMNS:
                if col == "전체결과":
                    df_results.loc[row_idx_in_results, col] = "확인필요"
                else:
                    df_results.loc[row_idx_in_results, col] = "확인필요"
            
            for col in EVIDENCE_VALUE_COLUMNS:
                df_results.loc[row_idx_in_results, col] = ""
            
            print(f"✅ Doc_No {current_doc_no} 오류 처리 완료 - 다음 전표로 진행", flush=True)

    # 11. 증빙이 없는 전표들에 대한 요약 로그 출력
    if no_evidence_docs:
        print(f"\n📊 증빙이 없는 전표 요약:", flush=True)
        print(f"   - 총 {len(no_evidence_docs)}건의 전표에 증빙이 없습니다.", flush=True)
        if len(no_evidence_docs) <= 10:
            print(f"   - 전표번호: {', '.join(no_evidence_docs)}", flush=True)
        else:
            print(f"   - 전표번호 (처음 10개): {', '.join(no_evidence_docs[:10])}...", flush=True)
            print(f"   - 나머지 {len(no_evidence_docs) - 10}건은 생략", flush=True)
    
    print(f"\n📈 처리 결과 요약:", flush=True)
    print(f"   - 총 전표: {total_docs}건", flush=True)
    print(f"   - AI 처리: {processed_docs}건", flush=True)
    print(f"   - 증빙 없음: {len(no_evidence_docs)}건", flush=True)

    # 12. 최종 DataFrame을 엑셀 파일로 저장
    try:
        save_results_to_excel(df_results, output_excel_path)
        
        # 최종 체크포인트 저장 및 정리
        save_checkpoint(df_results, output_dir, total_docs, total_docs, timestamp)
        save_intermediate_results(df_results, output_dir, timestamp, "완료")
        
        # 체크포인트 파일 정리 (최종 완료 시)
        checkpoint_file = os.path.join(output_dir, f"checkpoint_Gemini_{timestamp}.json")
        if os.path.exists(checkpoint_file):
            try:
                os.remove(checkpoint_file)
                print(f"🧹 체크포인트 파일 정리 완료", flush=True)
            except Exception as e:
                print(f"⚠️ 체크포인트 파일 정리 실패: {e}", flush=True)
        
        print(f"🎉 AI 대사 완료! 최종 결과: {output_excel_path}", flush=True)
        return True
    except Exception as e:
        print(f"❌ 엑셀 파일 저장 중 오류 발생: {e}", flush=True)
        return False

# 스크립트로 직접 실행될 때의 처리
if __name__ == "__main__":
    print(f"[디버깅] 명령행 인수 개수: {len(sys.argv)}", flush=True)
    for i, arg in enumerate(sys.argv):
        print(f"[디버깅] 인수[{i}]: {arg}", flush=True)
    
    # 명령행 인수 처리 (2단계 프로세스 지원)
    if len(sys.argv) > 1:
        # 명령행에서 인수 받기
        input_path = sys.argv[1] if len(sys.argv) > 1 else None
        ocr_path = sys.argv[2] if len(sys.argv) > 2 else None
        original_path = sys.argv[3] if len(sys.argv) > 3 else None  # 증빙원본 폴더 추가
        output_path = sys.argv[4] if len(sys.argv) > 4 else None
        doc_no_col = sys.argv[5] if len(sys.argv) > 5 else 'Doc_No'
        
        print(f"[디버깅] 파싱된 인수:", flush=True)
        print(f"  - input_path: {input_path}", flush=True)
        print(f"  - ocr_path: {ocr_path}", flush=True)
        print(f"  - original_path: {original_path}", flush=True)
        print(f"  - output_path: {output_path}", flush=True)
        print(f"  - doc_no_col: {doc_no_col}", flush=True)
        
        success = run_ai_reconciliation_gemini(
            input_excel_path=input_path,
            output_dir=output_path,
            ocr_json_dir=ocr_path,
            original_pdf_dir=original_path,  # 증빙원본 폴더 추가
            doc_no_column_name=doc_no_col
        )
    else:
        # 기본값으로 실행 (하드코딩된 경로 사용)
        print("[디버깅] 기본값으로 실행", flush=True)
        print("⚠️ 명령행 인수가 없어 하드코딩된 경로를 사용합니다.", flush=True)
        success = run_ai_reconciliation_gemini(
            input_excel_path='D:/CJ/11.자동화/매출증빙대사/01_전표목록/매출명세서_테스트용.xlsx',
            output_dir='D:/CJ/11.자동화/매출증빙대사/05_AI대사결과/',
            ocr_json_dir='D:/CJ/11.자동화/매출증빙대사/03_OCR결과_테스트/',
            original_pdf_dir='D:/CJ/11.자동화/매출증빙대사/02_증빙다운로드/'
        )
    
    if success:
        print("✅ Gemini AI 대사 완료! (2단계 프로세스)", flush=True)
    else:
        print("❌ Gemini AI 대사 실패!", flush=True)
        sys.exit(1)