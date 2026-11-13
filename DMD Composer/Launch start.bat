@echo off
title start
cd /d "%~dp0"

echo ========================================
echo   START LAUNCHER
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: No se encontro el entorno virtual.
    pause
    exit /b 1
)

echo Activando entorno...
call ".venv\Scripts\activate.bat"

echo.
echo Iniciando start...
echo.

cd /d "%~dp0scripts"
call "start.bat"

pause
