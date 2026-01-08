🔴 Critical Issues
1. 재시도 로직의 구조적 결함
문제 위치
python# Line 281-310: extract_with_gemini_async()
for attempt in range(max_retries + 1):
    try:
        # ❌ prompt는 루프 밖에서 1회만 생성됨
        response = await self.gemini_model.generate_content_async(
            prompt,  # 동일한 프롬프트 반복 전송
            generation_config={"response_mime_type": "application/json"}
        )
근본 원인

프롬프트 생성 위치: prompt 변수가 for 루프 시작 전에 한 번만 생성됨
재시도 보강 무효화: Line 301의 prompt += f"""..."""는 첫 번째 실패 후 실행되지만, 다음 iteration에서 원본 prompt로 초기화되지 않음
결과: 재시도 시 동일한 프롬프트만 반복 전송 → Gemini가 동일한 실수 반복

영향

N:1 매칭 실패 시 "라인 아이템 조합 분석" 지시사항이 실제로 전달되지 않음
최대 3회 재시도해도 성공률 개선 없음


2. 좌표(Coordinates) 추출 불가
문제 위치
python# Line 193-198: _build_extraction_prompt()
if 'currency' in output_format:
    expected_fields_example[field['name']] = {
        "value": 0.0, 
        "currency": "USD", 
        "coordinates": [0, 0, 0, 0]  # ❌ 단순 예시 값
    }
근본 원인

입력 데이터 부족

Gemini에게 OCR 텍스트만 제공
PDF 이미지나 위치 정보 없음
텍스트 기반으로는 좌표 추정 불가능


명확한 지시사항 부재

프롬프트에 "좌표를 추출하라"는 직접적 요구사항 없음
coordinates: [0, 0, 0, 0]는 응답 형식 예시일 뿐, 실제 추출 방법 설명 부재


기술적 한계

현재 사용 중인 gemini-2.0-flash는 텍스트 모델
Vision 기능 미활용 → 이미지 분석 불가



영향

하이라이트 기능 완전 작동 불가
모든 문서의 coordinates 필드가 [0, 0, 0, 0] 또는 null


3. N:1 매칭 검증 프롬프트의 모호성
문제 위치
python# Line 301-309
prompt += f"""
**REQUIRED ACTION:**
1. **SEARCH**: Look for the exact value {exp_amount}...
2. **COMBINE**: If the exact value is not found as a single number, 
   look for a combination of line items that sums up EXACTLY to {exp_amount}.
"""
근본 원인

구체성 부족

"combination of line items"라는 추상적 표현
Invoice 구조(Header, Line Items, Subtotal, Tax, Total)에 대한 컨텍스트 제공 없음
어떤 필드들을 조합해야 하는지 명시 부재


탐색 전략 부재

라인 아이템을 어떻게 식별할지 지시 없음
테이블 구조 인식 방법 설명 없음
수량 × 단가 = 금액 검증 로직 요구사항 부재


증거(Evidence) 요구사항 미흡

"어떻게 찾았는지" 설명 요청 없음
조합한 라인 번호 반환 요구 부재



영향

Gemini가 라인 아이템 스캔 없이 대충 근사치만 반환
기대값과 일치하는 라인이 명백히 있어도 발견 실패


🟡 Secondary Issues
4. 검증 실패 이력 미추적
문제

재시도 간 학습 불가
이전 시도에서 왜 실패했는지 정보 누적 없음

코드 증거
python# Line 303: if attempt == 0:
# → 첫 시도 실패만 감지, 2/3차 시도 결과는 무시됨
```

---

### 5. **토큰 효율성 문제**

#### 현재 구조
- 전체 OCR 텍스트(최대 3페이지)를 매 요청마다 전송
- 재시도 시 **동일한 텍스트 반복 전송**

#### 비효율 사례
```
1차 시도: 5,000 토큰 입력 → 실패
2차 시도: 5,000 토큰 입력 (동일) → 실패
3차 시도: 5,000 토큰 입력 (동일) → 실패
총 15,000 토큰 소비 (실제 필요: 5,000)
```

---

## 💡 Root Cause Analysis

### 핵심 설계 오류
```
┌─────────────────────────────────────────┐
│  현재 아키텍처                          │
├─────────────────────────────────────────┤
│  1. OCR 텍스트 추출                     │
│  2. Gemini에 텍스트 전송                │
│  3. JSON 응답 파싱                      │
│  4. 검증 실패 시 → 동일 프롬프트 재전송│  ❌
└─────────────────────────────────────────┘

문제점:
- Gemini는 "stateless" → 이전 실패 모름
- 동일 입력 = 동일 출력 (확률적 변동만 존재)
- 좌표 정보 소실 (이미지 미사용)