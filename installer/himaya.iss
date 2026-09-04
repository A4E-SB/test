; ============================================================================
;  Himaya (حماية) — Inno Setup script  ->  Himaya-Setup-<version>.exe
;
;  Prerequisite: the portable build must exist first:
;      build_installer.bat   (does everything: venv -> PyInstaller -> this script)
;  or manually:
;      pyinstaller --noconfirm himaya.spec
;      ISCC.exe installer\himaya.iss
;
;  Inno Setup 6+ : https://jrsoftware.org/isinfo.php
;  Silent install:  Himaya-Setup-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES
; ============================================================================

#define MyAppName "Himaya"
#define MyAppNameAr "حماية"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Himaya (community)"
#define MyAppURL "https://github.com/belmezouarsouhil95-byte/test"
#define MyAppExeName "Himaya.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Never change it after shipping the first installer (uninstall/updates depend on it).
AppId={{7A6C81D4-52F9-4B0E-9C3D-1E5A84B2F6C9}
AppName={#MyAppName} ({#MyAppNameAr})
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; MIT license shown during install
LicenseFile=..\LICENSE
; Uncomment the next line to disable the license page if you remove the file
; LicenseFile=
OutputDir=output
OutputBaseFilename=Himaya-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
MinVersion=10.0
PrivilegesRequiredOverridesAllowed=dialog
; smaller download / can fit a USB key alongside the portable build
; (the app itself is ~70-95 MB; the installer compresses it to roughly 40-60 MB)

[Languages]
; English is Inno's default; French is the main language for Algerian sellers.
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
french.DataDirQuestion=Voulez-vous aussi supprimer vos données Himaya (clients, commandes, liste noire) ?%n%nSi vous prévoyez de réinstaller Himaya, cliquez sur Non pour les conserver.
french.LaunchProgram=Lancer {#MyAppName}
english.DataDirQuestion=Do you also want to remove your Himaya data (customers, orders, blacklist)?%n%nClick No to keep it if you plan to reinstall Himaya.
english.LaunchProgram=Launch {#MyAppName}

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; the whole PyInstaller output folder (Himaya.exe + DLLs + assets)
Source: "..\dist\Himaya\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; remove generated PDF labels etc. inside {app} (user data in %APPDATA% is
; handled separately by the prompt below)

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  // After the files are removed, ask ONCE whether to also delete the
  // seller's database (%APPDATA%\Himaya). Default choice = keep (No).
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}') + '\Himaya';
    if DirExists(DataDir) then
    begin
      if MsgBox(ExpandConstant('{cm:DataDirQuestion}'), mbConfirmation,
                MB_YES_NO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
