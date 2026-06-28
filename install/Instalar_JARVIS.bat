@echo off
title Instalador de JARVIS AI

:: ── Sin flag: mostrar menú interactivo ──────────────────────────────────────
if "%1"=="" goto :interactive

:: ── Flags ────────────────────────────────────────────────────────────────────
if "%1"=="--run" goto :run_jarvis
if "%1"=="--install" goto :run_install
if "%1"=="--uninstall" goto :run_install
if "%1"=="--autostart" goto :run_autostart
if "%1"=="--noautostart" goto :run_noautostart

:: ── Flag desconocido: mostrar ayuda ──────────────────────────────────────────
echo Uso: %~nx0 [--install ^| --uninstall ^| --run ^| --autostart ^| --noautostart]
echo   --install     Instalar/actualizar dependencias
echo   --uninstall   Desinstalar
echo   --run         Iniciar JARVIS
echo   --autostart   Agregar JARVIS al inicio de Windows
echo   --noautostart Quitar JARVIS del inicio de Windows
pause
exit /b

:interactive
:: ── Solicitar permisos de Administrador ──────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Solicitando permisos de administrador...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)
:: Ya somos admin: ir al instalador interactivo
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" if exist ".venv\pyvenv.cfg" (
    ".venv\Scripts\python.exe" "install\install.py"
    pause
    exit
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    python "install\install.py"
    pause
    exit
)
echo [ERROR] No se encontro una instalacion valida de Python.
pause
exit

:run_jarvis
cd /d "%~dp0.."
if exist ".venv\Scripts\pythonw.exe" if exist ".venv\pyvenv.cfg" (
    start "" ".venv\Scripts\pythonw.exe" "main.py"
    exit
)
if exist ".venv\Scripts\python.exe" if exist ".venv\pyvenv.cfg" (
    start "" ".venv\Scripts\python.exe" "main.py"
    exit
)
echo [ERROR] No se encontro el entorno virtual. Ejecuta primero "Instalar_JARVIS.bat --install".
pause
exit

:run_autostart
cd /d "%~dp0.."
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "BAT_PATH=%~dp0..\install\Instalar_JARVIS.bat"
set "SHORTCUT_PATH=%STARTUP_DIR%\JARVIS.lnk"
if exist "%SHORTCUT_PATH%" (
    echo [INFO] JARVIS ya esta en el inicio de Windows.
) else (
    powershell -Command ^
        "$WshShell = New-Object -ComObject WScript.Shell; ^
         $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); ^
         $Shortcut.TargetPath = '%BAT_PATH%'; ^
         $Shortcut.Arguments = '--run'; ^
         $Shortcut.WorkingDirectory = '%~dp0..\'; ^
         $Shortcut.WindowStyle = 7; ^
         $Shortcut.Description = 'JARVIS AI Asistente'; ^
         $Shortcut.Save()"
    echo [OK] JARVIS agregado al inicio de Windows.
)
pause
exit /b

:run_noautostart
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.lnk"
if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [OK] JARVIS quitado del inicio de Windows.
) else (
    echo [INFO] JARVIS no estaba en el inicio de Windows.
)
pause
exit /b

:run_install
:: Ya somos admin — establecer directorio de trabajo a la raíz del proyecto
cd /d "%~dp0.."

:: 1. Comprobar si existe el Python del entorno virtual local primero (validando pyvenv.cfg)
if exist ".venv\Scripts\python.exe" if exist ".venv\pyvenv.cfg" (
    ".venv\Scripts\python.exe" "install\install.py" %1 %2
    exit
)

:: 2. Intentar buscar Python en la ruta estandar de instalacion del usuario (LocalAppData)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" "install\install.py" %1 %2
    exit
)
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    "%LocalAppData%\Programs\Python\Python313\python.exe" "install\install.py" %1 %2
    exit
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    "%LocalAppData%\Programs\Python\Python311\python.exe" "install\install.py" %1 %2
    exit
)

:: 3. Intentar con el Python global del sistema (si esta en el PATH)
where python >nul 2>&1
if %errorlevel% equ 0 (
    python "install\install.py" %1 %2
    exit
)

:: 4. Intentar en Program Files por si acaso
if exist "%ProgramFiles%\Python312\python.exe" (
    "%ProgramFiles%\Python312\python.exe" "install\install.py" %1 %2
    exit
)
if exist "%ProgramFiles%\Python313\python.exe" (
    "%ProgramFiles%\Python313\python.exe" "install\install.py" %1 %2
    exit
)

echo.
echo =======================================================================
echo [ERROR] No se pudo encontrar una instalacion de Python valida.
echo =======================================================================
echo.
echo Por favor, instala Python 3.12 o 3.13 y asegurate de marcar la opcion
echo "Add Python to PATH" durante la instalacion.
echo.
if not "%1"=="--install" pause
exit
