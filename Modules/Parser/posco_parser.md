# posco_parser.py 사용 가이드

## 📋 개요

POSCO 수출 증빙 문서(Invoice, BL, Packing List 등)를 PDF에서 자동으로 파싱하는 프로그램입니다.

**이 하나의 파일로 모든 작업이 가능합니다!**

---

## 🚀 빠른 시작 (3단계)

### 1. 설정하기
파일을 열어서 맨 위 부분만 수정:

```python
# 🔧 사용자 설정
INPUT_FOLDER = r"D:\내PDF폴더"  # ← 여기만 수정!
OUTPUT_FOLDER = ""              # 비워두면 자동 생성
```

### 2. 실행하기
```bash
python posco_parser.py
```

### 3. 결과 확인
`parsed_results` 폴더에 JSON 파일 생성됨!

---

## ⚙️ 설정 항목 상세

### INPUT_FOLDER (필수)
- **설명**: PDF 파일이 들어있는 폴더
- **형식**: `r"경로"` (r과 큰따옴표 필수!)
- **예시**:
  ```python
  INPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\Data\정규식 학습\테스트"
  INPUT_FOLDER = r"C:\Users\홍길동\Documents\PDFs"
  ```

### OUTPUT_FOLDER (선택)
- **설명**: 결과 JSON 저장 위치
- **기본값**: `""` (비워두면 INPUT_FOLDER/parsed_results에 자동 생성)
- **예시**:
  ```python
  OUTPUT_FOLDER = ""                    # 자동 생성
  OUTPUT_FOLDER = r"D:\결과폴더"         # 직접 지정
  ```

### PARALLEL_WORKERS (선택)
- **설명**: 병렬 처리 워커 수 (파일 많을 때 속도 향상)
- **추천값**: CPU 코어 수의 절반 (4코어 → 2, 8코어 → 4)
- **예시**:
  ```python
  PARALLEL_WORKERS = 1    # 순차 처리 (기본)
  PARALLEL_WORKERS = 4    # 4개 병렬 처리
  ```

### VERBOSE (선택)
- **설명**: 처리 과정 상세 출력 여부
- **값**: `True` = 자세히, `False` = 간단히
- **예시**:
  ```python
  VERBOSE = True     # 모든 과정 출력 (기본)
  VERBOSE = False    # 최소한만 출력
  ```

---

## 📊 출력 형식

### JSON 구조
```json
{
  "file_name": "sample.pdf",
  "total_pages": 12,
  "parsed_at": "2025-11-19T...",
  "document_types_found": ["invoice", "bl", "packing_list"],
  "documents": {
    "invoice": {
      "invoice_number": "1234567",
      "invoice_date": "2025-06-30",
      "currency": "EUR",
      "total_amount": 54656.40,
      "shipper": "POSCO INTERNATIONAL CORPORATION",
      "consignee": "...",
      "port_of_loading": "BUSAN, KOREA",
      "final_destination": "KOPER, SLOVENIA"
    },
    "bl": {
      "bl_number": "PLIHQ4G81934",
      "vessel_name": "CMA CGM PLATINUM",
      "port_of_loading": "BUSAN, KOREA",
      "port_of_discharge": "KOPER, SLOVENIA",
      "sailing_date": "2025-06-30",
      "container_numbers": ["CSNU7540886"],
      "gross_weight": 23600.0,
      "weight_unit": "KGS"
    },
    "packing_list": {
      "net_weight": 22200.0,
      "net_weight_unit": "KG",
      "gross_weight": 23600.0,
      "gross_weight_unit": "KG",
      "number_of_packages": 28
    }
  }
}
```

---

## 🔧 정규식 패턴 수정하기

### 패턴이 위치한 곳
파일 내 `class Patterns:` 부분을 찾으세요 (약 50줄 근처).

### Invoice Number 패턴 추가 예시
```python
class Patterns:
    INVOICE = {
        'invoice_number': [
            r'No\.\s*&\s*Date\s+of\s+Invoice\s*[\n\r\s]*(\d{7,10})',
            r'Invoice\s+No[.:]?\s*(\d{7,10})',
            r'VN-\d{4}-(\d{6})',           # ← 베트남용 추가!
            r'DE-INV-\d{4}-(\d{6})',      # ← 독일용 추가!
        ],
        ...
    }
```

### 새 필드 추가 예시
```python
# 1. Patterns 클래스에 패턴 추가
class Patterns:
    INVOICE = {
        ...
        'payment_terms': [                 # ← 새 필드!
            r'Payment\s+Terms[:\s]+([^\n]+)',
        ],
    }

# 2. parse_invoice() 함수에 추출 로직 추가
def parse_invoice(self, pages: List[Dict]) -> Dict[str, Any]:
    ...
    result['payment_terms'] = match_first(    # ← 추출!
        full_text, 
        Patterns.INVOICE['payment_terms']
    )
    return result
```

---

## 🐛 문제 해결

### 오류: "폴더를 찾을 수 없습니다"
**원인**: INPUT_FOLDER 경로가 잘못됨
**해결**:
1. 파일 탐색기에서 폴더 열기
2. 주소창 클릭 → Ctrl+C로 복사
3. INPUT_FOLDER = r"붙여넣기"
4. r과 큰따옴표 확인!

### 오류: "No module named 'fitz'"
**원인**: PyMuPDF 미설치
**해결**:
```bash
pip install PyMuPDF
```

### 필드가 추출되지 않음
**원인**: 정규식 패턴 불일치
**해결**:
1. 파싱 실패한 PDF 열기
2. 해당 필드 육안 확인 (예: Invoice No: 1234567)
3. Patterns 클래스에서 해당 필드 패턴 확인
4. 필요시 패턴 추가

### 한글이 깨짐
**원인**: 메모장으로 JSON 열어서
**해결**:
- VSCode 사용 (추천)
- 또는 메모장에서: 파일 → 다른 이름으로 저장 → 인코딩: UTF-8

---

## 📈 성능 최적화

### 파일이 많을 때 (100개+)
```python
PARALLEL_WORKERS = 4    # 병렬 처리
VERBOSE = False         # 출력 최소화
```

### 파일이 적을 때 (10개 이하)
```python
PARALLEL_WORKERS = 1    # 순차 처리
VERBOSE = True          # 상세 출력
```

---

## 🎯 사용 예시

### 예시 1: 기본 사용
```python
INPUT_FOLDER = r"D:\수출문서"
OUTPUT_FOLDER = ""
PARALLEL_WORKERS = 1
VERBOSE = True
```
→ 실행: `python posco_parser.py`

### 예시 2: 대량 처리
```python
INPUT_FOLDER = r"D:\대량문서"
OUTPUT_FOLDER = r"D:\결과"
PARALLEL_WORKERS = 4
VERBOSE = False
```
→ 실행: `python posco_parser.py`

### 예시 3: Python 스크립트에서 사용
```python
from posco_parser import DocumentParser

with DocumentParser('sample.pdf') as parser:
    results = parser.parse_all()
    parser.save_json('output.json')
    
    # 결과 사용
    if 'invoice' in results['documents']:
        inv_num = results['documents']['invoice']['invoice_number']
        print(f"Invoice: {inv_num}")
```

---

## 💡 팁

### 1. 경로 복사하기
- 파일 탐색기 → 주소창 클릭 → Ctrl+C
- INPUT_FOLDER = r"Ctrl+V"

### 2. 패턴 테스트
- https://regex101.com 에서 패턴 먼저 테스트
- 플래그: `gi` (global, case-insensitive)

### 3. 정확도 확인
- `accuracy_checker.py` 사용 (별도 파일)
- 정답 데이터 만들어서 자동 측정

### 4. 로그 파일 저장
```python
# 출력을 파일로 저장하려면:
python posco_parser.py > log.txt
```

---

## 📚 관련 문서

- `accuracy_checker.md` - 정확도 측정 방법
- `test_data_sample.json` - 정답 데이터 예시

---

## ✅ 체크리스트

설정:
- [ ] Python 3.8+ 설치됨
- [ ] `pip install PyMuPDF` 완료
- [ ] INPUT_FOLDER 경로 수정함
- [ ] r"경로" 형식 지킴

실행:
- [ ] `python posco_parser.py` 실행
- [ ] 오류 없이 완료됨
- [ ] parsed_results 폴더 생성 확인
- [ ] JSON 파일 열어서 데이터 확인

커스터마이징 (선택):
- [ ] 정규식 패턴 이해함
- [ ] 필요한 패턴 추가함
- [ ] 새 필드 추가함
- [ ] 정확도 측정함

---

**이 하나의 파일이면 충분합니다!**
필요시 정규식 패턴만 수정하세요.
