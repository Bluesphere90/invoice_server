VERSION 5.00
Begin {C62A69F0-16DC-11CE-9E98-00AA00574A4F} frmTaiHoaDon 
   Caption         =   "+++"
   ClientHeight    =   9225.001
   ClientLeft      =   120
   ClientTop       =   470
   ClientWidth     =   15930
   OleObjectBlob   =   "frmTaiHoaDon.frx":0000
   StartUpPosition =   1  'CenterOwner
End
Attribute VB_Name = "frmTaiHoaDon"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Dim url As String, url_sco As String, url2 As String, url_ct As String, res As String, errMsg As String
Dim sort As String, size As Long, search As String, search_ex As String, tthai As String, ttxly As String
Dim arrDate(), arrHDChiTiet(), k As Long, i As Long, blnNgay As Boolean, errDate As Boolean
Dim js As Object, jsErr As Object

Private Sub chkXmlZip_Click()
    Me.txtXMLFolderPath.Enabled = Me.chkXmlZip
    Me.cmdChonFolder.Enabled = Me.chkXmlZip
    Me.cmdChiTietXML.Enabled = Me.chkXmlZip
    If Me.chkXmlZip = True Then
        MsgBoxUni "B" & ChrW(7841) & "n ph" & ChrW(7843) & "i ch" & ChrW(7885) & "n " & ChrW(273) & ChrW(432) & ChrW(7901) & "ng d" & ChrW(7851) & _
                "n th" & ChrW(432) & " m" & ChrW(7909) & "c " & ChrW(273) & ChrW(7875) & " l" & ChrW(432) & "u file zip ho" & ChrW(7863) & "c d" & ChrW(249) & _
                "ng " & ChrW(273) & ChrW(432) & ChrW(7903) & "ng d" & ChrW(7851) & "n m" & ChrW(7863) & "c " & ChrW(273) & ChrW(7883) & "nh.", vbInformation, "Thông báo"
    Me.txtXMLFolderPath.SetFocus
    End If
End Sub

Private Sub cmdChiTietXML_Click()
    frmTrichXuatXML.Show
End Sub

Private Sub cmdChonFolder_Click()
    With Application.FileDialog(4) ' msoFileDialogFolderPicker
        .Title = "Chon thu muc de luu file Zip XML"
        .AllowMultiSelect = False
        If .Show <> -1 Then Exit Sub 'Check if user clicked cancel button
        Me.txtXMLFolderPath = .SelectedItems(1) & "\"
    End With
End Sub

Private Sub cmdDangXuat_Click()
    Unload Me
    frmDangNhap.Show
End Sub

Private Sub txtTuNgay_AfterUpdate()
    Dim blnErr As Boolean
    Me.txtTuNgay.Value = Format(correctDate(Me.txtTuNgay.Value, blnErr), "dd/mm/yyyy")
    If blnErr = True Then
        Me.lblSaiNgay.Visible = True
    Else
        Me.lblSaiNgay.Visible = False
    End If
End Sub

Private Sub txtTuNgay_KeyPress(ByVal KeyAscii As MSForms.ReturnInteger)
    If KeyAscii < 47 Or KeyAscii > 57 Then KeyAscii = 0
End Sub

Private Sub txtDenNgay_KeyPress(ByVal KeyAscii As MSForms.ReturnInteger)
    If KeyAscii < 47 Or KeyAscii > 57 Then KeyAscii = 0
End Sub

Private Sub txtDenNgay_AfterUpdate()
    Dim blnErr As Boolean
    Me.txtDenNgay.Value = Format(correctDate(Me.txtDenNgay.Value, blnErr), "dd/mm/yyyy")
    If blnErr = True Then
        Me.lblSaiNgay.Visible = True
    Else
        Me.lblSaiNgay.Visible = False
    End If
    If CDate(Me.txtDenNgay) < CDate(Me.txtTuNgay) Then
        MsgBoxUni "Sai ng" & ChrW(224) & "y. [Ng" & ChrW(224) & "y b" & ChrW(7855) & "t " & ChrW(273) & ChrW(7847) & "u] > [Ng" & ChrW(224) & "y k" & ChrW(7871) & "t th" & ChrW(250) & "c].", vbCritical
        errDate = True
        Exit Sub
    Else
        errDate = False
        Call lietKeThoiGian
    End If
End Sub

Function correctDate(ByRef textDate As String, ByRef err As Boolean) As Date
    Dim ngay As Long, thang As Long, nam As Long
    Dim dtNgayNhap As Date, dtNgayCuoiThang As Date
    
    If Len(textDate) < 10 Or Len(textDate) > 10 Then
        correctDate = Date
        err = True
        Exit Function
    ElseIf Mid(textDate, 3, 1) <> "/" Or Mid(textDate, 6, 1) <> "/" Then
        correctDate = Date
        err = True
        Exit Function
    End If
    
    ngay = CLng(Left(textDate, 2))
    thang = CLng(Mid(textDate, 4, 2))
    nam = CLng(Right(textDate, 4))
    
    If thang > 12 Then thang = 12
    
    dtNgayNhap = DateSerial(nam, thang, ngay)
    dtNgayCuoiThang = DateSerial(nam, thang + 1, 0)
    If dtNgayNhap > dtNgayCuoiThang Then dtNgayNhap = dtNgayCuoiThang
    
    correctDate = CStr(dtNgayNhap)
    
End Function

Private Sub UserForm_Initialize()
    Call optMua_Change
    Me.cboKQKT.ListIndex = 0
    Me.cboTTHD.ListIndex = 0
    Me.lblStatus.Visible = False
    Me.lblSaiNgay.Visible = False
    Me.txtXMLFolderPath = Environ("USERPROFILE") & "\Documents\"
    Me.txtXMLFolderPath.Enabled = False
    Me.cmdChonFolder.Enabled = False
    Me.chkTH.Value = True
    Me.chkCT.Value = True
    Me.lblBanRa.Visible = False
    Me.lblMuaVao.Visible = True
End Sub

Public Sub optMua_Change()
    Dim arrtthai(), arrttxly()
    If Me.optMua = True Then
        arrtthai = Sheets("LinkTraCuu").Range("H2:I8").Value
        Me.cboTTHD.list = arrtthai
        Me.cboTTHD.ListIndex = 0
        arrttxly = Sheets("LinkTraCuu").Range("K2:L5").Value
        Me.cboKQKT.list = arrttxly
        Me.cboKQKT.ListIndex = 0
    Else
        arrtthai = Sheets("LinkTraCuu").Range("H2:I8").Value
        Me.cboTTHD.list = arrtthai
        Me.cboTTHD.ListIndex = 0
        arrttxly = Sheets("LinkTraCuu").Range("N2:O11").Value
        Me.cboKQKT.list = arrttxly
        Me.cboKQKT.ListIndex = 0
    End If
    Me.lblMuaVao.Visible = Me.optMua.Value
    Me.lblBanRa.Visible = Not Me.optMua.Value
End Sub

Private Sub cmdTaiHoaDon_Click()
    If errDate Then
        MsgBoxUni "Ki" & ChrW(7875) & "m tra l" & ChrW(7841) & "i ng" & ChrW(224) & "y t" & ChrW(236) & "m ki" & ChrW(7871) & "m.", vbCritical, "Thông báo"
        Exit Sub
    End If
    
    Me.lblStatus.Visible = True
    
    If Len(Trim(Me.txtTuNgay)) = 0 Or Len(Trim(Me.txtDenNgay)) = 0 Then Exit Sub
    If Len(Trim(Me.cboTTHD)) = 0 Or Len(Trim(Me.cboKQKT)) = 0 Then Exit Sub
    
    Dim sMsg As String, ret As Long
    Dim lrTongMua As Long, lrTongBan As Long, lrChiTietMua As Long, lrChiTietBan As Long
    
    'Lay dong cuoi tung Sheet de Xóa
    lrTongMua = Sheets("TongHopHD_Mua").Cells(Sheets("TongHopHD_mua").Rows.count, "C").End(xlUp).row
    lrTongBan = Sheets("TongHopHD_Ban").Cells(Sheets("TongHopHD_Ban").Rows.count, "C").End(xlUp).row
    lrChiTietMua = Sheets("ChiTietHD_Mua").Cells(Sheets("ChiTietHD_Mua").Rows.count, "C").End(xlUp).row
    lrChiTietBan = Sheets("ChiTietHD_Ban").Cells(Sheets("ChiTietHD_Ban").Rows.count, "C").End(xlUp).row
    
    sMsg = "B" & ChrW(7841) & "n c" & ChrW(243) & " mu" & ChrW(7889) & "n X" & ChrW(243) & "a d" & ChrW(7919) & " li" & ChrW(7879) & "u c" & ChrW(361) & " kh" & ChrW(244) & "ng?"
    sMsg = sMsg & vbCrLf & "Ch" & ChrW(7885) & "n [Yes] " & ChrW(273) & ChrW(7875) & " X" & ChrW(243) & "a ho" & ChrW(7863) & "c [No] " & ChrW(273) & ChrW(7875) & " ghi k" & ChrW(7871) & " ti" & ChrW(7871) & "p."
    ret = MsgBoxUni(sMsg, vbYesNo + vbInformation, "Thông báo")
    
    'Timer----------
    Dim bd As Single, kt As Single
    bd = Timer
    '----------------
    
    If ret = vbYes Then
        If Me.optMua = True Then
            If lrTongMua < 3 Then lrTongMua = 3
            If lrChiTietMua < 3 Then lrChiTietMua = 3
            Sheets("TongHopHD_Mua").Range("A3:BZ" & lrTongMua).ClearContents
            Sheets("ChiTietHD_Mua").Range("A3:BZ" & lrChiTietMua).ClearContents
        Else
            If lrTongBan < 3 Then lrTongBan = 3
            If lrChiTietBan < 3 Then lrChiTietBan = 3
            Sheets("TongHopHD_Ban").Range("A3:BZ" & lrTongBan).ClearContents
            Sheets("ChiTietHD_Ban").Range("A3:BZ" & lrChiTietBan).ClearContents
        End If
        Call taiHoaDon_Total
        
    Else
        If Me.optMua = True Then
            Call taiHoaDon_Total(lrTongMua + 1, lrChiTietMua + 1)
        Else
            Call taiHoaDon_Total(lrTongBan + 1, lrChiTietBan + 1)
        End If
    End If
    
    '----------------------
    kt = Timer - bd
    Dim s As String
    s = " Thoi gian xu ly: " & Format(kt / 86400, "hh:mm:ss")
    '----------------------
    Me.lblStatus.Caption = s
    Me.lblStatus.Visible = True
    
    
    'MsgBox "Xong."
    'Unload Me

    
End Sub

Sub taiHoaDon_Total(Optional rowTotalstart As Long = 3, Optional rowDetailStart As Long = 3)
    Static row As Long, row_ct As Long, stt As Long, n As Long
    Dim k As Long, j As Long, i As Long, loaiHD As Long, ret As Boolean
    Dim item As Object
    Dim arrHDChiTiet_tmp(1000, 5)
    
    'Tao bang tra cac dieu kien tim kiem
    Call LinkTraCuu
    Call tenCotTraCuu
    arrTrangThai = Sheets("LinkTraCuu").Range("I2:I8").Value
    arrKQKTHoaDon = Sheets("LinkTraCuu").Range("O2:O11").Value
    '------------------------------------
    
    stt = 1
    'row = 3: row_ct = 3
    row = rowTotalstart: row_ct = rowDetailStart
    
    'Tham so cho request
    sort = "tdlap:asc,khmshdon:asc,shdon:asc"
    size = 50
    ttxly = Me.cboKQKT
    tthai = Me.cboTTHD
    bearer = cToken
    url2 = ""
    If Me.optMua = True Then
        url = "https://hoadondientu.gdt.gov.vn:30000/query/invoices/purchase?sort="
        url_sco = "https://hoadondientu.gdt.gov.vn:30000/sco-query/invoices/purchase?sort="
        loaiHD = 1 'mua
    Else
        url = "https://hoadondientu.gdt.gov.vn:30000/query/invoices/sold?sort="
        url_sco = "https://hoadondientu.gdt.gov.vn:30000/sco-query/invoices/sold?sort="
        loaiHD = 2 'ban
    End If
    n = 0   'n: so luong HD
    'Duyet tung khoan thoi gian de trich xuat hoa don
    For k = 1 To UBound(arrDate)
        If tthai = "All" Then 'Tat ca
            'Hd mua va ban giong nhau
            If ttxly = "All" Then  'Tat ca
                search = "tdlap=ge=" & Format(arrDate(k, 1), "dd/mm/yyyy") & "T00:00:00;tdlap=le=" & Format(arrDate(k, 2), "dd/mm/yyyy") & "T23:59:59"
            Else
                search = "tdlap=ge=" & Format(arrDate(k, 1), "dd/mm/yyyy") & "T00:00:00;tdlap=le=" & Format(arrDate(k, 2), "dd/mm/yyyy") & "T23:59:59;ttxly==" & ttxly
            End If
        Else
            If ttxly = "All" Then
                search = "tdlap=ge=" & Format(arrDate(k, 1), "dd/mm/yyyy") & "T00:00:00;tdlap=le=" & Format(arrDate(k, 2), "dd/mm/yyyy") & "T23:59:59;tthai==" & tthai
            Else
                search = "tdlap=ge=" & Format(arrDate(k, 1), "dd/mm/yyyy") & "T00:00:00;tdlap=le=" & Format(arrDate(k, 2), "dd/mm/yyyy") & "T23:59:59;tthai==" & tthai & ";ttxly==" & ttxly
            End If
        End If
        url2 = url & sort & "&size=" & size & "&search=" & search
nextPage:
        If httpGet(url2, bearer, res) = False Or Len(res) = 0 Then
            'MsgBoxUni "L" & ChrW(7895) & "i ph" & ChrW(225) & "t sinh t" & ChrW(7915) & " ng" & ChrW(224) & "y " & arrDate(k, 1) & " - " & arrDate(k, 2), vbExclamation, "Thông báo"
            errMsg = errMsg & "Loi tai hoa don tong hop ngay: " & arrDate(k, 1) & " - " & arrDate(k, 2) & vbCrLf
            If getStatus = 429 Or getStatus = 500 Then GoTo errLog
            GoTo nextDatePeriod 'Khi co loi phat sinh --> tiep tuc lay du lieu khoang thoi gian ke tiep
        End If
        
        Set js = JsonConverter.ParseJSON(res)
        If InStr(1, res, "error") > 0 Then
            'MsgBoxUni js("error") & vbCrLf & vbCrLf & "Vui long khoi dong lai ung dung"
            errMsg = errMsg & "Loi ket noi: " & js("error") & vbCrLf
            GoTo nextDatePeriod
        End If
        
        ghiExcel_TongHop res, row, loaiHD, stt
        
        'Lay tham so HD chi tiet
        For Each item In js("datas")
            arrHDChiTiet_tmp(n, 0) = item("nbmst") & ""
            arrHDChiTiet_tmp(n, 1) = item("khhdon")
            arrHDChiTiet_tmp(n, 2) = item("shdon")
            arrHDChiTiet_tmp(n, 3) = item("khmshdon")
            arrHDChiTiet_tmp(n, 4) = 1  'query
            arrHDChiTiet_tmp(n, 5) = ISODATE(item("tdlap"))
            n = n + 1
        Next
        
        'Tai nhieu trang
        If IsNull(js("state")) = False Then
            url2 = url & sort & "&size=" & size & "&state=" & js("state") & "&search=" & search
            GoTo nextPage 'Quay lai lay du lieu tiep trang 2 (>50)...
        End If
        
           '******************************************
        '// Chay sco query de lay hd tu may tinh tien
        url2 = url_sco & sort & "&size=" & size & "&search=" & search
nextPage_sco:
        If httpGet(url2, bearer, res) = False Or Len(res) = 0 Then
            'MsgBoxUni "L" & ChrW(7895) & "i ph" & ChrW(225) & "t sinh t" & ChrW(7915) & " ng" & ChrW(224) & "y " & arrDate(k, 1) & " - " & arrDate(k, 2), vbExclamation, "Thông báo"
            errMsg = errMsg & "Loi tai hoa don tong hop ngay: " & arrDate(k, 1) & " - " & arrDate(k, 2) & vbCrLf
            If getStatus = 429 Or getStatus = 500 Then GoTo errLog
            GoTo nextDatePeriod
        End If
        
        Set js = JsonConverter.ParseJSON(res)
        If InStr(1, res, "error") > 0 Then
            'MsgBoxUni js("error") & vbCrLf & vbCrLf & "Vui long khoi dong lai ung dung"
            errMsg = errMsg & "Loi ket noi: " & js("error") & vbCrLf
            GoTo nextDatePeriod
        End If
        
        ghiExcel_TongHop res, row, loaiHD, stt
        
        'Lay tham so HD chi tiet
        For Each item In js("datas")
            arrHDChiTiet_tmp(n, 0) = item("nbmst") & ""
            arrHDChiTiet_tmp(n, 1) = item("khhdon")
            arrHDChiTiet_tmp(n, 2) = item("shdon")
            arrHDChiTiet_tmp(n, 3) = item("khmshdon")
            arrHDChiTiet_tmp(n, 4) = 2  'sco-query
            arrHDChiTiet_tmp(n, 5) = ISODATE(item("tdlap"))
            n = n + 1
        Next
        
        'Tai nhieu trang
        If IsNull(js("state")) = False Then
            url2 = url_sco & sort & "&size=" & size & "&state=" & js("state") & "&search=" & search
            GoTo nextPage_sco
        End If
        
        '++++++++++++++++++++++++++++++++
        
nextDatePeriod: 'arrDate ke tiep
    Next k
    
    '/Resize mang arrHDChiTiet()
    ReDim arrHDChiTiet(n, 5)
    For k = 0 To n - 1
        arrHDChiTiet(k, 0) = arrHDChiTiet_tmp(k, 0)
        arrHDChiTiet(k, 1) = arrHDChiTiet_tmp(k, 1)
        arrHDChiTiet(k, 2) = arrHDChiTiet_tmp(k, 2)
        arrHDChiTiet(k, 3) = arrHDChiTiet_tmp(k, 3)
        arrHDChiTiet(k, 4) = arrHDChiTiet_tmp(k, 4)
        arrHDChiTiet(k, 5) = arrHDChiTiet_tmp(k, 5)
    Next
    Erase arrHDChiTiet_tmp
    
    
    If Me.chkCT = False Then GoTo taiXML
    
    '------------------------------------------
    'Ghi chi tiet hoa don
    For j = 0 To n - 1 'UBound(arrHDChiTiet) - 1
        If arrHDChiTiet(j, 4) = 1 Then
            url_ct = "https://hoadondientu.gdt.gov.vn:30000/query/invoices/detail?"
        Else
            url_ct = "https://hoadondientu.gdt.gov.vn:30000/sco-query/invoices/detail?"
        End If
        url_ct = url_ct & "nbmst=" & arrHDChiTiet(j, 0) & "&khhdon=" & arrHDChiTiet(j, 1) & "&shdon=" & arrHDChiTiet(j, 2) & "&khmshdon=" & arrHDChiTiet(j, 3)
        If httpGet(url_ct, bearer, res) = False Or Len(res) = 0 Then
            MsgBoxUni "L" & ChrW(7895) & "i ph" & ChrW(225) & "t sinh t" & ChrW(7915) & " ng" & ChrW(224) & "y " & arrDate(k, 1) & " - " & arrDate(k, 2), vbExclamation, "Thông báo"
            GoTo nextInvoice
        End If
        Set js = JsonConverter.ParseJSON(res)
        If InStr(1, res, "error") > 0 Then
            MsgBoxUni js("error") & vbCrLf & vbCrLf & "Vui long khoi dong lai ung dung"
            GoTo nextInvoice
        End If
        
        If Me.optMua = True Then
            ghiExcel_ChiTiet res, row_ct, "mua"
        Else
            ghiExcel_ChiTiet res, row_ct, "ban"
        End If
        
        Sleep Me.txtSleep
nextInvoice:                                    'arrHDChiTiet
    Next
    
taiXML:
    If Me.chkXmlZip = True Then
        Me.lblStatus.Caption = "B" & ChrW(7855) & "t " & ChrW(273) & ChrW(7847) & "u t" & ChrW(7843) & "i file XML/HTML v" & ChrW(224) & " gi" & ChrW(7843) & "i n" & ChrW(233) & "n..."
        
        DoEvents
        taiXML_zip n
    End If

errLog:
    If errMsg <> "" Then
        ghiLog errMsg
    End If
    
    MsgBox "Xong."

cleanup:
    Erase arrDate
    Erase arrHDChiTiet
    'Unload Me
End Sub

Sub lietKeThoiGian()
    Dim startYear As Long, startMonth As Long, startDay As Long, endYear As Long, endMonth As Long, endDay As Long
    Dim dtNgayCuoiThang As Date, dtNgayDauThang As Date, dtDenNgay As Date
    Dim tempArr()   'De redim arrDate
    
    startYear = Right(Me.txtTuNgay, 4)
    startMonth = Mid(Me.txtTuNgay, 4, 2)
    startDay = Left(Me.txtTuNgay, 2)
    
    endYear = Right(Me.txtDenNgay, 4)
    endMonth = Mid(Me.txtDenNgay, 4, 2)
    endDay = Left(Me.txtDenNgay, 2)
    
    dtNgayDauThang = DateSerial(startYear, startMonth, startDay)
    dtNgayCuoiThang = DateSerial(startYear, startMonth + 1, 0)
    dtDenNgay = DateSerial(endYear, endMonth, endDay)
    i = 1
    ReDim arrDate(60, 2)    '5 nam
    Do While dtNgayCuoiThang <= dtDenNgay
        
        arrDate(i, 1) = dtNgayDauThang: arrDate(i, 2) = dtNgayCuoiThang
        startMonth = startMonth + 1
        'Qua nam ke tiep
        If startMonth > 12 Then
            startMonth = 1
            startYear = startYear + 1
        End If
        dtNgayDauThang = DateSerial(startYear, startMonth, 1)
        dtNgayCuoiThang = DateSerial(startYear, startMonth + 1, 0)
        i = i + 1
    Loop
    If dtNgayDauThang <= dtDenNgay Then
        arrDate(i, 1) = dtNgayDauThang: arrDate(i, 2) = dtDenNgay
    Else
        i = i - 1
    End If
    
    ReDim tempArr(1 To i, 1 To 2)
    Dim k As Long
    For k = 1 To i
        tempArr(k, 1) = arrDate(k, 1)
        tempArr(k, 2) = arrDate(k, 2)
    Next
    
    arrDate = tempArr
    
    'For k = 1 To UBound(arrDate)
        'Debug.Print arrDate(k, 1), arrDate(k, 2)
    'Next
End Sub

Sub ghiLog(errorMessage As String, Optional txtFile As Boolean = False)
'    Select Case txtFile
'        Case True
'            Dim filePath As String, fileNum As Integer
'            filePath = Me.txtFolderPath & "errLog_" & Format(Now, "yyyymmdd_hhnnss") & ".txt"
'            fileNum = FreeFile
'            Open filePath For Output As fileNum
'            Print #fileNum, errorMessage
'            Close fileNum
'            'Debug.Print "Da luu log file thanh cong!"
'        Case False
'            CurrentDb.Execute "Insert Into tblErrLog (NgayPS, NoiDung) Values (#" & Now & "#,'" & errorMessage & "')", dbFailOnError
'    End Select
End Sub

Sub taiXML_zip(soHD As Long)
    On Error GoTo EH
    Dim nbmst As String, khhdon As String, shdon As String, khmshdon As String
    Dim urlXml As String, payload As String, filePath As Variant, m As Long
    
    '/ Tao folder luu file giai nen
    Dim strDate As String
    strDate = Format(Now, "_yyyymmdd_hhmmss")
    oSaveUnzipFolder = Me.txtXMLFolderPath & "FileGiaiNen" & strDate '& "\"
    MkDir oSaveUnzipFolder
    MsgBox oSaveUnzipFolder
    '-----------------------------------/
    
    Application.Cursor = xlWait
    
    For m = 0 To soHD - 1
        If arrHDChiTiet(m, 4) = 1 Then  'query
            urlXml = "https://hoadondientu.gdt.gov.vn:30000/query/invoices/export-xml?"
        Else    'sco-query
            urlXml = "https://hoadondientu.gdt.gov.vn:30000/sco-query/invoices/export-xml?"
        End If
        nbmst = arrHDChiTiet(m, 0)
        khhdon = arrHDChiTiet(m, 1)
        shdon = arrHDChiTiet(m, 2)
        khmshdon = arrHDChiTiet(m, 3)
        payload = "nbmst=" & nbmst & "&khhdon=" & khhdon & "&shdon=" & shdon & "&khmshdon=" & khmshdon
        urlXml = urlXml & payload
        'Call httpOption(urlXml)
        
        Dim http As Object, stream As Object
        Set stream = CreateObject("ADODB.Stream")
        Set http = CreateObject("MSXML2.XMLHTTP")
        With http
            .Open "GET", urlXml, False
            .setRequestHeader "User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            .setRequestHeader "Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
            .setRequestHeader "Accept-Encoding", "gzip"
            .setRequestHeader "Content-type", "application/zip"
            .setRequestHeader "Authorization", "Bearer " & bearer & ""
            .send
        End With
        
        Select Case http.Status
            Case 200
                stream.Type = 1 ' Binary
                stream.Open
                stream.Write http.responseBody ' Write the binary response to the stream
                filePath = Me.txtXMLFolderPath & khhdon & "_" & shdon & ".zip"
                stream.SaveToFile filePath, 2 ' Overwrite
                stream.Close
                DoEvents
                
                '//Unzip file vua tai, chi lay file xml/html
                Call Unzip(filePath, oSaveUnzipFolder)
                
            Case 500
                Debug.Print "Loi download file hoa don (zip): " & http.Status & "__" & khhdon & "_" & shdon & " res: " & http.responseText
                errMsg = errMsg & "- Khong ton tai ho so goc cua hoa don: " & khhdon & "_" & shdon & vbCrLf
                GoTo nextInvoice
            Case 429
                MsgBoxUni "L" & ChrW(7895) & "i 429 - G" & ChrW(7917) & "i qu" & ChrW(225) & " nhi" & ChrW(7873) & "u y" & ChrW(234) & "u c" & ChrW(7847) & "u t" & ChrW(7899) & "i m" & ChrW(225) & "y ch" & ChrW(7911) & " Web.", vbExclamation, "Tai XML Error 429"
                errMsg = errMsg & "- Qua nhieu yeu cau toi may chu web: " & khhdon & "_" & shdon & vbCrLf
                GoTo EH_Exit
            Case Else
                errMsg = errMsg & "- Loi ket noi: " & khhdon & "_" & shdon & vbCrLf
                GoTo nextInvoice
        End Select
        
nextInvoice:
        Sleep Me.txtSleep
    Next m
    
    
EH_Exit:
    If errMsg <> "" Then
        ghiLog errMsg
    End If
    Set stream = Nothing
    Set http = Nothing
     Application.Cursor = xlDefault
    Exit Sub
EH:
    Application.Cursor = xlDefault
    MsgBoxUni "C" & ChrW(243) & " l" & ChrW(7895) & "i ph" & ChrW(225) & "t sinh trong qu" & ChrW(225) & " tr" & ChrW(236) & "nh t" & ChrW(7843) & "i h" & ChrW(243) & "a " & ChrW(273) & ChrW(417) & "n.", vbCritical, "L" & ChrW(7895) & "i t" & ChrW(7843) & "i h" & ChrW(243) & "a " & ChrW(273) & ChrW(417) & "n"
    MsgBox "Ma loi: " & err.Number & vbCrLf & "Noi dung: " & err.Description, vbCritical, "L" & ChrW(7895) & "i t" & ChrW(7843) & "i h" & ChrW(243) & "a " & ChrW(273) & ChrW(417) & "n"
    Resume EH_Exit
    
End Sub
