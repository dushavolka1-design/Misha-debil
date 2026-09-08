Option Explicit
Dim fso, sh, root, scriptDir, py, launcher, env
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
py = fso.BuildPath(root, "apps\api\.venv\Scripts\pythonw.exe")
launcher = fso.BuildPath(scriptDir, "docly_launcher.py")
If Not fso.FileExists(py) Then
  MsgBox "Docly runtime is missing. Run the installer again.", vbCritical, "Docly"
  WScript.Quit 1
End If
Set env = sh.Environment("PROCESS")
env("PATH") = fso.BuildPath(root, "runtime\node") & ";" & env("PATH")
env("PYTHONDONTWRITEBYTECODE") = "1"
sh.CurrentDirectory = root
sh.Run """" & py & """ """ & launcher & """", 1, False
