# ZTDR0210 다운로더 설정 가이드

## 문제: Tree Control을 찾을 수 없음

VBS 스크립트가 SAP GUI의 트리 컨트롤을 찾지 못하고 있습니다.

## 해결 방법

### 1. SAP Scripting Tracker 사용

1. SAP GUI를 엽니다
2. ZTDR0210 트랜잭션으로 이동합니다
3. 전표번호를 입력하고 실행합니다
4. **Script Recording and Playback** 창을 엽니다:
   - ALT + F12를 누르거나
   - 메뉴에서 Customize Local Layout > Script Recording and Playback

5. Tracker 탭으로 이동합니다

6. 트리 컨트롤 영역을 클릭하면 해당 요소의 정확한 경로가 표시됩니다
   예: `wnd[0]/usr/cntlGRID1/shellcont/shell/shellcont[1]/shell`

7. 트리의 노드를 클릭해보면서 경로를 확인합니다

### 2. VBS 스크립트 수정

정확한 경로를 찾은 후:

1. `ztdr0210.vbs` 파일을 엽니다
2. 56-61번 라인의 `treePaths` 배열에 찾은 경로를 추가합니다:

```vbs
treePaths(0) = "실제로찾은경로"
```

### 3. 수동 다운로드 방법

자동화가 작동하지 않는 경우:

1. SAP에서 ZTDR0210을 수동으로 실행
2. 각 전표의 첨부파일을 수동으로 다운로드
3. 파일명을 `{전표번호}_{원본파일명}` 형식으로 저장
4. `step2_evidence_collection/dterm_downloads` 폴더에 저장
5. 프론트엔드에서 "수동 업로드" 버튼 사용

### 4. 자주 발생하는 경로들

다음 경로들을 시도해보세요:

```
wnd[0]/usr/cntlGRID1/shellcont/shell/shellcont[1]/shell
wnd[0]/usr/cntlGRID1/shellcont/shell
wnd[0]/usr/cntlCONTAINER/shellcont/shell
wnd[0]/usr/shell
wnd[0]/shellcont/shell
```

## 디버그 로그 확인

다운로드 실행 시 `dterm_debug.log` 파일에 로그가 기록됩니다.
이 파일을 확인하면 어떤 단계에서 실패했는지 알 수 있습니다.
