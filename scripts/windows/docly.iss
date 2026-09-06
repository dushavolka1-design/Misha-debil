#ifndef AppVersion
  #define AppVersion "0.2.1"
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

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Docly"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\windows\launch-installed.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\scripts\windows\assets\docly-icon.ico"
Name: "{userdesktop}\Docly"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\windows\launch-installed.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\scripts\windows\assets\docly-icon.ico"

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
      RaiseException('Could not start offline runtime setup.');
    if ExitCode <> 0 then
      RaiseException('Offline runtime setup failed. Installation is not ready; run setup again.');
  end;
end;
