Option Explicit

Dim fso, sh, root, scriptDir, launcherPy, iconPath, venvPyw, venvPy, target, cmd

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
launcherPy = fso.BuildPath(root, "scripts\windows\docly_launcher.py")
iconPath = fso.BuildPath(root, "scripts\windows\assets\docly-icon.ico")
venvPyw = fso.BuildPath(root, "apps\api\.venv\Scripts\pythonw.exe")
venvPy = fso.BuildPath(root, "apps\api\.venv\Scripts\python.exe")

If Not fso.FileExists(launcherPy) Then
  MsgBox "Launcher not found:" & vbCrLf & launcherPy, vbCritical, "Docly"
  WScript.Quit 1
End If

If fso.FileExists(venvPyw) Then
  target = venvPyw
ElseIf fso.FileExists(venvPy) Then
  target = venvPy
Else
  MsgBox "Python venv not found. Run scripts\windows\setup-desktop.ps1", vbExclamation, "Docly"
  WScript.Quit 1
End If

cmd = """" & target & """ """ & launcherPy & """"
' Visible splash (WindowStyle 1). Do not hide the window.
sh.Run cmd, 1, False
