# pdf_splitter.py 사용 가이드

## 📋 개요

여러 문서가 섞인 PDF를 자동으로 분석하여 문서 유형별로 분류하고 개별 PDF로 분리하는 도구입니다.

**Parser 전에 반드시 거쳐야 하는 1단계!**

---

## 🎯 역할

```
┌─────────────────────────────────────────┐
│  원본 PDF (20페이지)                     │
│  ├─ 1-3p: Invoice                        │
│  ├─ 4-8p: Bill of Lading                 │
│  ├─ 9-10p: Packing List                  │
│  ├─ 11-15p: Certificate                  │
│  └─ 16-20p: Unknown                      │
└─────────────────────────────────────────┘
              ↓ [PDF Splitter]
┌─────────────────────────────────────────┐
│  분류된 개별 PDF                          │
│  ├─ invoice/                             │
│  │   └─ 원본_invoice_01.pdf (3페이지)    │
│  ├─ bl/                                  │
│  │   └─ 원본_bl_01.pdf (5페이지)         │
│  ├─ packing_list/                        │
│  │   └─ 원본_packing_list_01.pdf (2p)    │
│  └─ certificate/                         │
│      └─ 원본_certificate_01.pdf (5p)     │
└─────────────────────────────────────────┘
              ↓ [Parser로 전달]
          JSON 결과
```

---

## 🚀 빠른 시작

### 1. 설정
파일 상단 수정:

```python
# 🔧 사용자 설정
INPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Splitter\Input"      # ← 원본 PDF 폴더
OUTPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Splitter\Output"     # ← 결과 저장 폴더

# 분류할 문서 유형 선택
DOCUMENT_TYPES = {
    'invoice': True,         # ✅ 필요
    'bl': True,              # ✅ 필요
    'packing_list': True,    # ✅ 필요
    'certificate': True,     # ✅ 필요
    'insurance': False,      # ❌ 불필요
    'weight_list': False,    # ❌ 불필요
    'mill_test': False,      # ❌ 불필요
}
```

### 2. 실행
```bash
python pdf_splitter.py
```

### 3. 결과 확인
```
분류완료/
├─ invoice/
│   ├─ 문서1_invoice_01.pdf
│   └─ 문서2_invoice_01.pdf
├─ bl/
│   ├─ 문서1_bl_01.pdf
│   └─ 문서2_bl_01.pdf
├─ packing_list/
│   └─ 문서1_packing_list_01.pdf
└─ certificate/
    └─ 문서1_certificate_01.pdf
```

---

## ⚙️ 설정 항목

### INPUT_FOLDER (필수)
- **설명**: 원본 PDF가 들어있는 폴더
- **형식**: `r"경로"`
- **예시**:
  ```python
  INPUT_FOLDER = r"D:\CJ\원본문서"
  INPUT_FOLDER = r"C:\Users\홍길동\Documents\PDFs"
  ```

### OUTPUT_FOLDER (필수)
- **설명**: 분류된 PDF를 저장할 폴더
- **자동 생성**: 없으면 자동으로 만들어짐
- **구조**: 하위에 문서 유형별 폴더 자동 생성
- **예시**:
  ```python
  OUTPUT_FOLDER = r"D:\분류완료"
  OUTPUT_FOLDER = r"D:\CJ\정제된문서"
  ```

### DOCUMENT_TYPES (중요!)
- **설명**: 어떤 문서 유형을 분류할지 선택
- **True**: 분류함, **False**: 무시함
- **예시**:
  ```python
  # 기본 4가지만 분류
  DOCUMENT_TYPES = {
      'invoice': True,
      'bl': True,
      'packing_list': True,
      'certificate': True,
      'insurance': False,
      'weight_list': False,
      'mill_test': False,
  }
  
  # 모든 유형 분류
  DOCUMENT_TYPES = {
      'invoice': True,
      'bl': True,
      'packing_list': True,
      'certificate': True,
      'insurance': True,
      'weight_list': True,
      'mill_test': True,
  }
  ```

### MIN_PAGES (선택)
- **설명**: 최소 페이지 수 (이보다 작으면 무시)
- **기본값**: 1
- **예시**:
  ```python
  MIN_PAGES = 1    # 1페이지도 분리
  MIN_PAGES = 2    # 2페이지 이상만 분리
  ```

### VERBOSE (선택)
- **설명**: 상세 출력 여부
- **True**: 모든 과정 출력, **False**: 최소 출력
- **예시**:
  ```python
  VERBOSE = True     # 자세히 (추천)
  VERBOSE = False    # 간단히
  ```

---

## 🔍 분류 원리

### 키워드 기반 분류
각 페이지의 텍스트를 분석하여 키워드 점수를 계산합니다.

#### Invoice 키워드
```python
강한 증거 (10점):
  - "commercial invoice"
  - "proforma invoice"
  - "tax invoice"

중간 증거 (3점):
  - "invoice no"
  - "total amount"
  - "payment terms"

약한 증거 (1점):
  - "shipper"
  - "consignee"
```

#### BL 키워드
```python
강한 증거 (10점):
  - "bill of lading"
  - "b/l no"
  - "multimodal transport bill"

중간 증거 (3점):
  - "vessel"
  - "port of loading"
  - "container no"
```

### 신뢰도 계산
```
신뢰도 = 총 점수 / 15점

예시:
- 20점 → 100% 신뢰
- 15점 → 100% 신뢰
- 10점 → 67% 신뢰
- 5점 → 33% 신뢰
- 5점 미만 → unknown으로 분류
```

---

## 📊 출력 형식

### 폴더 구조
```
OUTPUT_FOLDER/
├─ invoice/              ← Invoice 문서들
│   ├─ 파일1_invoice_01.pdf
│   └─ 파일2_invoice_01.pdf
├─ bl/                   ← BL 문서들
│   └─ 파일1_bl_01.pdf
├─ packing_list/         ← Packing List 문서들
│   └─ 파일1_packing_list_01.pdf
├─ certificate/          ← Certificate 문서들
├─ insurance/            ← Insurance 문서들
└─ unknown/              ← 분류 실패 문서들
```

### 파일명 규칙
```
{원본파일명}_{문서유형}_{순번}.pdf

예시:
- 거래문서_invoice_01.pdf
- 거래문서_bl_01.pdf
- 거래문서_packing_list_01.pdf
```

---

## 🎯 실전 사용 예시

### 예시 1: 기본 분류
```python
# 설정
INPUT_FOLDER = r"D:\원본문서"
OUTPUT_FOLDER = r"D:\분류완료"

DOCUMENT_TYPES = {
    'invoice': True,
    'bl': True,
    'packing_list': True,
    'certificate': True,
    'insurance': False,
    'weight_list': False,
    'mill_test': False,
}
```

**실행:**
```bash
python pdf_splitter.py
```

**결과:**
```
📊 요약:
  - 원본 페이지: 25
  - 생성된 문서: 4
  - invoice: 1개
  - bl: 1개
  - packing_list: 1개
  - certificate: 1개
```

### 예시 2: 모든 유형 분류
```python
DOCUMENT_TYPES = {
    'invoice': True,
    'bl': True,
    'packing_list': True,
    'certificate': True,
    'insurance': True,      # ✅ 추가
    'weight_list': True,    # ✅ 추가
    'mill_test': True,      # ✅ 추가
}
```

### 예시 3: Invoice와 BL만
```python
DOCUMENT_TYPES = {
    'invoice': True,
    'bl': True,
    'packing_list': False,  # ❌ 제외
    'certificate': False,   # ❌ 제외
    'insurance': False,
    'weight_list': False,
    'mill_test': False,
}
```

---

## 🔄 Parser와 연계

### 전체 워크플로우

```bash
# 1단계: Splitter로 분류
python pdf_splitter.py

# 2단계: Parser로 필드 추출
# posco_parser.py 설정 변경
INPUT_FOLDER = r"D:\분류완료\invoice"  # ← Splitter 결과 사용
python posco_parser.py
```

### 자동화 스크립트 (선택)
```python
# pipeline.py
import subprocess

# 1단계: 분류
print("1단계: PDF 분류 중...")
subprocess.run(["python", "pdf_splitter.py"])

# 2단계: Invoice 파싱
print("2단계: Invoice 파싱 중...")
# posco_parser.py의 INPUT_FOLDER를 변경하거나
# 직접 호출

# 3단계: BL 파싱
print("3단계: BL 파싱 중...")
# ...
```

---

## 🐛 문제 해결

### 분류가 잘못됨
**원인**: 키워드가 부족하거나 애매한 문서
**해결**:
1. VERBOSE = True로 설정
2. 어떤 키워드로 분류되는지 확인
3. 필요시 `ClassificationRules.KEYWORDS` 수정

### unknown으로 너무 많이 분류됨
**원인**: 신뢰도가 낮음
**해결**:
1. 해당 PDF 열어서 확인
2. 어떤 키워드가 있는지 체크
3. 키워드 추가

### 하나의 문서가 여러 개로 쪼개짐
**원인**: 중간에 다른 유형으로 오인
**해결**:
1. 연속된 페이지를 같은 문서로 인식하도록 로직 개선
2. MIN_PAGES 늘리기

### 파일이 너무 많이 생성됨
**원인**: 페이지마다 다르게 분류
**해결**:
```python
MIN_PAGES = 2  # 2페이지 이상만 분리
```

---

## 💡 고급 활용

### 1. 키워드 추가
특정 거래처만의 특수 키워드가 있다면:

```python
# pdf_splitter.py 내부 수정
class ClassificationRules:
    KEYWORDS = {
        'invoice': {
            'strong': [
                'commercial invoice',
                '상업송장',        # ← 한글 추가!
                'VN-Invoice',     # ← 베트남용 추가!
            ],
            ...
        }
    }
```

### 2. 신뢰도 임계값 조정
```python
# 현재는 0.3 (30%) 미만이면 unknown
# 더 엄격하게: 0.5 (50%)로 변경

# pdf_splitter.py 약 300줄 근처
if cls['confidence'] < 0.5:  # ← 0.3에서 0.5로
    doc_type = 'unknown'
```

### 3. 커스텀 문서 유형 추가
```python
DOCUMENT_TYPES = {
    ...
    'customs_declaration': True,  # ← 새 유형!
}

# 그리고 ClassificationRules에 키워드 추가
KEYWORDS = {
    ...
    'customs_declaration': {
        'strong': ['customs declaration', 'import declaration'],
        'medium': ['hs code', 'tariff'],
        'weak': [],
    }
}
```

---

## 📚 관련 문서

- `posco_parser.md` - 2단계 Parser 가이드
- `README.md` - 프로젝트 전체 개요

---

## ✅ 체크리스트

**설정:**
- [ ] INPUT_FOLDER 경로 설정
- [ ] OUTPUT_FOLDER 경로 설정
- [ ] DOCUMENT_TYPES 선택
- [ ] r"경로" 형식 확인

**실행:**
- [ ] python pdf_splitter.py 실행
- [ ] 오류 없이 완료
- [ ] OUTPUT_FOLDER에 하위 폴더 생성 확인
- [ ] 각 폴더에 PDF 파일 확인

**검증:**
- [ ] 랜덤으로 몇 개 PDF 열어보기
- [ ] 분류가 올바른지 확인
- [ ] unknown 폴더 확인 (있다면 원인 분석)

**다음 단계:**
- [ ] posco_parser.py로 필드 추출
- [ ] 결과 검증

---

**Splitter → Parser → JSON**
단계별로 증빙을 정제하세요! 🚀
