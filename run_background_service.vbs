Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

pyExe = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python313\python.exe"

If Not fso.FileExists(pyExe) Then
    pyExe = "python.exe"
End If

cmd = Chr(34) & pyExe & Chr(34) & " " & Chr(34) & strPath & "\dashboard\app.py" & Chr(34)
WshShell.Run cmd, 0, False
