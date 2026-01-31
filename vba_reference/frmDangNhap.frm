VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} frmDangNhap 
   Caption         =   "+++"
   ClientHeight    =   6210
   ClientLeft      =   120
   ClientTop       =   470
   ClientWidth     =   8100
   OleObjectBlob   =   "frmDangNhap.frx":0000
   ShowModal       =   0   'False
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "frmDangNhap"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Dim url As String, res As String, blnCaptcha As Boolean
Dim arrUsers

Private Sub cmdDauMK_Click()
    Me.txtPass.PasswordChar = "*"
    Me.cmdHienMK.Visible = True
    Me.cmdDauMK.Visible = False
End Sub

Private Sub cmdHienMK_Click()
    Me.txtPass.PasswordChar = ""
    Me.cmdHienMK.Visible = False
    Me.cmdDauMK.Visible = True
End Sub

Private Sub lblCapNhatMK_Click()
    If Me.txtUser <> "" Then
        sMST = Me.txtUser
        frmCapNhatMK.Show
    Else
        MsgBoxUni "T" & ChrW(234) & "n " & ChrW(273) & ChrW(259) & "ng nh" & ChrW(7853) & "p kh" & ChrW(244) & "ng " & ChrW(273) & ChrW(432) & ChrW(7907) & "c " & ChrW(273) & ChrW(7875) & " tr" & ChrW(7889) & "ng.", vbCritical
        Me.txtUser.SetFocus
        Exit Sub
    End If
End Sub

Private Sub lsbUsers_Change()
    Dim user As String, pass As String, tenDV As String
    user = Me.lsbUsers.list(Me.lsbUsers.ListIndex)
    pass = Me.lsbUsers.list(Me.lsbUsers.ListIndex, 1)
    tenDV = Me.lsbUsers.list(Me.lsbUsers.ListIndex, 2)
    Me.txtUser = user: Me.txtPass = pass: Me.txtTenDV = tenDV: Me.lblTenDV.Caption = tenDV
End Sub

Private Sub lsbUsers_Exit(ByVal Cancel As MSForms.ReturnBoolean)
    Me.lsbUsers.Visible = False
End Sub

Private Sub txtPass_Exit(ByVal Cancel As MSForms.ReturnBoolean)
    Me.lsbUsers.Visible = False
    If layCaptcha Then
        blnCaptcha = True
    Else
        blnCaptcha = False
    End If
    Me.cmdDangNhap.SetFocus
End Sub

Private Sub txtUser_AfterUpdate()
    On Error Resume Next    'Vuot loi could not set property visible
    Me.lsbUsers.Visible = False
End Sub

Private Sub txtUser_Change()
    Me.lsbUsers.Visible = True
End Sub

Private Sub UserForm_Initialize()
    Me.lblThanhCong.Visible = False
    Me.lblThatBai.Visible = False
    'Me.wbCatcha.Visible = False
    Me.cmdHienMK.Visible = True
    Me.cmdDauMK.Visible = False
    layUserPass
    createXmlHttpObj
End Sub

Private Sub txtPass_AfterUpdate()
    If layCaptcha Then
        blnCaptcha = True
    Else
        blnCaptcha = False
    End If
End Sub

Private Sub cmdDangNhap_Click()
    
    If blnCaptcha = False Then Exit Sub
    
    url = "https://hoadondientu.gdt.gov.vn:30000/security-taxpayer/authenticate"
    Call httpOption(url)
    
    Dim formData As String
    formData = "{""username"":""" & Me.txtUser & """,""password"":""" & Me.txtPass & """,""cvalue"":""" & Me.txtNhapCaptcha & """,""ckey"":""" & cKey & """}"
    createXmlHttpObj
    res = httpPost(url, formData)
    
    Set js = CreateObject("Scripting.Dictionary")
    Set js = JsonConverter.ParseJSON(res)
    
    If InStr(1, res, "message") > 0 Then
        If InStr(1, res, "captcha") Then
            MsgBoxUni js("message") & vbCrLf & "Vui l" & ChrW(242) & "ng nh" & ChrW(7853) & "p l" & ChrW(7841) & "i.", vbCritical, "Thông báo"
        Else
            MsgBoxUni js("message")
        End If
        
        Me.txtNhapCaptcha = ""
        Call layCaptcha
        
        Me.lblThanhCong.Visible = False
        Me.lblThatBai.Visible = True
        Exit Sub
    Else
        cToken = js("token")
        bearer = cToken
        Me.txtTenDV = layTenDV
        
        Me.lblThanhCong.Visible = True
        Me.lblThatBai.Visible = False
        Call saveUserPass
        Application.OnTime Time + TimeValue("00:00:01"), "closeForm"
    End If
    
End Sub

Function layCaptcha() As Boolean
    layCaptcha = True
    'Kiem tra ket noi internet
    If GetInternetConnectedState = False Then
        MsgBoxUni "Kh" & ChrW(244) & "ng c" & ChrW(243) & " k" & ChrW(7871) & "t n" & ChrW(7889) & "i internet.", vbCritical, "No internet"
        layCaptcha = False
        Exit Function
    End If
    
    Call createXmlHttpObj
    Dim cContent As String, sMsg As String
    url = "https://hoadondientu.gdt.gov.vn:30000/captcha"
    If httpGet(url, "", res) Then
        Set js = JsonConverter.ParseJSON(res)
        cKey = js("key")
        cContent = js("content")
        
        'Luu noi dung vao file .txt
        SaveStringToTextFile cContent
        
        'Me.wbCatcha.Visible = True
        'Me.wbCatcha.Navigate Environ$("USERPROFILE") & "\Documents\" & "myCaptcha.svg"
        
        DoEvents
        Me.txtNhapCaptcha = detectSVGCaptcha(res)
        
    Else
        sMsg = "C" & ChrW(243) & " l" & ChrW(7895) & "i k" & ChrW(7871) & "t n" & ChrW(7889) & "i v" & ChrW(224) & " l" & ChrW(7845) & "y d" & ChrW(7919) & " li" & ChrW(7879) & "u."
        sMsg = sMsg & vbCrLf & "Vui l" & ChrW(242) & "ng kh" & ChrW(7903) & "i " & ChrW(273) & ChrW(7897) & "ng l" & ChrW(7841) & "i " & ChrW(7913) & "ng d" & ChrW(7909) & "ng."
        MsgBoxUni sMsg, vbCritical
        layCaptcha = False
    End If
    
End Function

Sub SaveStringToTextFile(textData As String)
    'Param: textData - chuoi ky tu luu vao file text
    
    Dim filePath As String
    Dim fileNum As Integer
    
    'Me.wbCatcha.navigate ""
    
    filePath = Environ$("USERPROFILE") & "\Documents\" & "myCaptcha.txt"
    If Dir(Environ$("USERPROFILE") & "\Documents\" & "myCaptcha.svg") <> "" Then
        On Error Resume Next    'permission denied
        Kill Environ$("USERPROFILE") & "\Documents\" & "myCaptcha.svg"
    End If
    
    fileNum = FreeFile
    Open filePath For Output As fileNum
    Print #fileNum, textData
    Close fileNum
    'Doi duoi file .txt -> .svg
    Name filePath As Replace(filePath, ".txt", ".svg")
    
    'Debug.Print "Da luu va doi ten file thanh cong!"
End Sub

Sub layUserPass()
    arrUsers = Sheets("LinkTraCuu").Range("Q2:S" & Sheets("LinkTraCuu").Cells(Rows.count, "Q").End(xlUp).row).Value
    Me.lsbUsers.list = arrUsers
    Me.lsbUsers.Width = Me.txtUser.Width
    Me.lsbUsers.Height = 100
    Me.lsbUsers.Left = Me.txtUser.Left
    Me.lsbUsers.Top = Me.txtUser.Top + Me.txtUser.Height
End Sub

Sub saveUserPass()
    Dim X As Long, lr As Long
    For X = 1 To UBound(arrUsers, 1)
        If Me.txtUser = arrUsers(X, 1) Then
            Exit Sub
        End If
    Next
    'Luu user/pass moi
    With Sheets("LinkTraCuu")
        lr = .Cells(Rows.count, "Q").End(xlUp).row
        .Range("Q" & lr + 1).Value = Me.txtUser
        .Range("R" & lr + 1).Value = Me.txtPass
        .Range("S" & lr + 1).Value = Me.txtTenDV
        ThisWorkbook.Save
    End With

End Sub

Function layTenDV() As String
    url = "https://hoadondientu.gdt.gov.vn:30000/security-taxpayer/profile"
    If httpGet(url, bearer, res) Then
        Set js = JsonConverter.ParseJSON(res)
        layTenDV = js("name")
    Else
        layTenDV = ""
    End If
End Function
