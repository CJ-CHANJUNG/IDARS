import os
import glob
import time
import json
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
from google.protobuf.json_format import MessageToDict
from pypdf import PdfReader, PdfWriter # PDF 분할을 위한 라이브P
# --- 1. [필수] 사용자 설정 변수 ---
# 1-1. 서비스 계정 키 파일 경로 (JSON)
# [사용자 설정 완료]
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"D:\CJ\Project Manager\IDARS\IDARS PJT\document-ai-gcs-connector-key.json"

# 1-2. GCP 프로젝트 및 리소스 정보
PROJECT_ID = "concrete-fabric-465212-n3" # (이전 정보에서 확인)
LOCATION = "us" # (이전 정보에서 확인)
SPLITTER_PROCESSOR_ID = "87937bc0c460cb85" # (이전 정보에서 확인)

# 1-3. 로컬 폴더 경로
# [사용자 설정 완료]
LOCAL_INPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\Data\Input_Documents_To_Split"
LOCAL_OUTPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\Data\Extractor_Training_Data"

# 1-4. GCS 버킷 경로 (임시 처리용)
# [사용자 설정 완료]
GCS_INPUT_BUCKET = "idars-splitter-input"
# [가정] GCS Output 버킷 이름을 'idars-splitter-output'으로 가정합니다. 
# GCP에서 생성되었는지 확인하세요. (만약 다르다면 이 라인을 수정하세요.)
GCS_OUTPUT_BUCKET = "idars-splitter-output" 

WEEKLY_BATCH_ID = f"batch_{time.strftime('%Y%m%d_%H%M%S')}" # 고유 배치 ID
# --- [필수] 설정 종료 ---


def upload_files_to_gcs(local_path: str, bucket_name: str, gcs_prefix: str) -> list[str]:
    """로컬 폴더의 모든 PDF를 GCS로 업로드합니다."""
    print(f"[{time.strftime('%H:%M:%S')}] 1. 로컬 파일 업로드 시작...")
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    
    local_pdf_files = glob.glob(os.path.join(local_path, "*.pdf"))
    if not local_pdf_files:
        print(f"🛑 오류: '{local_path}' 폴더에서 PDF 파일을 찾을 수 없습니다.")
        return []

    print(f"    총 {len(local_pdf_files)}개의 PDF 파일을 GCS로 업로드합니다...")
    gcs_uris = []
    for local_file in local_pdf_files:
        file_name = os.path.basename(local_file)
        gcs_path = f"{gcs_prefix}/{file_name}"
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(local_file)
        gcs_uris.append(f"gs://{bucket_name}/{gcs_path}")

    print(f"[{time.strftime('%H:%M:%S')}] ✅ GCS 업로드 완료.")
    return gcs_uris

def run_splitter_batch_process(processor_id: str, gcs_input_uris: list[str], gcs_output_bucket: str, gcs_output_prefix: str) -> (str, str):
    """DMS Splitter 배치 처리를 요청하고, 완료 후 매니페스트 GCS 경로를 반환합니다."""
    print(f"[{time.strftime('%H:%M:%S')}] 2. DMS Splitter 배치 처리 요청...")
    
    docai_client = documentai.DocumentProcessorServiceClient(client_options={"api_endpoint": f"{LOCATION}-documentai.googleapis.com"})
    processor_name = docai_client.processor_path(PROJECT_ID, LOCATION, processor_id)

    input_documents = [documentai.GcsDocument(gcs_uri=uri, mime_type="application/pdf") for uri in gcs_input_uris]
    input_config = documentai.BatchDocumentsInputConfig(gcs_documents=documentai.GcsDocuments(documents=input_documents))
    
    output_gcs_uri = f"gs://{gcs_output_bucket}/{gcs_output_prefix}/"
    output_config = documentai.DocumentOutputConfig(gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(gcs_uri=output_gcs_uri))

    request = documentai.BatchProcessRequest(name=processor_name, input_documents=input_config, document_output_config=output_config)
    operation = docai_client.batch_process_documents(request)
    print(f"    작업 시작됨. 완료까지 대기합니다...")
    
    try:
        operation.result(timeout=1800) # 30분
        print(f"[{time.strftime('%H:%M:%S')}] ✅ DMS Splitter 배치 처리 완료.")
        
        # 매니페스트 파일 생성
        manifest_gcs_path = save_batch_manifest(
            operation_metadata=operation.metadata,
            bucket_name=gcs_output_bucket,
            output_prefix=gcs_output_prefix
        )
        return output_gcs_uri, manifest_gcs_path
        
    except Exception as e:
        print(f"🛑 오류: 배치 처리 실패 - {e}")
        return None, None

def save_batch_manifest(operation_metadata: documentai.BatchProcessMetadata, bucket_name: str, output_prefix: str) -> str:
    """배치 처리 완료 후, 입력/출력 매핑 매니페스트 JSON 파일을 GCS에 저장합니다."""
    print(f"[{time.strftime('%H:%M:%S')}] 3. 배치 매니페스트 파일 생성 시작...")
    storage_client = storage.Client(project=PROJECT_ID)
    mapping = {}
    metadata_dict = MessageToDict(operation_metadata._pb)
    
    for status in metadata_dict.get('individualProcessStatuses', []):
        try:
            input_uri = status.get('inputGcsSource')
            output_uri = status.get('outputGcsDestination') # 예: gs://.../1
            original_filename = os.path.basename(input_uri)
            output_folder_index = output_uri.strip('/').split('/')[-1]
            
            # [버그 수정] 
            # output_uri가 gs://.../1 처럼 '/' 없이 끝나는 것을 가정하여
            # output-document.json 앞에 '/'를 명시적으로 추가합니다.
            json_gcs_path = f"{output_uri.rstrip('/')}/output-document.json"
            
            mapping[original_filename] = {
                "output_folder_index": output_folder_index,
                "output_json_gcs_path": json_gcs_path # 수정된 경로 저장
            }
        except Exception:
            pass # 오류가 있는 파일은 건너뜁니다.

    if not mapping:
        print("🛑 오류: 매니페스트 매핑 정보를 생성할 수 없습니다.")
        return None

    try:
        bucket = storage_client.bucket(bucket_name)
        manifest_path = f"{output_prefix}/_batch_manifest.json"
        blob = bucket.blob(manifest_path)
        blob.upload_from_string(json.dumps(mapping, indent=2), content_type="application/json")
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 매니페스트 파일 생성 완료: gs://{bucket_name}/{manifest_path}")
        return f"gs://{bucket_name}/{manifest_path}"
    except Exception as e:
        print(f"🛑 오류: 매니페스트 파일 GCS 업로드 실패 - {e}")
        return None

def download_parse_and_split_pdfs(manifest_gcs_path: str, local_input_folder: str, local_output_folder: str):
    """
    [신규 기능]
    GCS에서 매니페스트와 JSON 결과를 다운로드하고, 원본 PDF를 쪼개서 로컬에 저장합니다.
    """
    print(f"[{time.strftime('%H:%M:%S')}] 4. PDF 분할 및 로컬 저장 시작...")
    storage_client = storage.Client(project=PROJECT_ID)
    
    # 1. 매니페스트 파일 다운로드 및 파싱
    try:
        bucket_name, blob_name = manifest_gcs_path.replace("gs://", "").split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        manifest_data = json.loads(blob.download_as_string())
    except Exception as e:
        print(f"🛑 오류: 매니페스트 파일 다운로드 실패. GCS 경로를 확인하세요: {manifest_gcs_path} - {e}")
        return

    print(f"    총 {len(manifest_data)}개의 원본 문서에 대한 분할을 시작합니다.")
    
    # 2. 매니페스트를 기반으로 각 파일 처리
    for original_filename, info in manifest_data.items():
        try:
            # 3. GCS에서 Splitter 결과 JSON 다운로드
            json_gcs_path = info['output_json_gcs_path']
            json_bucket_name, json_blob_name = json_gcs_path.replace("gs://", "").split("/", 1)
            json_bucket = storage_client.bucket(json_bucket_name)
            json_blob = json_bucket.blob(json_blob_name)
            
            docai_result = json.loads(json_blob.download_as_string())
            
            # 4. 원본 PDF 파일 경로 찾기
            original_pdf_path = os.path.join(local_input_folder, original_filename)
            if not os.path.exists(original_pdf_path):
                print(f"    ⚠️ 경고: 원본 PDF 파일을 찾을 수 없습니다 (건너뜀): {original_pdf_path}")
                continue
                
            reader = PdfReader(original_pdf_path)

            # 5. JSON의 'entities' (분류된 문서)를 기반으로 PDF 쪼개기
            entities = docai_result.get('entities', [])
            print(f"    📄 {original_filename}: 총 {len(entities)}개의 엔티티 감지됨")

            # 감지된 모든 문서 타입 출력 (디버깅용)
            detected_types = [entity.get('type', 'Unknown') for entity in entities]
            print(f"    감지된 타입들: {detected_types}")

            for entity in entities:
                doc_type = entity.get('type', 'Etc') # 예: Bill_of_Lading, Commercial_Invoice, Packing_List

                # BL과 Commercial Invoice만 필터링 (정확한 매칭)
                doc_type_normalized = doc_type.replace('_', '').replace('-', '').replace(' ', '').lower()

                is_bl = doc_type_normalized == 'billoflading'
                is_ci = doc_type_normalized == 'commercialinvoice'

                if not (is_bl or is_ci):
                    print(f"    ⏭️  건너뛰기: '{doc_type}' (BL/CI가 아님)")
                    continue

                # 타입명 표준화 (저장 폴더용)
                if is_bl:
                    standardized_type = "BL"
                elif is_ci:
                    standardized_type = "Commercial_Invoice"

                print(f"    🔍 '{doc_type}' → '{standardized_type}' 처리 시작")

                # --- [버그 수정] ---
                # 페이지 범위 추출 로직 강화 (여러 Document AI 응답 형식 지원)
                page_anchor = entity.get('pageAnchor', {})

                # pageAnchor가 없으면 건너뛰기
                if not page_anchor:
                    print(f"    ⚠️ 건너뛰기: '{standardized_type}' - pageAnchor 없음")
                    print(f"       [DEBUG] 엔티티 전체: {json.dumps(entity, indent=2, ensure_ascii=False)}")
                    continue

                print(f"       [DEBUG] pageAnchor 구조: {json.dumps(page_anchor, indent=2, ensure_ascii=False)}")

                page_start = None
                page_end = None

                # 케이스 1: pageSpans 사용 (start/end 또는 startIndex/endIndex)
                page_spans = page_anchor.get('pageSpans')
                if page_spans and len(page_spans) > 0:
                    span = page_spans[0]
                    print(f"       [DEBUG] pageSpans[0]: {json.dumps(span, indent=2, ensure_ascii=False)}")

                    # start/end 형식 (문자열일 수도 있음)
                    if 'start' in span:
                        page_start = int(span['start']) if span['start'] is not None else None
                        page_end = int(span.get('end', page_start + 1)) if span.get('end') is not None else page_start + 1
                    # startIndex/endIndex 형식
                    elif 'startIndex' in span:
                        page_start = int(span['startIndex']) if span['startIndex'] is not None else None
                        page_end = int(span.get('endIndex', page_start + 1)) if span.get('endIndex') is not None else page_start + 1

                # 케이스 2: pageRefs 사용 (개별 페이지 참조)
                if page_start is None:
                    page_refs = page_anchor.get('pageRefs')
                    if page_refs:
                        print(f"       [DEBUG] pageRefs: {json.dumps(page_refs, indent=2, ensure_ascii=False)}")

                        # pageRefs가 리스트인 경우
                        if isinstance(page_refs, list) and len(page_refs) > 0:
                            pages = []

                            for idx, ref in enumerate(page_refs):
                                # 방법 1: 명시적인 페이지 번호 필드
                                page_num = ref.get('page') or ref.get('pageNumber') or ref.get('pageIndex')

                                # 방법 2: pageRefs 배열의 인덱스가 페이지 번호인 경우
                                # (confidence만 있고 page 번호가 없을 때)
                                if page_num is None and 'confidence' in ref:
                                    page_num = idx  # 인덱스를 페이지 번호로 사용
                                    print(f"       [DEBUG] pageRefs[{idx}]에 page 번호 없음, 인덱스 사용: {page_num}")

                                if page_num is not None:
                                    pages.append(int(page_num))

                            if pages:
                                page_start = min(pages)
                                page_end = max(pages) + 1  # exclusive end
                                print(f"       [DEBUG] pageRefs에서 추출한 페이지: {pages} → start={page_start}, end={page_end}")

                # 케이스 3: textAnchor 사용 (텍스트 위치 기반)
                if page_start is None:
                    text_anchor = entity.get('textAnchor')
                    if text_anchor:
                        print(f"       [DEBUG] textAnchor: {json.dumps(text_anchor, indent=2, ensure_ascii=False)}")

                        # textAnchor.textSegments에서 페이지 정보 추출 시도
                        text_segments = text_anchor.get('textSegments', [])
                        if text_segments:
                            # 일반적으로 첫 번째 segment의 위치로 페이지 판단
                            # 하지만 이것만으로는 부족할 수 있음
                            print(f"       [DEBUG] textAnchor에 textSegments 있음, 하지만 페이지 번호 직접 추출 불가")

                # 페이지 정보를 찾지 못한 경우
                if page_start is None or page_end is None:
                    print(f"    ⚠️ 건너뛰기: '{standardized_type}' - 페이지 정보 추출 실패")
                    continue

                # 페이지 범위 유효성 검사
                if page_start >= page_end or page_end > len(reader.pages):
                    print(f"    ⚠️ 건너뛰기: '{standardized_type}' - 유효하지 않은 페이지 범위 (Start: {page_start}, End: {page_end}, 총 페이지: {len(reader.pages)})")
                    continue

                print(f"    ✅ 처리 중: '{standardized_type}' - 페이지 {page_start}~{page_end-1}")
                # --- [버그 수정 완료] ---

                # 6. 새 PDF 파일 생성 (pypdf)
                writer = PdfWriter()
                for i in range(page_start, page_end):
                    writer.add_page(reader.pages[i])

                # 7. 새 로컬 폴더에 저장
                output_subfolder = os.path.join(local_output_folder, standardized_type)
                os.makedirs(output_subfolder, exist_ok=True)

                base_name = os.path.splitext(original_filename)[0]
                slip_number = base_name.split("_")[0] if "_" in base_name else base_name

                # 파일 이름 생성 (1-based 페이지 번호로 더 직관적으로)
                # 단일 페이지: xxx_BL_page3.pdf
                # 여러 페이지: xxx_BL_page3-5.pdf
                page_start_1based = page_start + 1
                page_end_1based = page_end  # exclusive end이므로 +1 불필요

                if page_end - page_start == 1:
                    # 단일 페이지
                    new_filename = f"{slip_number}_{standardized_type}_page{page_start_1based}.pdf"
                else:
                    # 여러 페이지 (inclusive end로 표시)
                    new_filename = f"{slip_number}_{standardized_type}_page{page_start_1based}-{page_end_1based}.pdf"

                output_pdf_path = os.path.join(output_subfolder, new_filename)

                with open(output_pdf_path, "wb") as f_out:
                    writer.write(f_out)

                print(f"    💾 저장 완료: {output_pdf_path}")

        except Exception as e:
            print(f"🛑 오류: PDF 분할 중 실패 (파일: {original_filename}) - {e}")


if __name__ == "__main__":
    if not os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
        print(f"🛑 오류: 서비스 계정 키 파일을 찾을 수 없습니다. 경로를 확인하세요.")
        exit()
        
    if not os.path.exists(LOCAL_INPUT_FOLDER):
        print(f"🛑 오류: 로컬 입력 폴더를 찾을 수 없습니다: {LOCAL_INPUT_FOLDER}")
        exit()

    # 1. 로컬 파일 업로드
    gcs_input_prefix = WEEKLY_BATCH_ID
    gcs_input_uris = upload_files_to_gcs(
        local_path=LOCAL_INPUT_FOLDER,
        bucket_name=GCS_INPUT_BUCKET,
        gcs_prefix=gcs_input_prefix
    )
    
    if gcs_input_uris:
        # 2. DMS Splitter 배치 처리 실행
        gcs_output_prefix = f"{WEEKLY_BATCH_ID}/1_splitter_results"
        output_gcs_folder, manifest_gcs_path = run_splitter_batch_process(
            processor_id=SPLITTER_PROCESSOR_ID,
            gcs_input_uris=gcs_input_uris,
            gcs_output_bucket=GCS_OUTPUT_BUCKET,
            gcs_output_prefix=gcs_output_prefix
        )
        
        # 3. [신규] PDF 분할 및 로컬 저장 실행
        if manifest_gcs_path:
            download_parse_and_split_pdfs(
                manifest_gcs_path=manifest_gcs_path,
                local_input_folder=LOCAL_INPUT_FOLDER,
                local_output_folder=LOCAL_OUTPUT_FOLDER
            )
            print("\n--- 모든 작업 완료 ---")
            print(f"쪼개진 PDF 파일이 다음 폴더에 저장되었습니다:")
            print(f"{LOCAL_OUTPUT_FOLDER}")
            print("이제 이 폴더의 파일들로 Extractor 학습을 시작할 수 있습니다.")