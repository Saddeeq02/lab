[Setup]
AppName=Solunex Lab Scientist
AppVersion=1.0
DefaultDirName={pf}\SolunexLab
DefaultGroupName=Solunex Lab
OutputDir=dist_installer
OutputBaseFilename=SolunexLabSetup
SetupIconFile=iande.ico

Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\SolunexLab.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Solunex Lab Scientist"; Filename: "{app}\SolunexLab.exe"
Name: "{autodesktop}\Solunex Lab Scientist"; Filename: "{app}\SolunexLab.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Icon"; GroupDescription: "Additional Icons"

[Run]
Filename: "{app}\SolunexLab.exe"; Description: "Launch Solunex Lab Scientist"; Flags: nowait postinstall skipifsilent