# POSCO 수출 증빙 문서 자동화 시스템

PDF 문서 자동 분류 및 필드 추출 시스템

---

## 📦 파일 구성 (3개 핵심 파일)

```
📁 프로젝트
├── pdf_splitter.py          ← 1단계: 문서 자동 분류
├── posco_parser.py          ← 2단계: 필드 자동 추출
├── accuracy_checker.py      ← 3단계: 정확도 측정 (선택)
│
├── pdf_splitter.md          ← Splitter 가이드
├── posco_parser.md          ← Parser 가이드
├── accuracy_checker.md      ← Checker 가이드
├── 워크플로우.md             ← 전체 프로세스 가이드
└── README.md                ← 이 파일
```

---

## 🎯 전체 프로세스

```
원본 PDF (여러 문서 혼합)
    ↓
[1단계: Splitter] 문서 유형별 자동 분류
    ├─ invoice/
    ├─ bl/
    └─ packing_list/
    ↓
[2단계: Parser] 각 문서에서 필드 추출
    ↓
JSON 결과
```

---

## 🚀 빠른 시작

### 1. 설치
```bash
pip install PyMuPDF
```

또는
```bash
python -m pip install PyMuPDF
```

### 2. 1단계 - 문서 분류
```python
# pdf_splitter.py 설정
INPUT_FOLDER = r"D:\원본문서"
OUTPUT_FOLDER = r"D:\분류완료"
```
```bash
python pdf_splitter.py
```

### 3. 2단계 - 필드 추출
```python
# posco_parser.py 설정
INPUT_FOLDER = r"D:\분류완료\invoice"
```
```bash
python posco_parser.py
```

**완료!** 🎉

---

## 📋 각 도구의 역할

### pdf_splitter.py ⭐ (1단계)
- **역할**: 여러 문서가 섞인 PDF → 유형별로 자동 분류
- **입력**: 원본 PDF (20페이지)
- **출력**: 
  - invoice/ (3페이지)
  - bl/ (5페이지)
  - packing_list/ (2페이지)
- **자세히**: `pdf_splitter.md` 참고

**Invoice (인보이스)**
- invoice_number (번호)
- invoice_date (날짜)
- currency (통화)
- total_amount (총액)
- shipper (발송인)
- consignee (수취인)
- port_of_loading (선적항)
- final_destination (최종목적지)

**Bill of Lading (선하증권)**
- bl_number (BL 번호)
- vessel_name (선박명)
- port_of_loading (선적항)
- port_of_discharge (양륙항)
- sailing_date (출항일)
- container_numbers (컨테이너 번호)
- gross_weight (총중량)

**Packing List (포장명세서)**
- net_weight (순중량)
- gross_weight (총중량)
- number_of_packages (포장개수)

---

## 🎯 사용 시나리오

### 시나리오 1: 기본 파싱
```python
# posco_parser.py 설정
INPUT_FOLDER = r"D:\수출문서"
OUTPUT_FOLDER = ""
```
```bash
python posco_parser.py
```

### 시나리오 2: 대량 처리
```python
INPUT_FOLDER = r"D:\대량문서"
PARALLEL_WORKERS = 4    # 병렬 처리
VERBOSE = False         # 간단 출력
```

### 시나리오 3: 정확도 개선
1. `test_data.json` 생성 (정답 데이터)
2. `python accuracy_checker.py` 실행
3. 가장 틀리는 필드 확인
4. `posco_parser.py`의 정규식 패턴 수정
5. 재측정
6. 95% 달성까지 반복

---

## 📊 현재 성능

| 항목 | 값 |
|------|-----|
| 처리 속도 | ~0.025초/페이지 |
| 현재 정확도 | 60-70% |
| 목표 정확도 | 95% |
| 비용 | 무료 (정규식만 사용) |

---

## 🔧 커스터마이징

### 새로운 패턴 추가
`posco_parser.py`의 `class Patterns:` 수정:

```python
class Patterns:
    INVOICE = {
        'invoice_number': [
            r'기존패턴',
            r'VN-\d{4}-(\d{6})',      # ← 베트남용 추가!
        ],
    }
```

### 새로운 필드 추가
```python
# 1. 패턴 추가
class Patterns:
    INVOICE = {
        'payment_terms': [            # ← 새 필드!
            r'Payment\s+Terms[:\s]+([^\n]+)',
        ],
    }

# 2. 추출 로직 추가
def parse_invoice(self, pages):
    ...
    result['payment_terms'] = match_first(
        full_text, 
        Patterns.INVOICE['payment_terms']
    )
```

---

## 📚 문서

| 파일 | 설명 | 읽어야 할 사람 |
|------|------|---------------|
| `posco_parser.md` | 메인 파서 가이드 | **모두 (필독!)** |
| `accuracy_checker.md` | 정확도 측정 가이드 | 정확도 개선 작업자 |
| `README.md` | 프로젝트 개요 | 이 파일 |

---

## 🐛 자주 묻는 질문

### Q: "폴더를 찾을 수 없습니다" 오류
**A**: INPUT_FOLDER 경로 확인
- 파일 탐색기에서 주소 복사
- `r"경로"` 형식 지키기

### Q: "No module named 'fitz'" 오류
**A**: PyMuPDF 설치
```bash
pip install PyMuPDF
```

### Q: 필드가 추출되지 않음
**A**: 정규식 패턴 추가 필요
1. PDF 열어서 해당 필드 확인
2. `posco_parser.py`의 Patterns 수정
3. 자세한 내용은 `posco_parser.md` 참고

### Q: 정확도를 높이고 싶음
**A**: `accuracy_checker.md` 참고
1. 정답 데이터 생성
2. 정확도 측정
3. 패턴 개선
4. 반복

---

## 💡 핵심 포인트

### ✅ 장점
- **단순함**: 1개 파일로 모든 작업
- **빠름**: 0.025초/페이지
- **무료**: 추가 비용 없음
- **커스터마이징**: 정규식만 수정하면 됨

### ⚠️ 한계
- 정확도 60-70% (개선 가능)
- 새 양식에는 패턴 추가 필요
- 스캔 이미지 PDF는 어려움

### 🎯 추천 사용처
- POSCO 표준 양식 문서
- 정형화된 수출 증빙
- 대량 문서 처리

---

## 🔄 업데이트 계획

- [x] v1.0: 기본 파싱 기능
- [ ] v1.1: 더 많은 패턴 추가
- [ ] v1.2: 정확도 80% 달성
- [ ] v2.0: 정확도 95% 달성

---

## 📞 지원

**문제 발생시:**
1. 해당 .md 파일 확인
2. FAQ 확인
3. 오류 메시지와 함께 문의

---

## 📄 라이선스

MIT License - 자유롭게 사용/수정 가능

---

**간단하게, 효과적으로!**
`posco_parser.py` 하나면 충분합니다.
