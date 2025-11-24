# IDARS 프로젝트 리팩토링 가이드

## ⚠️ 실제 데이터 기반 구현 필수

**이 문서의 모든 JSON/데이터 예시는 구조 참고용입니다.**
- `<사용자 입력>`, `[TODO]` 표시 부분은 실제 데이터 확인 후 수정 필수
- 현재 프로젝트의 Data/projects/ 폴더 확인하여 실제 구조에 맞게 조정

---

## 1. 핵심 아키텍처: 마더 워크스페이스 + 미니 워크스페이스 연결

### 1.1 전체 구조

```
┌──────────────────────────────────────────┐
│   마더 워크스페이스 (통합 뷰)             │
│   - 모든 단계의 확정 데이터 실시간 누적   │
│   - 전체 진행 상황 시각화                │
│   - 각 단계로의 네비게이션 허브          │
└──────────────────────────────────────────┘
          ↑ 확정 시 데이터 전송
┌─────────┬─────────┬─────────┬─────────┐
│ Step 1  │ Step 2  │ Step 3  │ Step 4  │
│미니 WS 1│미니 WS 2│미니 WS 3│미니 WS 4│
└─────────┴─────────┴─────────┴─────────┘
```

### 1.2 데이터 흐름 (단방향, 순차적)

```
Step 1 확정 → confirmed_invoices.csv
    ↓ 마더 WS 갱신, Step 2 활성화
Step 2 확정 → evidence_metadata.json + PDFs
    ↓ 마더 WS 갱신, Step 3 활성화
Step 3 확정 → extracted_data.json
    ↓ 마더 WS 갱신, Step 4 활성화
Step 4 확정 → reconciliation_results.json
    ↓ 마더 WS 갱신, 프로젝트 완료
```

---

## 2. 핵심 원칙

### 2.1 확정 후 불가역 (Irreversible)
- 확정된 데이터는 직접 수정 불가
- 수정 필요 시: **확정 취소 → 수정 → 재확정**

### 2.2 순차적 진행 (Sequential)
- Step 1 → 2 → 3 → 4 순서로만 진행
- 이전 단계 미확정 시 다음 단계 접근 차단

### 2.3 역순 확정 취소 (Reverse Cancellation)
```
Step 1 수정 필요 시:
Step 4 확정 취소 → Step 3 확정 취소 → Step 2 확정 취소 
→ Step 1 확정 취소 → 수정 → 재확정 (1→2→3→4)
```

### 2.4 마더 워크스페이스 동기화
- 모든 확정/취소 시 마더 WS 자동 갱신
- 실시간 진행 상황 반영

---

## 3. 메뉴 구조

| # | 메뉴명 | 타입 | 역할 | 연결성 |
|---|--------|------|------|--------|
| 1 | 홈/프로젝트 관리 | - | 프로젝트 CRUD | - |
| 2 | 마더 워크스페이스 | 통합 | 전체 진행 상황 표시 | 모든 단계 데이터 수신 |
| 3 | Step 1: 전표 확정 | 미니 WS | SAP 전표 확정 | 확정 시 → 마더 WS + Step 2 활성화 |
| 4 | Step 2: 증빙 수집 | 미니 WS | DMS 다운로드 & 분류 | Step 1 데이터 읽기 → 확정 시 → 마더 WS + Step 3 활성화 |
| 5 | Step 3: 데이터 추출 | 미니 WS | OCR 추출 & 검증 | Step 2 데이터 읽기 → 확정 시 → 마더 WS + Step 4 활성화 |
| 6 | Step 4: 자동 대사 | 미니 WS | 규칙 & AI 대사 | Step 1, 3 데이터 읽기 → 확정 시 → 마더 WS + 완료 |
| 7 | 결과 대시보드 | 시각화 | 통계 & 그래프 | 모든 확정 데이터 읽기 전용 |

---

## 4. 프로젝트 디렉토리 구조

**[TODO: 실제 Data/projects/ 폴더 확인 후 조정]**

```
Data/projects/{ProjectName_YYYYMMDD_HHMMSS}/
├── metadata.json                         # 핵심 메타데이터
├── step1_invoice_confirmation/
│   └── confirmed_invoices.csv
├── step2_evidence_collection/
│   ├── evidence_metadata.json
│   └── DMS_Downloads/{전표번호}/
│       ├── BL.pdf
│       ├── Invoice.pdf
│       └── Packing_List.pdf
├── step3_data_extraction/
│   └── extracted_data.json
└── step4_reconciliation/
    └── reconciliation_results.json
```

---

## 5. metadata.json 구조

**[TODO: 실제 컬럼명/필드명 반영]**

```json
{
  "id": "<프로젝트ID>",
  "name": "<프로젝트명>",
  "created_at": "YYYY-MM-DDTHH:MM:SS",
  "updated_at": "YYYY-MM-DDTHH:MM:SS",
  "current_step": 0,
  "status": "new | in_progress | completed",
  
  "steps": {
    "step1": {
      "status": "pending | in_progress | completed | cancelled",
      "started_at": null,
      "completed_at": null,
      "data": {
        "invoice_count": 0,
        "total_amount": 0,
        "data_file": "step1_invoice_confirmation/confirmed_invoices.csv"
      }
    },
    "step2": { /* ... */ },
    "step3": { /* ... */ },
    "step4": { /* ... */ }
  }
}
```

---

## 6. 각 단계별 핵심 요구사항

### Step 1: 전표리스트 확정

**입력**: SAP 다운로드 or Excel 업로드  
**출력**: confirmed_da.csv  
**핵심 작업**:
1. 전표 데이터 불러오기
2. 행 선택, 컬럼 선택
3. 확정 → 마더 WS 갱신 + Step 2 활성화

**[TODO]**:
- SAP ZSDR0580 결과의 실제 컬럼명 확인
- 현재 구성되어 있는 칼럼명으로해도됨.

---

### Step 2: 증빙 수집

**입력**: Step 1 확정 데이터 (자동 로드)  
**출력**: evidence_metadata.json + PDF 파일들  
**핵심 작업**:
1. Step 1 전표번호 목록 읽기 (읽기 전용)
2. DMS 다운로드 (기존 dms_downloader 사용)
3. Split (문서 유형 분류: BL, Invoice, Packing List)
4. 전표별 증빙 상태 표시 (🟢 완료 / 🔴 미수집)
5. PDF 미리보기 (셀 클릭 시)
6. 수동 업로드 (미수집 건)
7. 확정 → 마더 WS 갱신 + Step 3 활성화

**[TODO]**:
- DMS 다운로드 결과 폴더 구조 확인
- Modules의 Splitter 상 규정된 증빙데이터들(BL, Invoice, Packing List, certificate origin 등 여러개 규정되어있음)로 구분함
- Split 키워드 리스트 작성

---

### Step 3: 데이터 추출

**입력**: Step 2 확정 데이터 (자동 로드)  
**출력**: extracted_data.json  
**핵심 작업**:
1. Step 2 증빙 메타데이터 읽기 (읽기 전용)
2. OCR 자동 실행 (문서 유형별 파서)
3. 추출 데이터 & 정확도 표시
4. 낮은 정확도 (<80%) 항목 수동 보정 (PDF + 데이터 동시 표시)
5. 확정 → 마더 WS 갱신 + Step 4 활성화

**[TODO]**:
- 추출필드는 향후 업데이트하며 Parser의 Invoice parser에 있는 것을 우선으로 시작예정
- 정규식 패턴 작성
- OCR 엔진 선택 (Tesseract / Azure / AWS)

---

### Step 4: 자동 대사

**입력**: Step 1, Step 3 확정 데이터 (자동 로드)  
**출력**: reconciliation_results.json  
**핵심 작업**:
1. Step 1 전표 데이터 & Step 3 추출 데이터 읽기 (읽기 전용)
2. 규칙 기반 1차 대사
3. 결과 분류: ✅ 일치 / ❌ 불일치 / ⚠️ 확인필요
4. 불일치/확인필요 건만 AI 대사 (Claude API)
5. 증빙 직접 확인 (PDF 팝업)
6. 확정 → 마더 WS 갱신 + 프로젝트 완료

**[TODO]**:
- Step 1과 Step 3 필드 매핑표 작성
- 대사 규칙 정의 (완전 일치 / 허용 오차)
- AI 프롬프트 작성

---

## 7. 확정 및 확정 취소 로직

### 확정 시

```python
def confirm_step(project_id, step_number, data):
    # 1. 확정 데이터 저장
    save_confirmed_data(step_number, data)
    
    # 2. metadata.json 업데이트
    metadata['steps'][f'step{step_number}']['status'] = 'completed'
    metadata['steps'][f'step{step_number}']['completed_at'] = now()
    metadata['current_step'] = step_number
    
    # 3. 다음 단계 활성화
    metadata['steps'][f'step{step_number + 1}']['status'] = 'pending'
    
    # 4. 마더 워크스페이스 갱신 트리거
    trigger_mother_workspace_update(project_id)
    
    save_metadata(project_id, metadata)
```

### 확정 취소 시

```python
def cancel_step_confirmation(project_id, step_number):
    # 1. 이후 단계 확정 여부 확인
    for i in range(step_number + 1, 5):
        if metadata['steps'][f'step{i}']['status'] == 'completed':
            return Error("먼저 Step {i} 확정을 취소하세요")
    
    # 2. 확정 데이터 삭제 (또는 백업)
    delete_confirmed_data(step_number)
    
    # 3. metadata.json 업데이트
    metadata['steps'][f'step{step_number}']['status'] = 'cancelled'
    metadata['current_step'] = step_number - 1
    
    # 4. 마더 워크스페이스 갱신
    trigger_mother_workspace_update(project_id)
    
    save_metadata(project_id, metadata)
```

---

## 8. 마더 워크스페이스 구현

### 핵심 기능
1. **타임라인 뷰**: Step 1 → 2 → 3 → 4 진행 상태 시각화
2. **단계별 요약 카드**: 각 단계 확정 데이터 핵심 지표 표시
3. **빠른 이동**: 각 단계로 이동 버튼 (현재 가능한 단계 강조)
4. **실시간 갱신**: 확정/취소 시 자동 리로드

### 데이터 조회 API

```python
@app.route('/api/projects/<project_id>/mother-workspace')
def get_mother_workspace_data(project_id):
    metadata = load_metadata(project_id)
    
    return {
        "project": metadata,
        "step1_summary": get_step_summary(project_id, 1) if metadata['steps']['step1']['status'] == 'completed' else None,
        "step2_summary": get_step_summary(project_id, 2) if metadata['steps']['step2']['status'] == 'completed' else None,
        "step3_summary": get_step_summary(project_id, 3) if metadata['steps']['step3']['status'] == 'completed' else None,
        "step4_summary": get_step_summary(project_id, 4) if metadata['steps']['step4']['status'] == 'completed' else None,
    }

def get_step_summary(project_id, step_number):
    # 각 단계의 확정 데이터 파일을 읽어서 요약 통계 계산
    # 예: Step 1 → 전표 개수, 총 금액
    #     Step 2 → 증빙 수집률, 문서 유형별 개수
    #     Step 3 → 평균 정확도, 낮은 정확도 개수
    #     Step 4 → 대사 일치율, 불일치 개수
    pass
```

---

## 9. UI/UX 가이드라인

### 안내 메시지 (모든 단계)

```
ℹ️ [현재 단계 설명]
- 이전 단계 확정 데이터: X건
- 필요한 작업: ...
- 확정 후: 다음 단계 활성화
- ⚠️ 확정 후 수정 불가 (확정 취소 필요)
```

### 확정 버튼 클릭 시 모달

```
⚠️ 데이터를 확정하시겠습니까?

- X건의 데이터가 확정됩니다
- 확정 후 직접 수정할 수 없습니다
- 수정하려면 확정 취소 후 재작업 필요
- 이후 단계들도 재확정 필요할 수 있습니다

[취소] [확정하기]
```

### 확정 취소 버튼 클릭 시 모달

```
⚠️ 확정을 취소하시겠습니까?

❌ 확정 데이터가 삭제됩니다
🔄 데이터 수정 후 다시 확정해야 합니다
⚠️ 이후 단계들도 순차 재확정 필요

[❌ 차단됨: Step X가 확정되어 있습니다]

[취소] [확정 취소]
```

---

## 10. 구현 체크리스트

### Phase 1: 기반 구조 (2주)
- [ ] metadata.json 스키마 정의
- [ ] 확정/취소 로직 구현
- [ ] 마더 워크스페이스 UI
- [ ] 홈/프로젝트 관리 페이지

### Phase 2: Step 1 & 2 (3주)
- [ ] Step 1: SAP 다운로드/업로드
- [ ] Step 1: 확정 → 마더 WS 연동
- [ ] Step 2: DMS 다운로드
- [ ] Step 2: Split 기능
- [ ] Step 2: 확정 → 마더 WS 연동

### Phase 3: Step 3 (3주)
- [ ] OCR 엔진 통합
- [ ] 문서 유형별 파서
- [ ] 수동 보정 UI
- [ ] 확정 → 마더 WS 연동

### Phase 4: Step 4 (3주)
- [ ] 규칙 기반 대사 엔진
- [ ] Claude API 연동
- [ ] AI 대사 UI
- [ ] 확정 → 마더 WS 연동

### Phase 5: 최적화 (2주)
- [ ] 결과 대시보드
- [ ] 에러 핸들링
- [ ] 성능 최적화

### Phase 6: 테스트 & 배포 (1주)
- [ ] End-to-End 테스트
- [ ] 버그 수정
- [ ] 배포

---

## 11. 실제 데이터 확인 TODO

### Step 1
- [ ] SAP ZSDR0580 CSV 열어보기
- [ ] 전표번호 컬럼명: `_________________`
- [ ] 금액 컬럼명: `_________________`
- [ ] 통화 컬럼명: `_________________`

### Step 2
- [ ] DMS 다운로드 폴더 구조 확인
- [ ] BL PDF 샘플 키워드: `_________________`
- [ ] Invoice PDF 샘플 키워드: `_________________`

### Step 3
- [ ] BL 추출 필드: `_________________`
- [ ] Invoice 추출 필드: `_________________`

### Step 4
- [ ] 대사 필드 매핑표 작성
- [ ] 허용 오차 값: `_________________`

---

## 12. AI 코딩 시 전달 사항

```
이 문서의 핵심:

1. 마더 워크스페이스 + 미니 워크스페이스 연결 구조
2. 확정 후 불가역, 순차적 진행, 역순 확정 취소
3. 모든 확정/취소 시 마더 WS 자동 갱신
4. <사용자 입력>, [TODO] 부분은 실제 데이터 확인 후 구현
5. 데이터 예시는 구조 참고용

우선순위: Phase 1 → 2 → 3 → 4 → 5 → 6
```

---

**문서 끝**
