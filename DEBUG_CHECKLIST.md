# 임시 디버깅 체크리스트

사용자에게 확인받을 사항:

## 브라우저 콘솔 확인 (F12 → Console 탭)
1. 새 프로젝트 생성 시 로그:
   - `Starting project: [프로젝트명] local` 또는 `Starting project: [프로젝트명] sap`
   - `Project created: {id: "...", ...}`
   - `Opening modal for source: local` 또는 `sap`
   - `Setting modal open true`

2. 파일 선택 시 로그:
   - `[MODAL] File selected: test.csv` ← 이 로그가 나와야 함!
   - `[FILE UPLOAD] Starting upload for file: test.csv` ← 이것도 나와야 함!

3. 에러가 있다면 빨간색으로 표시됨

## 브라우저 네트워크 확인 (F12 → Network 탭)
1. Network 탭 열기
2. 파일 업로드 시도
3. `/api/upload` 요청이 나타나는지 확인
   - 나타난다면: Status가 200인지, 400/500 에러인지 확인
   - 안 나타난다면: 요청 자체가 전송되지 않음 = 프론트엔드 문제

## 캐시 문제 확인
- Ctrl + Shift + R (강력 새로고침) 해보기
- 또는 Ctrl + F5

## 현재 상태
- 백엔드: 요청 0개 수신 = 프론트엔드에서 요청을 보내지 않고 있음
