; ============================================================================
;  Himaya (حماية) — ALL-IN-ONE installer  ->  Himaya-Setup-<version>.exe
;
;  Goal: one file, double-click, Suivant -> Suivant -> Terminé, done.
;  The setup.exe bundles the ENTIRE app:
;     • Himaya.exe (Python runtime + all libraries, no internet needed)
;     • Tesseract OCR engine (fra+eng) -> fake-receipt detection works
;       out of the box, nothing else to install
;     • Shortcuts, uninstaller, French/English wizard
;
;  Build (does everything automatically):  build_installer.bat
;  Manual:  pyinstaller --noconfirm himaya.spec   then  ISCC installer\himaya.iss
;
;  Inno Setup 6+ : https://jrsoftware.org/isinfo.php
;  Silent install:  Himaya-Setup-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES
; ============================================================================

; Root of the repo (folder containing this script's parent). All paths below
; are anchored to SourcePath so the script compiles from ANY working dir.
; NOTE: inside a #define line, use the ISPP expression "SourcePath + ..." —
; nested inline {#...} directives are NOT expanded in directive lines.
#define Root SourcePath + "\.."

#define MyAppName "Himaya"
#define MyAppNameAr "حماية"
#define MyAppVersion "1.1.4"
#define MyAppPublisher "Himaya (community)"
#define MyAppURL "https://github.com/belmezouarsouhil95-byte/test"
#define MyAppExeName "Himaya.exe"

; fail fast with a clear message if the portable build is missing
#if !DirExists(Root + "\dist\Himaya")
  #error "dist\Himaya not found - run PyInstaller first (build_installer.bat)"
#endif

[Setup]
; NOTE: never change AppId after shipping the first installer
; (updates/uninstall depend on it).
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
LicenseFile={#Root}\LICENSE
OutputDir={#SourcePath}\output
OutputBaseFilename=Himaya-Setup-{#MyAppVersion}
SetupIconFile={#Root}\assets\icon.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
MinVersion=10.0
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
french.FullInstall=Installation complète (application + moteur OCR de détection des faux reçus)
french.LaunchProgram=Lancer {#MyAppName}
french.DataDirQuestion=Voulez-vous aussi supprimer vos données Himaya (clients, commandes, liste noire) ?%n%nSi vous prévoyez de réinstaller Himaya, cliquez sur Non pour les conserver.
english.FullInstall=Full installation (application + OCR engine for fake-receipt detection)
english.LaunchProgram=Launch {#MyAppName}
english.DataDirQuestion=Do you also want to remove your Himaya data (customers, orders, blacklist)?%n%nClick No to keep it if you plan to reinstall Himaya.

[Tasks]
; "ez" defaults: desktop icon ON, OCR ON — the user can just click Suivant.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "ocr"; Description: "{cm:FullInstall}"; GroupDescription: "{cm:FullInstall}"

[Files]
; the whole PyInstaller output folder (Himaya.exe + Python + libraries + assets)
Source: "{#Root}\dist\Himaya\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; bundled Tesseract OCR (staged by build_installer.bat / CI). If not staged,
; the installer still builds; the app then uses hash+metadata+pixel checks
; and OCR can be pointed to an existing install in Settings.
Source: "{#SourcePath}\bundle\tesseract\*"; DestDir: "{app}\tesseract"; Flags: ignoreversion recursesubdirs skipifsourcedoesntexist; Tasks: ocr

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; app starts right after the last click (unless silent install)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent

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
                MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
