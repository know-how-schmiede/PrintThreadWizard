#define MyAppName "PrintThread Wizard"
#define MyAppFileName "PrintThreadWizard"
#define MyAppVersion "0.9.7"
#define MyAppPublisher "Rene Triebenstein / Know-How-Schmiede"
#define MyAppSourceDir "..\Fusion_AddIn\PrintThread Wizard"

[Setup]
AppId={{F4882367-D245-49F4-81DF-D84D111A85B4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={code:GetDefaultInstallDir}
DisableDirPage=no
AlwaysShowDirOnReadyPage=yes
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename={#MyAppFileName}_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UsePreviousAppDir=no
DirExistsWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,.vscode\*"

[Code]
var
  DetectionDone: Boolean;
  DetectedApiPath: String;
  DetectionMessage: String;

procedure DetectFusionApiPath;
var
  FusionPath, Fusion360Path: String;
  HasFusion, HasFusion360: Boolean;
begin
  if DetectionDone then
    Exit;

  FusionPath := ExpandConstant('{userappdata}\Autodesk\Autodesk Fusion\API');
  Fusion360Path := ExpandConstant('{userappdata}\Autodesk\Autodesk Fusion 360\API');
  HasFusion := DirExists(FusionPath);
  HasFusion360 := DirExists(Fusion360Path);

  { Directory presence is a suggestion, not proof of Fusion's active setting. }
  if HasFusion and not HasFusion360 then
    DetectedApiPath := FusionPath
  else
    DetectedApiPath := Fusion360Path;

  if HasFusion and HasFusion360 then
    DetectionMessage := 'Both Fusion API folders exist. Select the folder configured in Fusion.'
  else if not HasFusion and not HasFusion360 then
    DetectionMessage := 'No standard Fusion API folder was found. Select the folder configured in Fusion.'
  else
    DetectionMessage := 'An existing Fusion API folder was found. Check it against your Fusion settings.';

  DetectionDone := True;
  Log(DetectionMessage + ' Suggested API folder: ' + DetectedApiPath);
end;

function GetDefaultInstallDir(Param: String): String;
begin
  DetectFusionApiPath;
  Result := AddBackslash(DetectedApiPath) + 'AddIns\{#MyAppName}';
end;

procedure InitializeWizard;
var
  ExtraHeight: Integer;
begin
  DetectFusionApiPath;
  WizardForm.SelectDirLabel.Caption := DetectionMessage + #13#10 +
    'Fusion > Preferences > API > Default Path for Scripts and Add-Ins.' + #13#10 +
    'Destination: that path + \AddIns\{#MyAppName}';
  ExtraHeight := ScaleY(80) - WizardForm.SelectDirLabel.Height;
  WizardForm.SelectDirLabel.Height := ScaleY(80);
  WizardForm.DirEdit.Top := WizardForm.DirEdit.Top + ExtraHeight;
  WizardForm.DirBrowseButton.Top := WizardForm.DirBrowseButton.Top + ExtraHeight;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  { Silent setup cannot ask the user to resolve an ambiguous/custom path. }
  if WizardSilent and (ExpandConstant('{param:DIR|}') = '') then
    Result := 'Silent installation requires /DIR="<Fusion API path>\AddIns\{#MyAppName}". ' +
      'Check the API path in Fusion Preferences first.';
end;
