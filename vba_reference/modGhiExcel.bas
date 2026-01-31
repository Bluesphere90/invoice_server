Attribute VB_Name = "modGhiExcel"
Option Explicit

Sub dangnhap()
    frmDangNhap.Show
End Sub

Sub ghiExcel_TongHop(ByVal jsonText As String, row As Long, ByVal loaiHD As Long, sSTT As Long)
    
    Dim jsTH As Object, item As Object, itm As Object, subItms As Object, subItms2 As Object, l As Long
    Dim ws As Worksheet
    Dim arrCol, arrColName
    
    On Error Resume Next
    
    arrCol = Array(2, 3, 4, 5, 6, 7, 8, 9, 10, 11, _
        12, 13, 14, 15, 16, 17, 42, 43, 44, _
        47, 48, 49, 50, 51, 54)
    arrColName = Array("tlhdon", "khmshdon", "khhdon", "shdon", "tdlap", "dvtte", "tgia", "nbten", "nbmst", "nbdchi", _
        "nky", "mhdon", "ncma", "nmten", "nmmst", "nmdchi", "tgtcthue", "tgtkcthue", "tgtthue", _
        "ttcktmai", "tgtkhac", "tgtttbso", "tgtttbchu", "gchu", "msttcgp")
    
    Select Case loaiHD
        Case 1
            Set ws = ThisWorkbook.Sheets("TongHopHD_Mua")
        Case 2
            Set ws = ThisWorkbook.Sheets("TongHopHD_Ban")
    End Select
    
    Set jsTH = JsonConverter.ParseJSON(jsonText)
    
    Dim dataArray As Object, i As Long, v As Variant
    Set dataArray = jsTH("datas")
    For l = 1 To jsTH("datas").count
        'On Error Resume Next    'Bo qua cac loi khi khong tim thay cac item trong json,item = null
        '/Cot STT
        ws.Cells(row, 1).Value = sSTT
        
        For i = 0 To UBound(arrCol)
            v = dataArray(l)(arrColName(i))
            If v = "" Or IsNull(v) Then GoTo next_col
            Select Case arrColName(i)
                Case "ncma", "nky", "ncnhat", "ntao", "ntnhan", "tdlap"
                    ws.Cells(row, arrCol(i)).Value = ISODATE(Format(v, "yyyy-mm-dd"))
                Case Else
                    ws.Cells(row, arrCol(i)).Value = v
            End Select
next_col:
        Next i
        
        '/Ghi cac truong dac biet
        If Not dataArray(l)("thttltsuat") Is Nothing Then
            Set subItms = dataArray(l)("thttltsuat")
            If subItms.count > 0 Then
                Dim c As Long
                For c = 0 To subItms.count - 1  'Có tat ca 6 cot tsuat: KKKCT, KCT, 0%, 5%, 8%, 10%
                    Set subItms2 = subItms(c + 1)
                    ws.Cells(row, 18 + (4 * c)).Value = subItms2("tsuat")
                    ws.Cells(row, 19 + (4 * c)).Value = subItms2("thtien")
                    ws.Cells(row, 20 + (4 * c)).Value = subItms2("tthue")
                    ws.Cells(row, 21 + (4 * c)).Value = subItms2("gttsuat")
                Next c
            End If
        End If
        
        If Not IsEmpty(dataArray(l)("thttlphi")) Then
            If Not dataArray(l)("thttlphi") Is Nothing Then
                Set subItms = dataArray(l)("thttlphi")
                If subItms.count > 0 Then
                    Set subItms2 = subItms(1)
                    ws.Cells(row, 45).Value = subItms2("tlphi")
                    ws.Cells(row, 46).Value = subItms2("tphi")
                End If
            End If
        End If
        
        ws.Cells(row, 52).Value = arrTrangThai(CInt(dataArray(l)("tthai")), 1)
        ws.Cells(row, 53).Value = arrKQKTHoaDon(CInt(dataArray(l)("ttxly")) + 2, 1)
        
        '//Lay link va ma tra cuu
        Dim msttcgp As String
        If dataArray(l)("msttcgp") <> "" Or Not IsNull(dataArray(l)("msttcgp")) Then
            msttcgp = dataArray(l)("msttcgp")
            '/Lay link tra cuu
            Select Case msttcgp
                Case "0100684378"   'VNPT
                    Dim MST As String, mccqt As String
                    MST = ws.Cells(row, 10).Value: mccqt = ws.Cells(l + ROWSTART, 13).Value
                    If mccqt <> "" Then
                        ws.Cells(row, 55).Value = "https://" & MST & "-tt78.vnpt-invoice.com.vn/?strFkey=" & mccqt
                    Else
                        ws.Cells(row, 55).Value = "Khong co link tra cuu"
                    End If
                Case "0105987432"
                            ws.Cells(row, 55).Value = "https://" & MST & "hd.easyinvoice.com.vn"
                Case "0101360697"   'BKAV
                    If Not IsNull(dataArray(l)("id")) Then
                        If mccqt <> "" Then
                            ws.Cells(row, 55).Value = "https://van.ehoadon.vn/Lookup?InvoiceGUID=" & dataArray(l)("id")
                        Else
                            ws.Cells(row, 55).Value = "Khong co ma CQT"
                        End If
                    End If
                Case Else
                    ws.Cells(row, 55).Value = dicLink.item(msttcgp)
            End Select
            '------------------------------------------------------------------/
            
            '/Lay ma tra cuu
            'Con truong hop cttkhac khong exists!
            If Not dataArray(l)("cttkhac") Is Nothing Then
                Set subItms = dataArray(l)("cttkhac")
                For Each itm In subItms
                    If dicTenCotTC.Exists(itm("ttruong")) Then
                        ws.Cells(row, 56).Value = itm("dlieu")
                        Exit For
                    End If
                Next
            End If
            
            If Not dataArray(l)("ttkhac") Is Nothing Then
                Set subItms = dataArray(l)("ttkhac")
                For Each itm In subItms
                    If dicTenCotTC.Exists(itm("ttruong")) Then
                        ws.Cells(row, 56).Value = itm("dlieu")
                        Exit For
                    End If
                Next
            End If
            '-------------------------------------/
            
        Else    'truong hop khong co msttcgp
            ws.Cells(row, 55).Value = "Khong co link tra cuu"
        End If
        
        'Tang so tt va so thu thu dong
        sSTT = sSTT + 1
        row = row + 1
        
next_invoice:
    Next l
    
End Sub

Sub ghiExcel_ChiTiet(jsonText As String, row_ct As Long, loaiHD As String)
    Dim jsCT As Object, subItms As Object, subItms2 As Object, item As Object, itm As Object, col As Long, c As Long, sumRow As Long, tongthueCT As Double
    Dim ws As Worksheet
    Dim arrCol, arrColName, arrCol_detail, arrColName_detail
    
    On Error Resume Next
    
    sumRow = row_ct
    tongthueCT = 0
    
    '/Dung chung cho tat ca cac dong hang hoa
    arrCol = Array(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 31)
    arrColName = Array("khhdon", "shdon", "tdlap", "dvtte", "tgia", "nbten", "nbmst", "nbdchi", "nky", "mhdon", "ncma", "nmten", "nmmst", "nmdchi", "msttcgp")
    
    '/Nhieu dong hang hoa
    arrCol_detail = Array(15, 16, 17, 18, 19, 20, 21, 22, 23, 24, _
        25, 26, 27, 28)
    arrColName_detail = Array("stt", "tchat", "mhhdvu", "ten", "dvtinh", "sluong", "dgia", "tlckhau", "stckhau", "ltsuat", _
        "tsuat", "thtien", "tthue", "thtcthue")
    
    'Ten worksheet ghi du lieu chi tiet
    Select Case loaiHD
        Case "mua"
            Set ws = ThisWorkbook.Sheets("ChiTietHD_Mua")
        Case "ban"
            Set ws = ThisWorkbook.Sheets("ChiTietHD_Ban")
    End Select
    
    Set jsCT = JsonConverter.ParseJSON(jsonText)
    
    '/Ghi thong tin chung
    For col = 0 To UBound(arrCol)
        If jsCT.Exists(arrColName(col)) Then
            If Not IsNull(jsCT(arrColName(col))) Then
                'Dinh dang du lieu dang Date
                Select Case arrColName(col)
                    Case "ncma", "nky", "ncnhat", "ntao", "ntnhan", "tdlap"
                        ws.Cells(row_ct, col + 1).Value = CStr(ISODATE(Format(jsCT(arrColName(col)), "yyyy-mm-dd")))
                    Case Else
                        ws.Cells(row_ct, col + 1).Value = jsCT(arrColName(col))
                End Select
            End If
        End If
    Next
    
    '/Lay link tra cuu
    Dim msttcgp As String
    ws.Cells(row_ct, 31).Value = jsCT("msttcgp")
    msttcgp = ws.Cells(row_ct, 31).Value
    If msttcgp <> "" Then   'Co MSTTCGP
        Dim MST As String, mccqt As String
        MST = ws.Cells(row_ct, 7).Value: mccqt = ws.Cells(row_ct, 10).Value
        Select Case msttcgp
            Case "0100684378"   'VNPT
                If mccqt <> "" Then
                    ws.Cells(row_ct, 32).Value = "https://" & MST & "-tt78.vnpt-invoice.com.vn/?strFkey=" & mccqt
                Else
                    ws.Cells(row_ct, 32).Value = "Không có MCCQT"
                End If
            Case "0101360697"   'BKAV
                ws.Cells(row_ct, 32).Value = "https://van.ehoadon.vn/Lookup?InvoiceGUID= [DLHDon Id]" '& .Offset(, 0).Value
            Case "0105987432"
                ws.Cells(row_ct, 32).Value = "https://" & MST & "hd.easyinvoice.com.vn"
            Case Else
                ws.Cells(row_ct, 32).Value = dicLink.item(msttcgp)
        End Select
        
        '/Lay ma tra cuu
        'Con truong hop cttkhac khong exists!
        If Not jsCT("cttkhac") Is Nothing Then
            Set subItms = jsCT("cttkhac")
            For Each itm In subItms
                If dicTenCotTC.Exists(itm("ttruong")) Then
                    ws.Cells(row_ct, 33).Value = itm("dlieu")
                    Exit For
                End If
            Next
        End If
        
        If Not jsCT("ttkhac") Is Nothing Then
            Set subItms = jsCT("ttkhac")
            For Each itm In subItms
                If dicTenCotTC.Exists(itm("ttruong")) Then
                    ws.Cells(row_ct, 33).Value = itm("dlieu")
                    Exit For
                End If
            Next
        End If
        '-------------------------------------/
        
    Else    'truong hop khong co msttcgp
        ws.Cells(row_ct, 32).Value = "Khong co link tra cuu"
    End If
    
    '/Ghi thong tin tung ma HHDVu
    For Each item In jsCT("hdhhdvu")
        For col = 0 To UBound(arrCol_detail)
            On Error Resume Next    'bo qua loi khong co ten cot trong json
            'Cac cot con lai
            If col = 10 Then
                Select Case item(arrColName_detail(col - 1))
                    Case "KKKNT"
                        ws.Cells(row_ct, col + 15).Value = "KKKNT"
                    Case "KCT"
                        ws.Cells(row_ct, col + 15).Value = "KCT"
                    Case Else
                        ws.Cells(row_ct, col + 15).Value = item(arrColName_detail(col))
                End Select
            Else
                ws.Cells(row_ct, col + 15).Value = item(arrColName_detail(col))
            End If
        Next
        
        Dim arrTThue As Variant, arrThTiencoVAT As Variant
        arrTThue = Split(Sheets("LinkTraCuu").Range("O14"), ",")
        arrThTiencoVAT = Split(Sheets("LinkTraCuu").Range("O15"), ",")
        
        If item.Exists("ttkhac") Then
            If Not item("ttkhac") Is Nothing Then
                Dim ttruong As String
                Set subItms = item("ttkhac")
                If subItms.count > 0 Then
                    For c = 1 To subItms.count  'Có tat ca 3 cot
                        Set subItms2 = subItms(c)
                        ttruong = subItms2("ttruong")
                        If isInArray(ttruong, arrTThue) Then
                            ws.Cells(row_ct, 27).Value = subItms2("dlieu")
                            tongthueCT = tongthueCT + Val(subItms2("dlieu"))
                        ElseIf isInArray(ttruong, arrThTiencoVAT) Then
                            ws.Cells(row_ct, 28).Value = subItms2("dlieu")
                        End If
                    Next
                End If
            End If
        End If
        
        If ws.Cells(row_ct, 27).Value = 0 Then   'Khong co gia tri cho cot tthueVAT
            ws.Cells(row_ct, 27).Value = Val(ws.Cells(row_ct, 25).Value) * ws.Cells(row_ct, 26).Value
            ws.Cells(row_ct, 28).Value = ws.Cells(row_ct, 26).Value + ws.Cells(row_ct, 27).Value
        End If
        If ws.Cells(row_ct, 28).Value = 0 Then  'Khong co gia tri cho cot THTiencoVAT
            ws.Cells(row_ct, 28).Value = ws.Cells(row_ct, 26).Value + ws.Cells(row_ct, 27).Value
        End If
        
        '/Dung cho hd khong nhan ma loai 2: chi tiet hhdv ("tthue"= #,##)
        If item.Exists("tthue") Then
            If Not IsNull(item("tthue")) Then
                tongthueCT = item("tthue")
            End If
        End If
        '------------------------------/
        
        row_ct = row_ct + 1
    Next
    
    '// So sanh tien thue chi tiet va tong hop
    If jsCT.Exists("tgtthue") Then
        If Not IsNull(jsCT("tgtthue")) Then
            ws.Cells(sumRow, 29).Value = jsCT("tgtthue")
        End If
    End If
    
    If tongthueCT <> jsCT("tgtthue") Then
        ws.Cells(sumRow, 30).Value = "Kiem tra lai tien thue: [" & Format(tongthueCT, "standard") & "] <> [" & Format(jsCT("tgtthue"), "standard") & "]"
        ws.Cells(sumRow, 30).Font.Color = vbRed
    Else
        ws.Cells(sumRow, 30).Value = "Tien thue ok"
        ws.Cells(sumRow, 30).Font.Color = vbBlue
    End If
    
    '---------------------------------------/
    
    '/Copy thong tin chung
    If row_ct > sumRow Then
        CopyThongTinChung_CT ws.name, sumRow, row_ct - 1
    End If
    
End Sub

Sub LinkTraCuu()
    Dim n As Long, lr As Long, arrLinks As Variant
    
    Set dicLink = CreateObject("Scripting.Dictionary")
    With Sheets("LinkTraCuu")
        lr = .Range("B" & .Rows.count).End(xlUp).row
    End With
    arrLinks = Sheets("LinkTraCuu").Range("B2:E" & lr).Value
    
    For n = 1 To UBound(arrLinks)
        'Debug.Print arrLinks(n, 1), arrLinks(n, 3), , arrLinks(n, 4)
        dicLink(arrLinks(n, 1)) = arrLinks(n, 3)
    Next n
    Erase arrLinks
End Sub

Sub tenCotTraCuu()
    Dim arrVals(), m As Long
    
    Set dicTenCotTC = CreateObject("Scripting.Dictionary")
    arrVals = Sheets("LinkTraCuu").Range("E2:E" & Sheets("LinkTraCuu").Cells(Rows.count, "B").End(xlUp).row).Value
    For m = 1 To UBound(arrVals)
        If Len(arrVals(m, 1)) > 0 Then
            On Error Resume Next
            dicTenCotTC.Add arrVals(m, 1), "ttruong"
        End If
    Next m
    Erase arrVals
'    For m = 0 To dicTenCotTC.Count - 1
'        Debug.Print dicTenCotTC.Keys()(m), dicTenCotTC.Items()(m)
'    Next m
'    dicTenCotTC.RemoveAll
End Sub

Sub CopyThongTinChung_CT(shtName As String, frow As Long, lrow As Long)
    Dim ws As Worksheet, sourceRange As Range, targetRange As Range
    
    Set ws = ThisWorkbook.Sheets(shtName)
    Set sourceRange = ws.Range("A" & frow & ":N" & frow)
    Set targetRange = ws.Range("A" & frow + 1 & ":N" & lrow)
    sourceRange.Copy Destination:=targetRange
    ' Clear the clipboard
    Application.CutCopyMode = False
    'MsgBox "Copy thanh cong", vbInformation
End Sub
