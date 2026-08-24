#define MyAppName "PrintThread Wizard"
#define MyAppFileName "PrintThreadWizard"
#define MyAppVersion "0.8.0"
#define MyAppPublisher "Rene Triebenstein / Know-How-Schmiede"
#define MyAppSourceDir "..\Fusion_AddIn\PrintThread Wizard"

[Setup]
AppId={{F4882367-D245-49F4-81DF-D84D111A85B4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\Autodesk\Autodesk Fusion 360\API\AddIns\{#MyAppName}
DisableDirPage=yes
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename={#MyAppFileName}_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UsePreviousAppDir=yes
DirExistsWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,.vscode\*"
