; JARVIS AI — Inno Setup Installer
; Compile with Inno Setup 6+ (jrsoftware.org/isdl.php)
; Output: Instalar_JARVIS.exe

#define MyAppName "JARVIS AI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "YongllyPM"
#define MyAppURL "https://github.com/YongllyPM/Jarvis"
#define MyAppExeName "JARVIS.lnk"

[Setup]
AppId={{E8F5A8C3-9B2A-4D6F-8C7D-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\JARVIS
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=Instalar_JARVIS
SetupIconFile=assets\jarvis_icono.ico
UninstallDisplayIcon={app}\assets\jarvis_icono.ico
Compression=lzma2/ultra
SolidCompression=yes
PrivilegesRequired=admin
DisableProgramGroupPage=yes
DisableReadyPage=no
UsePreviousAppDir=yes
DisableWelcomePage=no
CloseApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
spanish.WelcomeLabel1=Bienvenido a JARVIS AI
spanish.WelcomeLabel2=Este asistente te guiará en la instalación de JARVIS, tu asistente personal con inteligencia artificial.%n%nJARVIS te permite controlar tu PC con voz y texto, ver la pantalla, procesar archivos, generar imágenes, conectarte con Telegram y mucho más.%n%n--- CRÉDITOS ---%nCódigo base original por Dexter-666 (JARVIS v1)%nModificado, corregido y mejorado por YongllyPM%nNueva interfaz, personajes 2D, tienda, actualizaciones y más funciones%n%n

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "main.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "ui.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "install.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "build_characters.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "download_vosk.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "file_events.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "beta_config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "sitecustomize.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: ".gitignore"; DestDir: "{app}"; Flags: ignoreversion
Source: "Iniciar JARVIS Beta.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "Desinstalar_JARVIS.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "Instalar_JARVIS.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "actions\*"; DestDir: "{app}\actions"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "agent\*"; DestDir: "{app}\agent"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "backups\*"; DestDir: "{app}\backups"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "launchers\*"; DestDir: "{app}\launchers"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "memory\*"; DestDir: "{app}\memory"; Flags: ignoreversion recursesubdirs createallsubdirs

; .venv excluded (rebuilt by install.py)

[Dirs]
Name: "{app}"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Iniciar JARVIS Beta.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\jarvis_icono.ico"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\Iniciar JARVIS Beta.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\jarvis_icono.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\Instalar_JARVIS.bat"; Parameters: "--install"; WorkingDir: "{app}"; Flags: runhidden runascurrentuser; StatusMsg: "Instalando dependencias... (puede tomar varios minutos)"
Filename: "{app}\Iniciar JARVIS Beta.vbs"; WorkingDir: "{app}"; Description: "Iniciar JARVIS ahora"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
Filename: "{app}\Instalar_JARVIS.bat"; Parameters: "--uninstall"; WorkingDir: "{app}"; Flags: runhidden runascurrentuser

[Code]
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := 'La instalación se completó correctamente.'#13#10#13#10'JARVIS se iniciará automáticamente al cerrar este asistente.';
end;
