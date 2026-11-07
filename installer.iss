; Inno Setup Script for Edge Sidecar Browser (v1.3.2)
; ========================================================

#define MyAppName "Edge Sidecar Browser"
#define MyAppVersion "1.3.2"
#define MyAppPublisher "EdgeSidecar Open Source"
#define MyAppURL "https://github.com/L-Jack-00/EdgeSidecar"
#define MyAppExeName "EdgeSidecar.exe"

[Setup]
AppId={{C9F28D13-7D15-4D19-9B21-9C3E5A6B7E8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\EdgeSidecar
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist_installer
OutputBaseFilename=EdgeSidecar-Setup-v1.3.2
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=app.ico

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "registerbrowser"; Description: "Windows 기본 웹 브라우저로 등록 (외부 링크 연결 지원)"; Flags: checkedonce

[Files]
Source: "dist\EdgeSidecar\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Register StartMenuInternet client in HKCU
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar"; ValueType: string; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar"; ValueType: string; ValueName: "LocalizedString"; ValueData: "{#MyAppName}"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\DefaultIcon"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"",0"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"""
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#MyAppName}"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: """{app}\{#MyAppExeName}"",0"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "{#MyAppName} - Zero-Telemetry & Rule Engine Web Browser"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities"; ValueType: string; ValueName: "StartMenuInternet"; ValueData: "EdgeSidecar"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities\FileAssociations"; ValueType: string; ValueName: ".htm"; ValueData: "EdgeSidecarHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities\FileAssociations"; ValueType: string; ValueName: ".html"; ValueData: "EdgeSidecarHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities\URLAssociations"; ValueType: string; ValueName: "http"; ValueData: "EdgeSidecarHTML"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities\URLAssociations"; ValueType: string; ValueName: "https"; ValueData: "EdgeSidecarHTML"
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "EdgeSidecar"; ValueData: "Software\Clients\StartMenuInternet\EdgeSidecar\Capabilities"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\EdgeSidecarHTML"; ValueType: string; ValueData: "Edge Sidecar HTML Document"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\EdgeSidecarHTML\DefaultIcon"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"",0"
Root: HKCU; Subkey: "Software\Classes\EdgeSidecarHTML\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
