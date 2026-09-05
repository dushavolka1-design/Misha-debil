Option Explicit

Dim fso, sh, root, scriptDir, launcherPy, iconPath, desktop, startFolder, shortcutName, productTitle, oldProductTitle
Dim venvPyw, venvPy, target, pythonCmd

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
launcherPy = fso.BuildPath(root, "scripts\windows\docly_launcher.py")
iconPath = fso.BuildPath(root, "scripts\windows\assets\docly-icon.ico")
venvPyw = fso.BuildPath(root, "apps\api\.venv\Scripts\pythonw.exe")
venvPy = fso.BuildPath(root, "apps\api\.venv\Scripts\python.exe")

productTitle = "Docly"
oldProductTitle = ChrW(&H410) & ChrW(&H43D) & ChrW(&H430) & ChrW(&H43B) & ChrW(&H438) & ChrW(&H437) & ChrW(&H430) & ChrW(&H442) & ChrW(&H43E) & ChrW(&H440) & " " & _
  ChrW(&H434) & ChrW(&H43E) & ChrW(&H43A) & ChrW(&H443) & ChrW(&H43C) & ChrW(&H435) & ChrW(&H43D) & ChrW(&H442) & ChrW(&H43E) & ChrW(&H432) & " " & ChrW(&H420) & ChrW(&H424)
shortcutName = productTitle & ".lnk"

If Not fso.FileExists(launcherPy) Then
  MsgBox "Launcher not found:" & vbCrLf & launcherPy, vbCritical, productTitle
  WScript.Quit 1
End If
If Not fso.FileExists(iconPath) Then
  MsgBox "Icon not found:" & vbCrLf & iconPath, vbCritical, productTitle
  WScript.Quit 1
End If

If fso.FileExists(venvPyw) Then
  target = venvPyw
ElseIf fso.FileExists(venvPy) Then
  target = venvPy
Else
  pythonCmd = sh.ExpandEnvironmentStrings("%SystemRoot%\py.exe")
  If fso.FileExists(pythonCmd) Then
    target = pythonCmd
  Else
    target = "python.exe"
  End If
End If

desktop = sh.SpecialFolders("Desktop")
Call PurgeShortcuts(desktop, False)
Call PurgeShortcuts(sh.SpecialFolders("Programs"), True)

startFolder = fso.BuildPath(sh.SpecialFolders("Programs"), productTitle)
If Not fso.FolderExists(startFolder) Then fso.CreateFolder startFolder

Call MakeShortcut(fso.BuildPath(desktop, shortcutName))
Call MakeShortcut(fso.BuildPath(startFolder, shortcutName))

WScript.Echo "OK"

Sub MakeShortcut(lnkPath)
  Dim sc
  Set sc = sh.CreateShortcut(lnkPath)
  sc.TargetPath = target
  sc.Arguments = """" & launcherPy & """"
  sc.WorkingDirectory = root
  sc.Description = productTitle
  sc.WindowStyle = 1
  sc.IconLocation = iconPath & ",0"
  sc.Save
End Sub

Function IsDarShortcut(lnkPath)
  Dim sc, t, a, n
  IsDarShortcut = False
  If Not fso.FileExists(lnkPath) Then Exit Function
  Set sc = sh.CreateShortcut(lnkPath)
  t = LCase(sc.TargetPath)
  a = LCase(sc.Arguments)
  n = LCase(fso.GetFileName(lnkPath))
  If InStr(t, "document-analyzer-rf") > 0 Then IsDarShortcut = True: Exit Function
  If InStr(a, "document-analyzer-rf") > 0 Then IsDarShortcut = True: Exit Function
  If InStr(a, "start-dar") > 0 Then IsDarShortcut = True: Exit Function
  If InStr(a, "docly_launcher") > 0 Then IsDarShortcut = True: Exit Function
  If InStr(n, "document analyzer") > 0 Then IsDarShortcut = True: Exit Function
  If InStr(n, "docly") > 0 Then IsDarShortcut = True
End Function

Function IsOldProductFolder(folderName)
  Dim n
  n = LCase(folderName)
  IsOldProductFolder = False
  If n = "docly" Then Exit Function
  If folderName = oldProductTitle Then IsOldProductFolder = True: Exit Function
  If InStr(n, "document analyzer") > 0 Then IsOldProductFolder = True
End Function

Sub PurgeShortcuts(folderPath, recursive)
  Dim folder, f, subf
  If Not fso.FolderExists(folderPath) Then Exit Sub
  Set folder = fso.GetFolder(folderPath)
  For Each f In folder.Files
    If LCase(fso.GetExtensionName(f.Name)) = "lnk" Then
      If IsDarShortcut(f.Path) Then fso.DeleteFile f.Path, True
    End If
  Next
  If recursive Then
    For Each subf In folder.SubFolders
      If IsOldProductFolder(subf.Name) Then
        Call DeleteFolderRecursive(subf.Path)
      Else
        Call PurgeShortcuts(subf.Path, True)
      End If
    Next
  End If
End Sub

Sub DeleteFolderRecursive(folderPath)
  Dim folder, f, subf
  If Not fso.FolderExists(folderPath) Then Exit Sub
  Set folder = fso.GetFolder(folderPath)
  For Each f In folder.Files
    fso.DeleteFile f.Path, True
  Next
  For Each subf In folder.SubFolders
    Call DeleteFolderRecursive(subf.Path)
  Next
  fso.DeleteFolder folderPath, True
End Sub
