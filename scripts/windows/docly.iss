#ifndef AppVersion
  #define AppVersion "0.2.2"
#endif
#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif

[Setup]
AppId={{745693E7-F4C3-494A-AEA5-3F91839937ED}
AppName=Docly
AppVersion={#AppVersion}
AppPublisher=Docly
DefaultDirName={localappdata}\Programs\Docly
DefaultGroupName=Docly
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=Docly-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\scripts\windows\assets\docly-icon.ico
SetupIconFile={#PayloadDir}\scripts\windows\assets\docly-icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
english.StartMenuTask=Create a Start menu shortcut
russian.StartMenuTask=Создать ярлык в меню «Пуск»
english.AutostartTask=Start Docly when you sign in
russian.AutostartTask=Запускать Docly при входе в систему
english.RuntimeStartFailed=Could not start offline runtime setup.
russian.RuntimeStartFailed=Не удалось запустить автономную установку среды выполнения.
english.RuntimeSetupFailed=Offline runtime setup failed. Installation is not ready; see the setup log.
russian.RuntimeSetupFailed=Не удалось установить среду выполнения. Установка не готова к работе; подробности в журнале установки.

[Tasks]
Name: "startmenu"; Description: "{cm:StartMenuTask}"; Flags: unchecked
Name: "autostart"; Description: "{cm:AutostartTask}"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Remove only this application's optional shortcut when explicitly deselected.
Type: files; Name: "{group}\Docly.lnk"; Tasks: not startmenu

[Icons]
Name: "{group}\Docly"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\windows\launch-installed.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\scripts\windows\assets\docly-icon.ico"; Tasks: startmenu
Name: "{userdesktop}\Docly"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\windows\launch-installed.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\scripts\windows\assets\docly-icon.ico"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Docly"; ValueData: """{sys}\wscript.exe"" ""{app}\scripts\windows\launch-installed.vbs"""; Flags: uninsdeletevalue; Tasks: autostart
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Docly"; Flags: deletevalue dontcreatekey; Tasks: not autostart

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\windows\launch-installed.vbs"""; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,Docly}"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; Only generated application/runtime files. Never delete LocalAppData\Docly.
Type: filesandordirs; Name: "{app}\apps\api\.venv"
Type: filesandordirs; Name: "{app}\apps\web\.next\cache"
Type: filesandordirs; Name: "{app}\artifacts\local-run"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\scripts\windows\install-runtime.ps1') + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      RaiseException(ExpandConstant('{cm:RuntimeStartFailed}'));
    if ExitCode <> 0 then
      RaiseException(ExpandConstant('{cm:RuntimeSetupFailed}'));
  end;
end;
