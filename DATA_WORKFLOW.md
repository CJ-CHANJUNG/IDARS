# 전표 데이터 처리 워크플로우

전표 데이터(엑셀)를 CSV로 변환하고 처리하는 자동화 워크플로우입니다.

## 📁 폴더 구조

```
project/
├── data/
│   ├── raw/          # 원본 엑셀 파일 (암호화된 파일)
│   ├── processed/    # CSV 변환된 파일
│   └── output/       # 최종 결과 파일
├── scripts/
│   ├── convert_to_csv.py   # 엑셀 → CSV 변환 스크립트
│   └── process_data.py     # 데이터 처리 스크립트
└── excel data/       # (기존) 임시 보관용
```

## 🔄 워크플로우

### 1단계: 엑셀 파일 준비

보안 암호화된 엑셀 파일은 Python으로 직접 읽을 수 없으므로:

1. 엑셀에서 파일 열기
2. **다른 이름으로 저장** → **CSV UTF-8 (쉼표로 분리)** 선택
3. `data/raw/` 폴더에 저장

```
예: EXPORT.xlsx → data/raw/EXPORT.csv
```

### 2단계: CSV 변환 및 검증

```bash
python scripts/convert_to_csv.py EXPORT.csv
```

이 스크립트는:
- ✅ 파일 로드 및 검증
- ✅ 데이터 정보 출력 (행/열 개수, 컬럼 목록)
- ✅ 미리보기 표시
- ✅ `data/processed/` 폴더로 복사

### 3단계: 데이터 처리

#### 기본 정보 확인

```bash
python scripts/process_data.py EXPORT.csv
```

#### 요약 통계 보기

```bash
python scripts/process_data.py EXPORT.csv --summary
```

#### 데이터 필터링

```bash
# 특정 조건 필터링
python scripts/process_data.py EXPORT.csv --filter "금액 > 1000000"

# 컬럼명에 공백이 있는 경우 백틱 사용
python scripts/process_data.py EXPORT.csv --filter "`전표 금액` > 1000000"
```

#### 그룹화 및 집계

```bash
# 전표번호별 합계
python scripts/process_data.py EXPORT.csv --groupby "전표번호"

# 여러 컬럼으로 그룹화
python scripts/process_data.py EXPORT.csv --groupby "전표번호,선적일자" --agg sum

# 평균 계산
python scripts/process_data.py EXPORT.csv --groupby "전표번호" --agg mean
```

#### 결과 내보내기

```bash
# CSV로 저장
python scripts/process_data.py EXPORT.csv --filter "금액 > 1000000" --export result.csv

# 엑셀로 저장
python scripts/process_data.py EXPORT.csv --groupby "전표번호" --export summary.xlsx
```

## 💡 사용 예시

### 예시 1: 고액 전표만 필터링하여 저장

```bash
python scripts/process_data.py EXPORT.csv --filter "금액 > 5000000" --export high_value.xlsx
```

### 예시 2: 전표번호별 합계 리포트

```bash
python scripts/process_data.py EXPORT.csv --groupby "전표번호" --agg sum --export summary_by_invoice.xlsx
```

### 예시 3: 선적일자별 통계

```bash
python scripts/process_data.py EXPORT.csv --groupby "선적일자" --summary --export daily_summary.csv
```

## 🛠️ 필요 라이브러리

```bash
pip install pandas openpyxl
```

## 📝 팁

### 1. 빠른 파일 변환

엑셀에서 CSV 저장 시:
- **파일 형식**: CSV UTF-8 (쉼표로 분리)
- **위치**: `data/raw/` 폴더
- 원본 파일명 유지 권장

### 2. 컬럼명 확인

처리 전 컬럼명을 먼저 확인:

```bash
python scripts/process_data.py EXPORT.csv --info
```

### 3. 복잡한 필터링

pandas query 문법 사용 가능:

```bash
# AND 조건
python scripts/process_data.py EXPORT.csv --filter "금액 > 1000000 and 금액 < 10000000"

# OR 조건
python scripts/process_data.py EXPORT.csv --filter "전표번호 == 'A001' or 전표번호 == 'A002'"

# 문자열 포함
python scripts/process_data.py EXPORT.csv --filter "전표번호.str.contains('2024')"
```

### 4. 배치 처리

여러 파일을 한번에 처리하려면 쉘 스크립트 작성:

```bash
# batch_process.sh (Linux/Mac)
for file in data/raw/*.csv; do
    python scripts/process_data.py "$file" --export "output/$(basename $file)"
done
```

```cmd
# batch_process.bat (Windows)
for %%f in (data\raw\*.csv) do (
    python scripts/process_data.py "%%f" --export "output/%%~nxf"
)
```

## 🔐 보안 주의사항

- ⚠️ CSV 파일은 암호화되지 않습니다
- ⚠️ 민감한 데이터는 처리 후 삭제 권장
- ⚠️ `data/processed/`와 `data/output/` 폴더를 `.gitignore`에 추가

## ❓ 문제 해결

### "파일을 찾을 수 없습니다"

- `data/raw/` 폴더에 파일이 있는지 확인
- 파일명이 정확한지 확인 (대소문자 구분)

### "엑셀 파일을 읽을 수 없습니다"

- 보안 암호화된 파일은 직접 읽을 수 없음
- 엑셀에서 CSV로 저장 후 다시 시도

### "컬럼을 찾을 수 없습니다"

- `--info` 옵션으로 컬럼명 확인
- 공백이 있는 컬럼명은 백틱(`)으로 감싸기

## 🚀 향후 개선 사항

- [ ] GUI 인터페이스 추가
- [ ] 자동 폴더 감시 기능
- [ ] 데이터 검증 규칙 추가
- [ ] 리포트 템플릿 기능
- [ ] 데이터베이스 연동
