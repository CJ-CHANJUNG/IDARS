# 프롬프트 설정 가이드

## 📋 개요

이 디렉토리에는 Gemini API 호출 시 사용되는 모든 프롬프트가 JSON 파일로 관리됩니다.

## 📁 파일 구조

```
Config/
├── smart_prompts.json    # Smart Extraction Engine (BL, Invoice 추출)
├── dterm_prompts.json    # D-Term Extraction Engine (도착일 추출)
└── PROMPTS_README.md     # 이 파일
```

## 🎯 사용 방법

### 1. **프롬프트 확인**
- `smart_prompts.json` 또는 `dterm_prompts.json` 파일을 VSCode에서 엽니다
- 각 프롬프트에는 `description`, `usage`, `llm_delivery` 필드가 있어 어떻게 사용되는지 확인할 수 있습니다

### 2. **프롬프트 수정**
- JSON 파일에서 `"content"` 필드의 값을 수정합니다
- `"editable": true`인 항목만 수정하세요
- 저장 후 백엔드를 재시작하면 새 프롬프트가 적용됩니다

### 3. **안전장치**
- 프롬프트 파일이 없거나 손상되어도 코드 내부의 기본값(Fallback)이 사용됩니다
- 따라서 실험적으로 수정해도 시스템이 멈추지 않습니다

## 📝 주요 프롬프트 설명

### Smart Extraction Engine (`smart_prompts.json`)

| 프롬프트 ID | 설명 | LLM 전달 여부 |
|------------|------|--------------|
| `system_instruction` | 시스템 전역 지시사항 | ✅ 모든 API 호출 시 자동 포함 |
| `doc_type_instructions` | BL/Invoice별 추가 지시사항 | ✅ 메인 프롬프트에 삽입 |
| `hint_instruction_template` | SAP 기대값 힌트 | ✅ expected_values가 있을 때만 |
| `main_extraction_prompt` | 메인 추출 프롬프트 템플릿 | ✅ 최종 프롬프트 |
| `n1_matching_retry_prompt` | N:1 매칭 실패 시 재시도 | ✅ 검증 실패 시만 |
| `retry_config` | API 재시도 설정 | ❌ 로직 제어용 |
| `validation_config` | 결과 검증 규칙 | ❌ 로직 제어용 |

### D-Term Extraction Engine (`dterm_prompts.json`)

| 프롬프트 ID | 설명 | LLM 전달 여부 |
|------------|------|--------------|
| `system_instruction` | D-Term 전용 시스템 지시사항 | ✅ 모든 API 호출 시 자동 포함 |
| `text_extraction_prompt` | 텍스트 기반 도착일 추출 | ✅ 기본 추출 방식 |
| `vision_extraction_prompt` | 이미지 기반 도착일 추출 | ✅ Fallback 방식 |
| `directive_explanations` | Directive 상세 설명 | ❌ 참고용 문서 |
| `fallback_config` | Vision API 전환 조건 | ❌ 로직 제어용 |

## 🔧 수정 예시

### 예시 1: BL 지시사항 강화

**Before:**
```json
"BL": {
  "content": "이 문서는 선하증권(Bill of Lading)입니다. 선박 정보, 운송 정보, Incoterms, 그리고 **중량 정보(Net Weight, Gross Weight)**를 주의 깊게 찾아 추출하세요."
}
```

**After:**
```json
"BL": {
  "content": "이 문서는 선하증권(Bill of Lading)입니다. 선박 정보, 운송 정보, Incoterms, **중량 정보(Net Weight, Gross Weight)**, 그리고 **컨테이너 번호(Container No)**를 반드시 찾아 추출하세요. 컨테이너 번호는 보통 'CNTR NO' 또는 'Container Number' 라벨 옆에 있습니다."
}
```

### 예시 2: 재시도 횟수 조정

**Before:**
```json
"retry_config": {
  "max_retries": 1,
  "retry_delay_seconds": 2
}
```

**After:**
```json
"retry_config": {
  "max_retries": 3,
  "retry_delay_seconds": 5
}
```

## ⚠️ 주의사항

1. **JSON 문법 검증**: 수정 후 반드시 JSON 문법이 올바른지 확인하세요 (VSCode에서 자동 검증됨)
2. **변수 유지**: `{doc_type}`, `{ocr_text}` 같은 변수는 삭제하지 마세요
3. **백업**: 중요한 수정 전에는 파일을 백업하세요
4. **재시작 필요**: 프롬프트 수정 후 백엔드를 재시작해야 적용됩니다

## 🚀 향후 확장

### Phase 2: 프론트엔드 UI (계획 중)
- 웹 UI에서 프롬프트 확인/수정 가능
- 자동 백업 및 버전 관리
- 실시간 적용 (재시작 불필요)

### API 엔드포인트 (향후 추가 예정)
```
GET  /api/settings/prompts/smart    # 프롬프트 조회
PUT  /api/settings/prompts/smart    # 프롬프트 업데이트
GET  /api/settings/prompts/history  # 변경 이력
```

## 📞 문제 해결

### Q: 프롬프트 파일을 수정했는데 적용이 안 돼요
**A:** 백엔드를 재시작하세요. 프롬프트는 엔진 초기화 시 한 번만 로드됩니다.

### Q: JSON 파일이 손상되었어요
**A:** 파일을 삭제하면 자동으로 코드 내부의 기본값(Fallback)이 사용됩니다.

### Q: 어떤 프롬프트를 수정해야 할지 모르겠어요
**A:** 각 프롬프트의 `description`과 `usage` 필드를 먼저 읽어보세요.

## 📚 참고 자료

- [Gemini API 공식 문서](https://ai.google.dev/docs)
- [프롬프트 엔지니어링 가이드](https://www.promptingguide.ai/)
