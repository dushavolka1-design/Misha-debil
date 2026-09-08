#ifndef PayloadDir
  #error PayloadDir must be provided by build-installer.ps1
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\release"
#endif
[Setup]
AppId={{86D10F83-C1C7-4DD9-9B3C-0A2268F7E97D}
AppName=Docly
AppVersion=0.1.0
AppPublisher=Docly
DefaultDirName={localappdata}\Programs\Docly
DefaultGroupName=Docly
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
OutputDir={#ReleaseDir}
OutputBaseFilename=Docly-Setup-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Docly
UninstallDisplayIcon={app}\scripts\windows\assets\docly-icon.ico
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\installer\prerequisites.ps1"; Flags: dontcopy
Source: "{#PayloadDir}\installer\check-running.ps1"; Flags: dontcopy

[Icons]
Name: "{userdesktop}\Docly"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\first-run.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\scripts\windows\assets\docly-icon.ico"
Name: "{userprograms}\Docly\Docly"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\first-run.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\scripts\windows\assets\docly-icon.ico"

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\first-run.ps1"""; Description: "Запустить Docly (первый запуск требует интернета)"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Only generated dependencies/caches. NEVER recursively delete {app} or user data.
Type: filesandordirs; Name: "{app}\node_modules"
Type: filesandordirs; Name: "{app}\apps\web\node_modules"
Type: filesandordirs; Name: "{app}\apps\web\.next"
Type: filesandordirs; Name: "{app}\apps\api\node_modules"
Type: filesandordirs; Name: "{app}\apps\api\.venv"
Type: filesandordirs; Name: "{app}\packages\ui\node_modules"
Type: filesandordirs; Name: "{app}\packages\contracts\node_modules"
Type: filesandordirs; Name: "{app}\installer\.tools"
Type: files; Name: "{app}\installer\prepared.txt"
Type: files; Name: "{app}\installer\bootstrap.lock"

[Code]
function PowerShellPath(): String;
begin
  Result := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
end;

function InitializeSetup(): Boolean;
begin
  Result := FileExists(PowerShellPath());
  if not Result then
    MsgBox('Для установки Docly требуется Windows PowerShell 5.1. Восстановите компонент PowerShell в Windows и повторите установку.', mbError, MB_OK);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Code: Integer; Args: String;
begin
  Result := '';
  ExtractTemporaryFile('check-running.ps1');
  if not Exec(PowerShellPath(), '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\check-running.ps1') + '" -InstallRoot "' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewWaitUntilTerminated, Code) then begin
    Result := 'Не удалось проверить запущенные процессы Docly.'; exit;
  end;
  if Code <> 0 then begin
    Result := 'Docly запущен или проверка процессов не удалась. Закройте процессы Docly перед установкой. См. installer\README.md.'; exit;
  end;
  ExtractTemporaryFile('prerequisites.ps1');
  Args := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\prerequisites.ps1') + '"';
  if WizardSilent then Args := Args + ' -CheckOnly';
  if not Exec(PowerShellPath(), Args, '', SW_SHOW, ewWaitUntilTerminated, Code) then begin
    Result := 'Не удалось запустить проверку Node.js и Python.'; exit;
  end;
  if Code <> 0 then Result := 'Установите Node.js 20+ x64 и Python 3.12+ x64, затем повторите установку Docly.';
end;

function InitializeUninstall(): Boolean;
var Code: Integer;
begin
  Result := False;
  if not Exec(PowerShellPath(), '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\installer\check-running.ps1') + '" -InstallRoot "' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewWaitUntilTerminated, Code) then exit;
  Result := Code = 0;
  if not Result then
    MsgBox('Закройте процессы Docly перед удалением. Если окно браузера уже закрыто, остановите процессы из папки Docly в Диспетчере задач. Пользовательские данные будут сохранены.', mbError, MB_OK);
end;
