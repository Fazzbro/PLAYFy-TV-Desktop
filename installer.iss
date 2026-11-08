; ==============================================================================
; Inno Setup Script for PLAYFy TV Desktop
; Target OS: Windows 10 / Windows 11 (64-bit)
; Compiler: Inno Setup 6 / 7
; ==============================================================================

#define MyAppName "PLAYFy TV"
#define MyAppVersion "1.7.0"
#define MyAppPublisher "PLAYFy TV Contributors"
#define MyAppURL "https://github.com/Fazzbro/PLAYFy-TV-Desktop"
#define MyAppExeName "PLAYFy-TV.exe"
#define MyOutputDir "dist\installer"
#define MyOutputBaseFilename "PLAYFy-TV-Setup-v1.7.0"

[Setup]
; Unique application GUID for install/uninstall tracking
AppId={{8B1D4F3A-8F5E-4B7C-9F3E-2A4B6C8D0E1F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Default destination: C:\Users\<User>\AppData\Local\Programs\PLAYFy TV (non-admin)
; or C:\Program Files\PLAYFy TV (if installed with admin rights)
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE

; Modern installer appearance and visual assets
SetupIconFile=logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
WizardSizePercent=100

; Compression settings (optimal balance of installation speed and small binary size)
Compression=lzma2/ultra64
SolidCompression=yes

; Output settings
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseFilename}

; Multi-user privilege handling (allows standard user install without UAC, or admin install)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; Architecture settings (64-bit Intel/AMD Windows)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Clean upgrade behavior: close running instances before overwriting
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=auto
UsedUserAreasWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "Create Start Menu shortcuts"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Launch {#MyAppName} on Windows startup"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Primary application directory built by PyInstaller
Source: "dist\PLAYFy-TV\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: startmenuicon
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Registry]
; Windows startup launch registry key (enabled only if autostart task was checked)
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PLAYFyTV"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
