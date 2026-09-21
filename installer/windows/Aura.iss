#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef Edition
  #define Edition "Essential"
#endif
#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef OutputPath
  #define OutputPath "..\..\dist\windows"
#endif
#if Edition == "Complete"
  #define EditionLabel "Completo"
#else
  #define EditionLabel "Essencial"
#endif

[Setup]
AppId={{9744A9C1-19F6-4D16-90E2-9E2D016A3F10}
AppName=Aura
AppVersion={#AppVersion}
AppVerName=Aura {#AppVersion} - {#EditionLabel}
AppPublisher=Aura
DefaultDirName={localappdata}\Programs\Aura
DefaultGroupName=Aura
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
MinVersion=10.0.19041
OutputDir={#OutputPath}
OutputBaseFilename=Aura-Setup-{#EditionLabel}-{#AppVersion}
SetupIconFile=aura.ico
UninstallDisplayIcon={app}\aura.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile={#PayloadDir}\LEIAME.txt
SetupLogging=yes
CloseApplications=no
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho Iniciar Aura na área de trabalho"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Iniciar Aura"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\desktop\Start-Aura.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\aura.ico"
Name: "{group}\Configurar Aura"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\desktop\Configure-Aura.ps1"" -Mode {#Edition}"; WorkingDir: "{app}"; IconFilename: "{app}\aura.ico"
Name: "{group}\Backup Aura"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\desktop\Backup-Aura.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\aura.ico"
Name: "{group}\LEIAME"; Filename: "{app}\LEIAME.txt"
Name: "{group}\Desinstalar Aura"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Iniciar Aura"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\desktop\Start-Aura.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\aura.ico"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\desktop\Configure-Aura.ps1"" -Mode {#Edition}"; Description: "Configurar o Aura agora (internet e criação da administradora)"; Flags: postinstall skipifsilent runasoriginaluser; WorkingDir: "{app}"

[UninstallRun]
; No database deletion and no uninstall of shared Python/MySQL/VC++ runtimes.
