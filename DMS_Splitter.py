import os
import glob
import time
# ... (import ... )

# --- 1. [필수] 사용자 설정 변수 ---
# ... (os.environ, PROJECT_ID, LOCATION, SPLITTER_PROCESSOR_ID ... )

# 1-4. 로컬 파일 및 GCS 버킷 경로
LOCAL_FILES_PATH = r"C:\path\to\your\local_105_files" # TODO: 105개 파일이 있는 로컬 폴더 경로
GCS_INPUT_BUCKET = "your-idars-input-bucket"     # TODO: 생성한 GCS Input 버킷 이름
GCS_OUTPUT_BUCKET = "your-idars-output-bucket"   # TODO: 생성한 GCS Output 버킷 이름

# 1-5. [신규] 주간 배치 ID (매주 실행 시 이 부분만 변경하거나 동적 생성)
WEEKLY_BATCH_ID = f"2025_W{time.strftime('%U')}" # 예: 2025_W45
# --- [필수] 설정 종료 ---


def upload_files_to_gcs(local_path: str, bucket_name: str, gcs_prefix: str) -> list[str]:
# ... (기존 코드와 동일) ...


def run_splitter_batch_process(processor_id: str, gcs_input_uris: list[str], gcs_output_bucket: str, gcs_output_prefix: str) -> str:
# ... (기존 코드와 동일) ...
    """DMS Splitter 배치 처리를 요청하고 완료까지 대기합니다."""
    
    print(f"[{time.strftime('%H:%M:%S')}] 2. DMS Splitter 배치 처리 요청...")
    
# ... (docai_client, processor_name, input_documents, input_config ...)
    
    # 출력 설정 (경로 수정)
    output_gcs_uri = f"gs://{gcs_output_bucket}/{gcs_output_prefix}/" # gcs_output_prefix에 이미 "1_splitter_results"가 포함됨
    output_config = documentai.DocumentOutputConfig(
# ... (기존 코드와 동일) ...
        gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(gcs_uri=output_gcs_uri)
    )

    # 배치 처리 요청
# ... (기GCS_INPUT_BUCKET존 코드와 동일) ...
    request = documentai.BatchProcessRequest(
# ... (기존 코드와 동일) ...
        name=processor_name,
        input_documents=input_config,
        document_output_config=output_config,
    )
# ... (operation, try/except ... )


if __name__ == "__main__":
# ... (인증 설정 ...)
        
    # 1. 로컬 파일 업로드 (GCS 경로에 WEEKLY_BATCH_ID 적용)
    gcs_input_prefix = WEEKLY_BATCH_ID
    gcs_input_uris = upload_files_to_gcs(
        local_path=LOCAL_FILES_PATH,
        bucket_name=GCS_INPUT_BUCKET,
        gcs_prefix=gcs_input_prefix
    )
    
    if gcs_input_uris:
        # 2. DMS Splitter 배치 처리 실행 (GCS 경로에 WEEKLY_BATCH_ID 적용)
        gcs_output_prefix = f"{WEEKLY_BATCH_ID}/1_splitter_results" # 출력 경로 지정
        
        output_path = run_splitter_batch_process(
            processor_id=SPLITTER_PROCESSOR_ID,
            gcs_input_uris=gcs_input_uris,
            gcs_output_bucket=GCS_OUTPUT_BUCKET,
            gcs_output_prefix=gcs_output_prefix
        )
# ... (기존 코드와 동일) ...
        
        if output_path:
# ... (기존 코드와 동일) ...
            print("\n--- 작업 완료 ---")
            print(f"DMS Splitter의 분류 결과가 다음 GCS 경로에 JSON 파일로 저장되었습니다:")
            print(output_path)
            print("이제 이 경로의 JSON 파일들을 파싱하여 BL, Invoice 문서를 분리할 수 있습니다.")