@echo off
title Desinstalador de JARVIS AI

:: ── Solicitar permisos de Administrador ──────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Solicitando permisos de administrador...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)

cd /d "%~dp0"

echo =======================================================================
echo            DESINSTALADOR DE JARVIS AI
echo =======================================================================
echo.
echo Esta accion eliminara JARVIS completamente del sistema.
echo.
echo Se eliminara:
echo   - Carpeta .venv (entorno virtual)
echo   - Cache de Python (__pycache__)
echo   - Acceso directo del Escritorio
echo   - Directorio completo de JARVIS (opcional)
echo.
echo Los siguientes archivos se conservaran si eliges "No":
echo   - config/api_keys.json (tus API keys)
echo   - assets/ (personajes, iconos)
echo   - actions/ (modulos)
echo.
set /p resp="¿Deseas continuar? (S/N): "
if /i "%resp%" neq "S" (
    echo.
    echo Saliendo del desinstalador...
    timeout /t 2 >nul
    exit /b
)

echo.
echo =======================================================================
echo  [1] Desinstalacion completa (todo el proyecto)
echo  [2] Solo limpiar entorno virtual y cache
echo  [3] Salir
echo =======================================================================
echo.
set /p opcion="Selecciona una opcion (1-3): "

if "%opcion%"=="1" goto full_clean
if "%opcion%"=="2" goto light_clean
goto end

:light_clean
cls
echo.
echo =======================================================================
echo   LIMPIEZA LIGERA
echo =======================================================================
echo.

:: Eliminar entorno virtual
if exist ".venv" (
    echo [1/3] Eliminando entorno virtual...
    rmdir /s /q ".venv"
    echo [OK] Entorno virtual eliminado.
) else (
    echo [1/3] No hay entorno virtual que eliminar.
)

:: Eliminar caches Python
echo [2/3] Eliminando archivos cache...
del /s /q "*.pyc" 2>nul
del /s /q "*.pyo" 2>nul
for /d /r %%i in (__pycache__) do rmdir /s /q "%%i" 2>nul
echo [OK] Cache eliminado.

:: Eliminar acceso directo del escritorio
echo [3/3] Eliminando acceso directo del Escritorio...
set "lnk=%USERPROFILE%\Desktop\JARVIS AI.lnk"
if exist "%lnk%" (
    del /f /q "%lnk%"
    echo [OK] Acceso directo eliminado.
) else (
    echo [3/3] No se encontro acceso directo en el Escritorio.
)

echo.
echo =======================================================================
echo   LIMPIEZA LIGERA COMPLETADA
echo =======================================================================
echo.
echo Para reinstalar JARVIS, ejecuta "Instalar_JARVIS.bat".
echo.
pause
exit /b

:full_clean
cls
echo.
echo =======================================================================
echo   DESINSTALACION COMPLETA
echo =======================================================================
echo.
echo ADVERTENCIA: Esto eliminara TODO el proyecto JARVIS.
echo Se borraran configuraciones, personajes, modulos y archivos.
echo.

set /p confirm="¿Estas SEGURO? Escribe 'BORRAR' para confirmar: "
if /i "%confirm%" neq "BORRAR" (
    echo Operacion cancelada.
    pause
    exit /b
)

echo.
echo [1/5] Eliminando entorno virtual...
if exist ".venv" (
    rmdir /s /q ".venv"
    echo [OK] Entorno virtual eliminado.
) else (
    echo [OK] No hay entorno virtual.
)

echo [2/5] Eliminando caches de Python...
del /s /q "*.pyc" 2>nul
for /d /r %%i in (__pycache__) do rmdir /s /q "%%i" 2>nul
echo [OK] Cache eliminado.

echo [3/5] Eliminando acceso directo del Escritorio...
set "lnk=%USERPROFILE%\Desktop\JARVIS AI.lnk"
if exist "%lnk%" (
    del /f /q "%lnk%"
    echo [OK] Acceso directo eliminado.
)
set "vbs=%USERPROFILE%\Desktop\JARVIS AI.lnk"
if exist "%vbs%" del /f /q "%vbs%"

:: Eliminar tambien el acceso directo del menu inicio si existe
set "startlnk=%APPDATA%\Microsoft\Windows\Start Menu\Programs\JARVIS AI.lnk"
if exist "%startlnk%" (
    del /f /q "%startlnk%"
    echo [OK] Acceso directo de Inicio eliminado.
)

echo [4/5] Eliminando archivos de configuracion...
if exist "config\api_keys.json" (
    del /f /q "config\api_keys.json"
)
if exist "config\agents.json" (
    del /f /q "config\agents.json"
)
if exist "config\rules.json" (
    del /f /q "config\rules.json"
)
if exist "config" (
    rmdir /s /q "config"
)
echo [OK] Configuracion eliminada.

echo [5/5] Eliminando archivos restantes...
:: Eliminar archivos no esenciales generados por el programa
for %%f in (build dist *.spec jarvis.log) do (
    if exist "%%f" (
        if exist "%%f" (
            if exist "%%f\." (rmdir /s /q "%%f") else (del /f /q "%%f")
        )
    )
)

echo.
echo =======================================================================
echo   DESINSTALACION COMPLETADA
echo =======================================================================
echo.
echo JARVIS ha sido eliminado del sistema.
echo Puedes cerrar esta ventana.
echo.
pause
exit /b

:end
echo Saliendo...
timeout /t 2 >nul
exit /b
