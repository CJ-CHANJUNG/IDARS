# accuracy_checker.py 사용 가이드

## 📋 개요

파싱 결과의 정확도를 자동으로 측정하는 도구입니다.
정답 데이터와 파싱 결과를 비교하여 필드별 정확도를 계산합니다.

**정확도 개선 작업시 필수 도구!**

---

## 🎯 언제 사용하나요?

- 현재 파싱 정확도를 알고 싶을 때
- 패턴 수정 전후 비교할 때
- 어떤 필드가 가장 많이 틀리는지 알고 싶을 때
- 95% 정확도 목표 달성을 위한 개선 작업시

---

## 🚀 빠른 시작

### 1단계: 정답 데이터 만들기

`test_data.json` 파일 생성:

```json
{
  "sample1.pdf": {
    "invoice": {
      "invoice_number": "1234567",
      "invoice_date": "2025-06-30",
      "currency": "EUR",
      "total_amount": 54656.40
    },
    "bl": {
      "bl_number": "PLIHQ4G81934",
      "vessel_name": "CMA CGM PLATINUM"
    }
  },
  "sample2.pdf": {
    "invoice": {
      "invoice_number": "7654321",
      "currency": "USD",
      "total_amount": 123456.78
    }
  }
}
```

**작성 팁:**
- PDF 20-30개 샘플로 시작
- 손으로 직접 확인하여 정답 입력
- 중요한 필드 위주로 (invoice_number, total_amount 등)

### 2단계: 설정하기

`accuracy_checker.py` 파일 열어서 상단 수정:

```python
# 🔧 사용자 설정
GROUND_TRUTH_FILE = r"D:\test_data.json"  # ← 정답 파일 경로
PDF_FOLDER = ""                            # 비워두면 자동
```

### 3단계: 실행하기

```bash
python accuracy_checker.py
```

### 4단계: 결과 확인

화면에 출력됨:

```
📊 정확도 리포트
════════════════════════════════════════
invoice.invoice_number              :  85.00% (17/20)
invoice.total_amount                :  70.00% (14/20)
invoice.currency                    :  95.00% (19/20)
bl.bl_number                        :  60.00% (12/20)
════════════════════════════════════════
전체 정확도                          :  77.50% (62/80)

❌ 가장 많이 틀리는 필드 TOP 5
════════════════════════════════════════
  bl.bl_number                      : 8개 틀림
  invoice.total_amount              : 6개 틀림
  invoice.invoice_number            : 3개 틀림
```

`accuracy_report.json` 파일도 생성됨 (상세 결과)

---

## ⚙️ 설정 항목

### GROUND_TRUTH_FILE (필수)
- **설명**: 정답 데이터 JSON 파일 경로
- **형식**: `r"경로"`
- **예시**:
  ```python
  GROUND_TRUTH_FILE = r"D:\test_data.json"
  GROUND_TRUTH_FILE = r"C:\Users\홍길동\Documents\test_data.json"
  ```

### PDF_FOLDER (선택)
- **설명**: PDF 파일들이 있는 폴더
- **기본값**: `""` (정답 파일과 같은 폴더)
- **예시**:
  ```python
  PDF_FOLDER = ""                    # 자동 탐색
  PDF_FOLDER = r"D:\PDFs"            # 직접 지정
  ```

---

## 📝 정답 데이터 작성 가이드

### 기본 구조
```json
{
  "PDF파일명.pdf": {
    "문서유형": {
      "필드명": "정답값"
    }
  }
}
```

### 전체 예시
```json
{
  "거래1.pdf": {
    "invoice": {
      "invoice_number": "1234567",
      "invoice_date": "2025-06-30",
      "currency": "EUR",
      "total_amount": 54656.40,
      "shipper": "POSCO INTERNATIONAL CORPORATION",
      "port_of_loading": "BUSAN, KOREA"
    },
    "bl": {
      "bl_number": "PLIHQ4G81934",
      "vessel_name": "CMA CGM PLATINUM",
      "port_of_loading": "BUSAN, KOREA",
      "port_of_discharge": "KOPER, SLOVENIA",
      "gross_weight": 23600.0
    },
    "packing_list": {
      "net_weight": 22200.0,
      "gross_weight": 23600.0,
      "number_of_packages": 28
    }
  },
  
  "거래2.pdf": {
    "invoice": {
      "invoice_number": "7654321",
      "currency": "USD",
      "total_amount": 123456.78
    }
  }
}
```

### 작성 팁

**1. 샘플 수**
- 최소 20개 추천
- 정확도 향상 작업시 30-50개 권장

**2. 다양성**
- 여러 거래처 (독일, 일본, 베트남 등)
- 다양한 금액대
- 다양한 상품 유형

**3. 중요 필드 위주**
- 필수: invoice_number, total_amount, currency
- 추가: bl_number, vessel_name, dates
- 선택: 긴 텍스트 필드 (shipper 주소 등)

**4. 정확성**
- PDF 열어서 직접 확인
- 복사-붙여넣기 활용
- 숫자는 쉼표 제거 (54656.40)

---

## 📊 결과 해석

### 정확도 점수 해석
- **95% 이상**: 훌륭! 프로덕션 준비 완료
- **85-94%**: 좋음! 조금만 더 개선
- **70-84%**: 개선 필요
- **70% 미만**: 많은 개선 필요

### TOP 에러 필드 활용
1. 가장 틀리는 필드 확인
2. 해당 필드의 실패 케이스 분석
3. `posco_parser.py`에서 패턴 개선
4. 재측정
5. 반복

---

## 🔄 정확도 개선 워크플로우

### 전체 프로세스
```
1. 정답 데이터 생성 (test_data.json, 30개)
   ↓
2. 현재 정확도 측정
   python accuracy_checker.py
   → 68%
   ↓
3. TOP 3 필드 확인
   - bl.bl_number: 12개 틀림
   - invoice.total_amount: 8개 틀림
   - invoice.invoice_number: 6개 틀림
   ↓
4. bl_number 패턴 개선
   posco_parser.py 수정
   ↓
5. 재측정
   python accuracy_checker.py
   → 75%
   ↓
6. 3-5번 반복
   ↓
7. 95% 달성! 🎉
```

### 실전 예시

**1일차: 측정**
```bash
python accuracy_checker.py
# 결과: 68%
# TOP 에러: bl_number (12개), total_amount (8개)
```

**2일차: bl_number 개선**
```python
# posco_parser.py 수정
class Patterns:
    BL = {
        'bl_number': [
            r'기존패턴',
            r'새패턴1',  # ← 추가!
            r'새패턴2',  # ← 추가!
        ],
    }
```
```bash
python accuracy_checker.py
# 결과: 75% (개선됨!)
```

**3일차: total_amount 개선**
```python
# posco_parser.py 수정 후
python accuracy_checker.py
# 결과: 82%
```

**4-5일차: 반복**
```bash
# 계속 반복...
# 최종: 95% 달성! 🎉
```

---

## 🐛 문제 해결

### 오류: "정답 파일이 없습니다"
**해결**:
1. `test_data_sample.json` 복사
2. 이름을 `test_data.json`으로 변경
3. 실제 값으로 채우기
4. GROUND_TRUTH_FILE 경로 확인

### 오류: "PDF 파일을 찾을 수 없습니다"
**해결**:
1. PDF_FOLDER 경로 확인
2. 정답 파일의 파일명과 실제 파일명 일치 확인
3. 확장자 .pdf 확인

### JSON 파싱 오류
**해결**:
1. https://jsonlint.com 에서 JSON 검증
2. 쉼표, 따옴표 확인
3. 마지막 항목 뒤 쉼표 제거

### 정확도가 계속 낮음
**원인**:
1. 패턴이 맞지 않음
2. PDF 품질이 낮음 (스캔 이미지 등)

**해결**:
1. 실패한 케이스 직접 확인
2. 패턴 수정
3. 필요시 OCR 재처리

---

## 💡 팁

### 1. 빠른 정답 데이터 생성
```python
# 먼저 파싱 실행
python posco_parser.py

# 결과 JSON 열어서 복사-붙여넣기
# 잘못된 값만 수정
```

### 2. 점진적 확장
```
1일차: 10개 샘플로 시작
2일차: 20개로 확장
3일차: 30개로 확장
```

### 3. 거래처별 그룹화
```json
{
  "독일_거래1.pdf": {...},
  "독일_거래2.pdf": {...},
  "일본_거래1.pdf": {...},
  "베트남_거래1.pdf": {...}
}
```

### 4. 버전 관리
```
test_data_v1.json  (68% 정확도)
test_data_v2.json  (75% 정확도)
test_data_v3.json  (85% 정확도)
```

---

## 📚 관련 문서

- `posco_parser.md` - 메인 파서 사용법
- `test_data_sample.json` - 정답 데이터 예시

---

## ✅ 체크리스트

정답 데이터 준비:
- [ ] test_data.json 생성
- [ ] 20-30개 샘플 준비
- [ ] 중요 필드 위주로 작성
- [ ] JSON 형식 검증

설정:
- [ ] GROUND_TRUTH_FILE 경로 설정
- [ ] PDF_FOLDER 경로 확인
- [ ] posco_parser.py와 같은 폴더

실행:
- [ ] python accuracy_checker.py 실행
- [ ] 정확도 확인
- [ ] accuracy_report.json 생성 확인

개선 작업:
- [ ] TOP 에러 필드 확인
- [ ] 실패 케이스 분석
- [ ] 패턴 개선
- [ ] 재측정
- [ ] 95% 목표 달성

---

**정확도 개선의 핵심 도구!**
꾸준히 측정하고 개선하세요.
