#define MyAppName "yt-dlp-gui"
#ifndef AppVersion
  #define AppVersion "dev"
#endif

[Setup]
AppId={{1F094291-A9C4-4A3C-B7CB-E75639D7A31A}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher=dsymbol
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
LicenseFile=
OutputDir={#RepoRoot}\release
OutputBaseFilename=yt-dlp-gui-installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\yt-dlp-gui.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#RepoRoot}\app\dist\yt-dlp-gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\yt-dlp-gui.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\yt-dlp-gui.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\yt-dlp-gui.exe"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
