# SAP Script Recording으로 정확한 경로 찾기

## 문제 상황
D-term 다운로더가 "Tree control not found" 에러로 실패합니다. ZTDR0210 화면 구조가 예상과 다를 수 있어서 SAP에서 직접 레코딩하여 정확한 경로를 찾아야 합니다.

## SAP Script Recording 사용 방법

### 1. Script Recording 열기
1. SAP GUI를 실행하고 로그인합니다
2. **Alt + F12** 키를 누릅니다
3. 또는 메뉴: `Customize Local Layout` > `Script Recording and Playback`

### 2. 레코딩 시작
1. Script Recording 창에서 **"Record"** 버튼 클릭
2. 다음 작업을 **정확히** 수행:
   ```
   a. T-code 입력: /nZTDR0210
   b. Date 필드 클리어 (S_BUDAT-LOW 필드)
   c. Billing Document 입력 (예: 94511241)
   d. F8 실행 버튼 클릭
   e. 결과 화면에서 증빙 파일이 있는 트리/폴더 클릭
   f. 파일 하나를 더블클릭하여 다운로드 다이얼로그 열기
   g. 다운로드 취소 (레코딩만 하면 됨)
   ```
3. **"Stop"** 버튼 클릭

### 3. 레코딩된 스크립트 확인
레코딩 창 하단에 VBScript가 생성됩니다. 다음 부분을 찾아주세요:

#### 찾아야 할 것 #1: 트리 컨트롤 경로
```vbs
session.findById("wnd[0]/usr/...").expandNode "..."
또는
session.findById("wnd[0]/usr/...").selectedNode = "..."
```

#### 찾아야 할 것 #2: 파일 다운로드 다이얼로그
```vbs
session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = "..."
session.findById("wnd[1]/usr/ctxtDY_PATH").text = "..."
```

### 4. 레코딩된 경로 복사
위에서 찾은 경로를 복사해주세요. 예:
```
wnd[0]/usr/cntlGRID1/shellcont/shell
또는
wnd[0]/usr/tabsTABSTRIP/tabpTAB1/ssubSUBSCREEN:PROGRAM:SCREEN/cntlTREE/shellcont/shell
```

## Tracker 사용 방법 (대안)

레코딩 대신 Tracker를 사용할 수도 있습니다:

1. Script Recording 창에서 **"Tracker"** 탭으로 이동
2. ZTDR0210에서 F8 실행 후 결과 화면 진입
3. 트리/폴더 영역을 **클릭**
4. Tracker에 해당 요소의 정확한 경로가 표시됨
5. 경로를 복사

## 경로 전달 방법

찾은 경로를 다음 형식으로 알려주세요:

```
트리 경로: wnd[0]/usr/...
다운로드 다이얼로그 경로: wnd[1]/usr/...
```

또는 레코딩된 VBScript 전체를 붙여넣어 주셔도 됩니다.

## 참고: DMS Downloader와 비교

DMS Downloader (ZSDR0390)의 구조:
```
1. F8 실행
2. 그리드 결과 클릭: wnd[0]/shellcont/shell.clickCurrentCell()
3. 첨부탭 선택: wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN.select()
4. 트리 접근: wnd[0]/usr/tabsTAB_MAIN/tabpTSMAIN/ssubSCR_MAIN:SAPLCV110:0102/cntlCTL_FILES1/shellcont/shell/shellcont[1]/shell
```

ZTDR0210도 비슷한 구조일 수 있지만, 탭 이름이나 경로가 다를 수 있습니다.
