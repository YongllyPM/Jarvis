@echo off
title Liberar Instancias de JARVIS
echo.
echo ============================================================
echo   LIBERAR INSTANCIAS DE JARVIS - RESET DE PROCESOS HUNG
echo ============================================================
echo.
echo Este script cerrara solo los procesos de JARVIS (main.py).
echo Procesos Python de otras aplicaciones NO seran afectados.
echo.
echo Presione una tecla para continuar...
pause > nul
echo.
powershell -Command ^
    "Get-CimInstance Win32_Process -Filter 'Name=\"python.exe\" OR Name=\"pythonw.exe\"' ^
    | Where-Object CommandLine -like '*main.py*' ^
    | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host \"  Cerrado PID $($_.ProcessId): $($_.CommandLine)\" }"
echo.
if %errorlevel% equ 0 (
    echo ============================================================
    echo   PROCESOS DE JARVIS DEPURADOS CON EXITO.
    echo ============================================================
) else (
    echo No se encontraron procesos de JARVIS en ejecucion.
)
echo.
pause
