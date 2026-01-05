' ZTDR0210 Debug Script
' SAP GUI 요소를 찾아서 출력하는 디버깅 스크립트
' Usage: cscript ztdr0210_debug.vbs <billing_document>

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
billingDoc = "94531411"
If WScript.Arguments.Count > 0 Then
    billingDoc = WScript.Arguments(0)
End If

WScript.Echo "=== ZTDR0210 Debug Mode ==="
WScript.Echo "Billing Document: " & billingDoc
WScript.Echo ""

' T-code 실행
session.findById("wnd[0]/tbar[0]/okcd").text = "/nZTDR0210"
session.findById("wnd[0]").sendVKey 0
WScript.Sleep 1500

' Date 필드 클리어
On Error Resume Next
session.findById("wnd[0]/usr/ctxtS_BUDAT-LOW").text = ""
Err.Clear

' Billing Document 입력
session.findById("wnd[0]/usr/ctxtS_VBELN-LOW").text = billingDoc
session.findById("wnd[0]/usr/ctxtS_VBELN-LOW").SetFocus
session.findById("wnd[0]").sendVKey 0

WScript.Sleep 3000

' 현재 창 정보 출력
WScript.Echo "=== Current Window Info ==="
WScript.Echo "Window Title: " & session.findById("wnd[0]").text
WScript.Echo ""

' usr 컨테이너 하위 요소 탐색
WScript.Echo "=== Exploring wnd[0]/usr children ==="
Set usrArea = session.findById("wnd[0]/usr")
If Not usrArea Is Nothing Then
    WScript.Echo "usr area found. Type: " & usrArea.Type

    ' usr의 모든 자식 요소 출력 (ID 기반 탐색)
    On Error Resume Next

    ' Try common control names
    Dim controlNames(15)
    controlNames(0) = "cntlGRID1"
    controlNames(1) = "cntlCONTAINER"
    controlNames(2) = "cntlCUSTOM_CONTAINER"
    controlNames(3) = "cntlTREE"
    controlNames(4) = "cntlCC_TREE"
    controlNames(5) = "shell"
    controlNames(6) = "tabsTABSTRIP"
    controlNames(7) = "cntlGRID"
    controlNames(8) = "cntlCTRL"
    controlNames(9) = "ssubMAIN"
    controlNames(10) = "shellcont"

    For i = 0 To 10
        Err.Clear
        ctrlPath = "wnd[0]/usr/" & controlNames(i)
        Set ctrl = session.findById(ctrlPath)
        If Err.Number = 0 And Not ctrl Is Nothing Then
            WScript.Echo "  [FOUND] " & ctrlPath & " - Type: " & ctrl.Type

            ' If it's a container, try to find shell inside
            If ctrl.Type = "GuiContainer" Or ctrl.Type = "GuiCustomControl" Or ctrl.Type = "GuiContainerShell" Then
                Err.Clear
                Set shellTest = session.findById(ctrlPath & "/shellcont")
                If Err.Number = 0 And Not shellTest Is Nothing Then
                    WScript.Echo "    -> shellcont found: " & shellTest.Type

                    Err.Clear
                    Set shellTest2 = session.findById(ctrlPath & "/shellcont/shell")
                    If Err.Number = 0 And Not shellTest2 Is Nothing Then
                        WScript.Echo "    -> shell found: " & shellTest2.Type
                    End If
                End If
            End If
        End If
        Err.Clear
    Next
Else
    WScript.Echo "usr area not found!"
End If

WScript.Echo ""
WScript.Echo "=== Trying common tree paths ==="

' 여러 경로 시도
Dim treePaths(10)
treePaths(0) = "wnd[0]/usr/cntlGRID1/shellcont/shell/shellcont[1]/shell"
treePaths(1) = "wnd[0]/usr/cntlGRID1/shellcont/shell"
treePaths(2) = "wnd[0]/usr/shell"
treePaths(3) = "wnd[0]/usr/cntlCONTAINER/shellcont/shell"
treePaths(4) = "wnd[0]/usr/tabsTABSTRIP/tabpTAB1/ssubSUBSCREEN:SAPLKKBL:0101/cntlGRID1/shellcont/shell"
treePaths(5) = "wnd[0]/usr/cntlCUSTOM_CONTAINER/shellcont/shell"
treePaths(6) = "wnd[0]/usr/cntlTREE/shellcont/shell"
treePaths(7) = "wnd[0]/usr/cntlCC_TREE/shellcont/shell"
treePaths(8) = "wnd[0]/shellcont/shell"
treePaths(9) = "wnd[0]/usr/ssubMAIN:SAPLKKBL:0101/cntlGRID1/shellcont/shell"

For i = 0 To 9
    On Error Resume Next
    Set testTree = session.findById(treePaths(i))
    If Err.Number = 0 And Not testTree Is Nothing Then
        WScript.Echo "[FOUND] " & treePaths(i) & " - Type: " & testTree.Type
    Else
        WScript.Echo "[NOT FOUND] " & treePaths(i)
    End If
    Err.Clear
Next

WScript.Echo ""
WScript.Echo "=== Complete ==="
WScript.Echo "Please check the output above to find the correct tree path."
