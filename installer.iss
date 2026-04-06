[Setup]
AppName=IE Lab
AppVersion=1.0
DefaultDirName={pf}\IELab
DefaultGroupName=IE Lab
OutputDir=dist_installer
OutputBaseFilename=IELabSetup
SetupIconFile=C:\Users\RAFAWA ENTERPRISES\Desktop\solunex_lab_app\iande.ico

Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\IELab.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\IE Lab"; Filename: "{app}\IELab.exe"
Name: "{autodesktop}\IE Lab"; Filename: "{app}\IELab.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Icon"; GroupDescription: "Additional Icons"

[Run]
Filename: "{app}\IELab.exe"; Description: "Launch IE Lab"; Flags: nowait postinstall skipifsilent