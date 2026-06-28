' J.A.R.V.I.S — Lanzador simple (sin elevación UAC para evitar ventana de permisos)
Dim ws, fso, scriptDir, rootDir, py, cmd, mainPy
Set ws  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
rootDir = fso.GetParentFolderName(Left(scriptDir, Len(scriptDir) - 1)) & "\"

ws.CurrentDirectory = rootDir

mainPy = rootDir & "main.py"
If Not fso.FileExists(mainPy) Then
    MsgBox "JARVIS: no se encontró 'main.py' en la carpeta " & rootDir & ". Verifica la instalación.", 16, "JARVIS"
    WScript.Quit 1
End If

py = rootDir & ".venv\Scripts\pythonw.exe"
If Not fso.FileExists(py) Then
    py = rootDir & ".venv\Scripts\python.exe"
End If
If Not fso.FileExists(py) Then
    MsgBox "JARVIS: ejecuta el archivo install\Instalar_JARVIS.bat primero para configurar el entorno.", 16, "JARVIS"
    WScript.Quit 1
End If

cmd = Chr(34) & py & Chr(34) & " " & Chr(34) & mainPy & Chr(34)
ws.Run cmd, 0, False
Set ws  = Nothing
Set fso = Nothing
