@echo off
REM ============================================================
REM  DMD STUDIO - Arranque (Windows 10)
REM  Servidor local SOLO en 127.0.0.1. Abre el navegador solo.
REM ============================================================
setlocal
cd /d "%~dp0..\.."

if not exist ".venv-studio\Scripts\python.exe" (
  echo No existe el entorno virtual. Ejecuta primero scripts\windows\install_studio.bat
  pause & exit /b 1
)

".venv-studio\Scripts\python.exe" -m studio
if errorlevel 1 pause
