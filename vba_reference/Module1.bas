Attribute VB_Name = "Module1"
Sub Button2_Click()

End Sub


Sub ExportAllVBA()
    Dim vbComp As Object
    Dim exportPath As String

    exportPath = ThisWorkbook.Path & "\VBA_Export\"

    If Dir(exportPath, vbDirectory) = "" Then
        MkDir exportPath
    End If

    For Each vbComp In ThisWorkbook.VBProject.VBComponents
        Select Case vbComp.Type
            Case 1 ' Standard Module
                vbComp.Export exportPath & vbComp.name & ".bas"
            Case 2 ' Class Module
                vbComp.Export exportPath & vbComp.name & ".cls"
            Case 3 ' UserForm
                vbComp.Export exportPath & vbComp.name & ".frm"
        End Select
    Next vbComp

    MsgBox "Export xong toàn b? VBA!", vbInformation
End Sub

