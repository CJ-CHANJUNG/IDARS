' ZTDR0210 SAP GUI Automation Script
' D조건 도착 증빙 다운로드
' Usage: cscript ztdr0210.vbs <billing_document> <save_path>

On Error Resume Next

' SAP GUI 연결
Set SapGuiAuto = GetObject("SAPGUI")
If Err.Number <> 0 Then
    WScript.Echo "Error: SAP GUI not found. Please open SAP first."
    WScript.Quit 1
End If

Set application = SapGuiAuto.GetScriptingEngine
Set connection = application.Children(0)
Set session = connection.Children(0)

If Err.Number <> 0 Then
    WScript.Echo "Error: SAP session not found"
    WScript.Quit 1
End If

Err.Clear

' 커맨드 라인 인자 받기
If WScript.Arguments.Count < 2 Then
    WScript.Echo "Usage: cscript ztdr0210.vbs <billing_document> <save_path>"
    WScript.Quit 1
End If

billingDoc = WScript.Arguments(0)
savePath = WScript.Arguments(1)

WScript.Echo "Starting download for: " & billingDoc

' T-code 실행
WScript.Echo "[STEP 1] Executing T-code ZTDR0210..."
session.findById("wnd[0]/tbar[0]/okcd").text = "/nZTDR0210"
session.findById("wnd[0]").sendVKey 0
WScript.Sleep 1500
WScript.Echo "[STEP 1] ✓ T-code executed"

' Date 필드 클리어 (중요!)
WScript.Echo "[STEP 2] Clearing date field..."
On Error Resume Next
session.findById("wnd[0]/usr/ctxtS_BUDAT-LOW").text = ""
If Err.Number <> 0 Then
    WScript.Echo "[STEP 2] Warning: Date field not found (Error: " & Err.Number & ")"
Else
    WScript.Echo "[STEP 2] ✓ Date field cleared"
End If
Err.Clear

' Billing Document 입력
WScript.Echo "[STEP 3] Entering billing document: " & billingDoc
On Error Resume Next
session.findById("wnd[0]/usr/ctxtS_VBELN-LOW").text = billingDoc
If Err.Number <> 0 Then
    WScript.Echo "[STEP 3] ERROR: Billing document field not found (Error: " & Err.Number & ")"
    WScript.Quit 1
End If
session.findById("wnd[0]/usr/ctxtS_VBELN-LOW").SetFocus
WScript.Sleep 100
Err.Clear
WScript.Echo "[STEP 3] ✓ Billing document entered"

' F8 실행 버튼 클릭 (중요!)
WScript.Echo "[STEP 3.5] Pressing F8 (Execute) button..."
On Error Resume Next
session.findById("wnd[0]/tbar[1]/btn[8]").press
If Err.Number <> 0 Then
    WScript.Echo "[STEP 3.5] ERROR: Execute button not found (Error: " & Err.Number & ")"
    WScript.Quit 1
End If
Err.Clear
WScript.Echo "[STEP 3.5] ✓ Execute button pressed"

' 결과 로딩 대기
WScript.Echo "[STEP 4] Waiting for results to load (3 seconds)..."
WScript.Sleep 3000
WScript.Echo "[STEP 4] ✓ Wait completed"

' 트리 구조 찾기 (여러 가능한 경로 시도)
WScript.Echo "[STEP 5] Searching for tree control..."
Set tree = Nothing
Dim treePaths(5)
treePaths(0) = "wnd[0]/usr/cntlGRID1/shellcont/shell/shellcont[1]/shell"
treePaths(1) = "wnd[0]/usr/cntlGRID1/shellcont/shell"
treePaths(2) = "wnd[0]/usr/shell"
treePaths(3) = "wnd[0]/usr/cntlCONTAINER/shellcont/shell"
treePaths(4) = "wnd[0]/usr/tabsTABSTRIP/tabpTAB1/ssubSUBSCREEN:SAPLKKBL:0101/cntlGRID1/shellcont/shell"

For i = 0 To 4
    WScript.Echo "[STEP 5." & (i+1) & "] Trying path: " & treePaths(i)
    On Error Resume Next
    Set tree = session.findById(treePaths(i))
    If Err.Number <> 0 Then
        WScript.Echo "[STEP 5." & (i+1) & "] ✗ Not found (Error: " & Err.Number & " - " & Err.Description & ")"
    ElseIf tree Is Nothing Then
        WScript.Echo "[STEP 5." & (i+1) & "] ✗ Element is Nothing"
    Else
        WScript.Echo "[STEP 5." & (i+1) & "] ✓ FOUND! Type: " & tree.Type
        Exit For
    End If
    Err.Clear
Next

If tree Is Nothing Then
    WScript.Echo "[STEP 5] ERROR: Tree control not found in any known path"
    WScript.Echo "[STEP 5] Current window title: " & session.findById("wnd[0]").text
    WScript.Quit 1
End If

WScript.Echo "[STEP 5] ✓ Tree control located successfully"
Err.Clear

nodeCount = 0
fileCount = 0

' 먼저 루트 노드 확장 시도
WScript.Echo "[STEP 6] Expanding root node..."
On Error Resume Next
tree.expandNode "          1"
If Err.Number <> 0 Then
    WScript.Echo "[STEP 6] Warning: Could not expand root node (Error: " & Err.Number & ")"
Else
    WScript.Echo "[STEP 6] ✓ Root node expanded"
End If
WScript.Sleep 1000
Err.Clear

WScript.Echo "[STEP 7] Starting file download from tree nodes..."

' 노드 순회하며 다운로드 (노드 2부터 시작, 최대 30개)
For nodeIdx = 2 To 30
    ' 노드 키 포맷: 10자리 공백 + 번호
    nodeKey = Right("          " & nodeIdx, 10)

    On Error Resume Next

    ' 노드 선택
    tree.selectedNode = nodeKey

    If Err.Number = 0 Then
        WScript.Echo "[STEP 7." & nodeIdx & "] Processing node " & nodeIdx & "..."
        nodeCount = nodeCount + 1
        WScript.Sleep 300

        ' 더블클릭으로 파일 열기
        WScript.Echo "[STEP 7." & nodeIdx & ".1] Double-clicking node..."
        tree.doubleClickNode nodeKey
        WScript.Sleep 1500

        ' 다운로드 다이얼로그 확인
        Err.Clear
        Set dlg = session.findById("wnd[1]")

        If Err.Number = 0 And Not dlg Is Nothing Then
            ' 파일명 필드 찾기
            Err.Clear
            originalFilename = session.findById("wnd[1]/usr/ctxtDY_FILENAME").text

            If Err.Number = 0 And originalFilename <> "" Then
                ' 저장 파일명 생성
                saveFilename = billingDoc & "_" & originalFilename

                ' 다운로드 경로 및 파일명 설정
                On Error Resume Next
                session.findById("wnd[1]/usr/ctxtDY_PATH").text = savePath
                session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = saveFilename

                ' 저장 버튼 클릭
                session.findById("wnd[1]/tbar[0]/btn[0]").press
                WScript.Sleep 800

                fileCount = fileCount + 1
                WScript.Echo "  Downloaded: " & saveFilename

                ' 확인 메시지가 있을 경우 처리
                Err.Clear
                On Error Resume Next
                session.findById("wnd[2]/usr/btnSPOP-OPTION1").press
                WScript.Sleep 300
            Else
                WScript.Echo "  No filename found, skipping..."
            End If

            ' 다이얼로그 닫기 (혹시 열려있을 경우)
            Err.Clear
            On Error Resume Next
            session.findById("wnd[1]/tbar[0]/btn[0]").press
            WScript.Sleep 300
        Else
            WScript.Echo "  No download dialog, might be a folder node"
        End If

        ' 원래 화면으로 돌아가기
        Err.Clear
        On Error Resume Next

        ' Back 버튼 시도
        session.findById("wnd[0]/tbar[0]/btn[3]").press
        WScript.Sleep 300

        ' 혹은 Escape 키
        If Err.Number <> 0 Then
            Err.Clear
            session.findById("wnd[0]").sendVKey 12  ' F12 = Back
            WScript.Sleep 300
        End If

        Err.Clear
    Else
        ' 노드를 찾을 수 없으면 종료
        WScript.Echo "No more nodes found at index " & nodeIdx
        Exit For
    End If

    Err.Clear
Next

WScript.Echo ""
WScript.Echo "=== Download Complete ==="
WScript.Echo "Total nodes processed: " & nodeCount
WScript.Echo "Total files downloaded: " & fileCount
WScript.Quit 0
