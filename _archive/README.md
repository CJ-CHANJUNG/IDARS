# Archive Folder

이 폴더에는 프로젝트 정리 과정에서 이동된 파일들이 보관되어 있습니다.

## 📁 폴더 구조

### `debug_scripts/` (8개 파일)
개발 과정에서 사용된 디버그 스크립트들입니다.
- debug_headers*.py (4개)
- debug_step3_match.py
- debug_walkthrough.py
- backend/debug_extraction*.py (2개)

### `test_scripts/` (5개 파일)
테스트 및 검증용 스크립트들입니다.
- test_dterm_api_integration.py
- test_ocr_coordinates.py
- check_extraction_logs.py
- check_step1_expected.py
- check_step1_values.py

### `temp_files/` (5개 파일)
임시 분석 및 작업 파일들입니다.
- analyze_samples.py
- clear_final_status.py
- subset_sum.py
- 94456924.json
- temp_debug.json

### `logs/` (6개 파일)
디버그 로그 및 분석 결과 파일들입니다.
- analysis_result.txt
- crash_log.txt
- crash_log_engine.txt
- debug_output.txt
- ocr_debug.txt
- dms_debug.log (~536KB)
- dterm_debug.log (~179KB)

### `docs_old/` (5개 파일)
구 버전 문서 및 가이드들입니다.
- IDARS_Complete_Spec.md (62KB)
- IDARS_Agent_Implementation_Guide.md
- IDARS_Improvement_Plan.md
- IDARS_Refactoring_Guide.md
- extractor 수정안.md

## ⚠️ 주의사항

- 이 파일들은 **삭제되지 않고 이동**되었습니다.
- 필요시 언제든지 복구 가능합니다.
- 시스템 작동에는 영향을 주지 않습니다.

## 🗑️ 삭제 가능 여부

이 폴더는 다음과 같은 경우 안전하게 삭제할 수 있습니다:
1. 프로젝트가 안정적으로 작동하는 것을 확인한 후
2. Git에 커밋되어 이력이 보존된 후
3. 최소 1개월 이상 사용하지 않은 경우

---

**정리 일시**: 2026-01-08  
**정리 사유**: 프로젝트 구조 클리닝
