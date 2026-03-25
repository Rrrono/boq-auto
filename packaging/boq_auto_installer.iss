#define MyAppName "BOQ AUTO"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Bosco Consult"
#define MyAppURL "https://example.local"
#define MyAppExeName "BOQ AUTO.exe"
#define MyAdminExeName "BOQ AUTO Admin.exe"

[Setup]
AppId={{6E65D1C4-8C8C-4A61-B0B2-C4F26C23A201}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=boq_auto_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\BOQ AUTO Production\*"; DestDir: "{app}\production"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\BOQ AUTO Admin\*"; DestDir: "{app}\admin"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\BOQ AUTO"; Filename: "{app}\production\{#MyAppExeName}"
Name: "{group}\BOQ AUTO Admin"; Filename: "{app}\admin\{#MyAdminExeName}"
Name: "{autodesktop}\BOQ AUTO"; Filename: "{app}\production\{#MyAppExeName}"
Name: "{autodesktop}\BOQ AUTO Admin"; Filename: "{app}\admin\{#MyAdminExeName}"

[Run]
Filename: "{app}\production\{#MyAppExeName}"; Description: "Launch BOQ AUTO"; Flags: nowait postinstall skipifsilent
