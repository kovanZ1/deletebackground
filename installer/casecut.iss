; Inno Setup script для CaseCutoutTool. Компиляция в CI: iscc installer\casecut.iss
; Результат: installer\Output\CaseCutoutTool-Setup.exe

[Setup]
AppName=CaseCutoutTool
AppVersion=0.1.2
DefaultDirName={autopf}\CaseCutoutTool
DefaultGroupName=CaseCutoutTool
DisableProgramGroupPage=yes
OutputBaseFilename=CaseCutoutTool-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\CaseCutoutTool\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CaseCutoutTool"; Filename: "{app}\CaseCutoutTool.exe"
Name: "{autodesktop}\CaseCutoutTool"; Filename: "{app}\CaseCutoutTool.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
Filename: "{app}\CaseCutoutTool.exe"; Description: "Запустить CaseCutoutTool"; Flags: nowait postinstall skipifsilent
