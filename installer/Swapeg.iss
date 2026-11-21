; Swapeg installer (Inno Setup 6). Compiled by tools\build.ps1 - paths come from environment variables.
; Keep this file ASCII-only.

#define MyAppName "Swapeg"
#define MyAppExe "Swapeg.exe"
#define MyAppVersion GetEnv("SWAPEG_VERSION")
#define RepoRoot GetEnv("SWAPEG_ROOT")
#define AppDist GetEnv("SWAPEG_DIST")
#define OutDir GetEnv("SWAPEG_OUT")

[Setup]
AppId={{B7D4E2A1-5C3F-4A8E-9D16-2F0C8E7A41B3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Swapeg
VersionInfoVersion={#MyAppVersion}
; Per-user install: the app downloads ffmpeg into its own "bin" folder, so the install folder must be writable.
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutDir}
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-Setup
SetupIconFile={#RepoRoot}\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
MinVersion=10.0

[Languages]
#if FileExists(AddBackslash(CompilerPath) + "Languages\Korean.isl")
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#AppDist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; AppUserModelID: "Swapeg.App"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; AppUserModelID: "Swapeg.App"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Remove the app's saved settings on uninstall.
Root: HKCU; Subkey: "Software\Swapeg"; Flags: uninsdeletekey

[UninstallDelete]
; The "bin" folder (downloaded ffmpeg) is created after installation, so remove it explicitly.
Type: filesandordirs; Name: "{app}"
