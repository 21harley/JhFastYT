; Compilar: iscc /DRepo=usuario/repo install\setup.iss
#ifndef Repo
  #define Repo "21harley/JhFastYT"
#endif

[Setup]
AppName=JhFastYT
AppVersion=0.1.1
DefaultDirName={localappdata}\JhFastYT
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist-setup
OutputBaseFilename=JhFastYT-Setup

[Files]
Source: "install.ps1"; DestDir: "{tmp}"; Flags: dontcopy

[Icons]
Name: "{userprograms}\JhFastYT"; Filename: "{app}\app\JhFastYT.exe"; WorkingDir: "{app}\app"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\tools"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  rc: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ExtractTemporaryFile('install.ps1');
    if not Exec('powershell.exe',
        '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\install.ps1') + '" -Repo "{#Repo}" -Dir "' + ExpandConstant('{app}') + '" -NoShortcut',
        '', SW_HIDE, ewWaitUntilTerminated, rc) or (rc <> 0) then
    begin
      MsgBox('No se pudieron descargar los componentes. Revisa tu conexion a internet y vuelve a intentarlo.', mbError, MB_OK);
      Abort;
    end;
  end;
end;
