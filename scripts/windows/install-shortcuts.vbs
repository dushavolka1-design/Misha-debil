Option Explicit

Dim fso, sh, root, scriptDir, launcherPy, iconPath, desktop, startFolder
Dim venvPyw, venvPy, target
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
launcherPy = fso.BuildPath(root, "scripts\windows\docly_launcher.py")
iconPath = fso.BuildPath(root, "scripts\windows\assets\docly-icon.ico")
venvPyw = fso.BuildPath(root, "apps\api\.venv\Scripts\pythonw.exe")
venvPy = fso.BuildPath(root, "apps\api\.venv\Scripts\python.exe")

If Not fso.FileExists(launcherPy) Then
  WScript.Echo "Launcher not found: " & launcherPy
  WScript.Quit 1
End If
If Not fso.FileExists(iconPath) Then
  WScript.Echo "Icon not found: " & iconPath
  WScript.Quit 1
End If
If fso.FileExists(venvPyw) Then
  target = venvPyw
ElseIf fso.FileExists(venvPy) Then
  target = venvPy
Else
  WScript.Echo "Python environment missing. Run setup-desktop.ps1 first."
  WScript.Quit 1
End If

desktop = sh.SpecialFolders("Desktop")
startFolder = fso.BuildPath(sh.SpecialFolders("Programs"), "Docly")
' Never recursively delete user folders or shortcuts based on product-name matches.
' Old installations and manually created shortcuts remain untouched.
Call CheckShortcut(fso.BuildPath(desktop, "Docly.lnk"))
Call CheckShortcut(fso.BuildPath(startFolder, "Docly.lnk"))
If Not fso.FolderExists(startFolder) Then fso.CreateFolder startFolder
Call MakeShortcut(fso.BuildPath(desktop, "Docly.lnk"))
Call MakeShortcut(fso.BuildPath(startFolder, "Docly.lnk"))
WScript.Echo "OK"

Sub CheckShortcut(lnkPath)
  Dim sc, arguments
  If Not fso.FileExists(lnkPath) Then Exit Sub
  Set sc = sh.CreateShortcut(lnkPath)
  arguments = LCase(sc.Arguments)
  If InStr(arguments, "docly_launcher.py") = 0 And InStr(arguments, "start-dar") = 0 Then
    WScript.Echo "Refusing to replace an unrelated shortcut: " & lnkPath
    WScript.Quit 1
  End If
End Sub

Sub MakeShortcut(lnkPath)
  Dim sc
  Set sc = sh.CreateShortcut(lnkPath)
  sc.TargetPath = target
  sc.Arguments = """" & launcherPy & """"
  sc.WorkingDirectory = root
  sc.Description = "Docly"
  sc.WindowStyle = 1
  sc.IconLocation = iconPath & ",0"
  sc.Save
End Sub
