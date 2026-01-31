Attribute VB_Name = "modMsgboxTV"
Option Explicit

#If VBA7 Then
    Private Declare PtrSafe Function GetActiveWindow Lib "user32" () As LongPtr
    Public Declare PtrSafe Function MessageBoxW Lib "user32" _
                                    (ByVal hwnd As LongPtr, _
                                    ByVal lpText As LongPtr, _
                                    ByVal lpCaption As LongPtr, _
                                    ByVal wType As Long) As Long
#Else
    Private Declare Function GetActiveWindow Lib "user32" () As Long
    Public Declare Function MessageBoxW Lib "user32" _
                            (ByVal hwnd As Long, _
                            ByVal lpText As Long, _
                            ByVal lpCaption As Long, _
                            ByVal wType As Long) As Long
#End If

Public Function MsgBoxUni(ByVal sMsgUni As String, Optional ByVal Buttons As VbMsgBoxStyle = vbOKOnly, Optional ByVal sTitleUni As String = "Thông báo") As VbMsgBoxResult
    MsgBoxUni = MessageBoxW(GetActiveWindow, StrPtr(sMsgUni), StrPtr(sTitleUni), Buttons)
End Function
