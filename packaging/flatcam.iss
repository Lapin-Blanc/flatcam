; Inno Setup script for FlatCAM (Windows installer).
;
; Packages the Nuitka standalone build (flatcam_run.dist) into a per-user
; installer: no UAC/admin required, installs under %LocalAppData%\Programs.
;
; Build:
;   iscc /DAppVersion=8.6.2 /DSourceDir="..\dist-nuitka\flatcam_run.dist" packaging\flatcam.iss
;
; AppVersion and SourceDir default to dev-friendly values when not passed, so
; the script also compiles from a local checkout for testing.

#define AppName "FlatCAM"
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist-nuitka\flatcam_run.dist"
#endif
#define AppExe "flatcam.exe"
#define AppPublisher "FlatCAM modernization fork (Lapin-Blanc)"
#define AppURL "https://github.com/Lapin-Blanc/flatcam"

[Setup]
; AppId uniquely identifies the app for upgrades/uninstall; keep it stable.
AppId={{3F53C451-575D-43CE-A18F-6113C5B6122B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
; Per-user install: no elevation, lands in %LocalAppData%\Programs\FlatCAM.
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist-installer
OutputBaseFilename=FlatCAM-{#AppVersion}-windows-x86_64-setup
SetupIconFile=..\share\flatcam_icon256.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 64-bit only (matches the Nuitka x86_64 build).
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
