@echo off
REM ============================================================
REM  DMD STUDIO - Instalacion inicial (Windows 10, Python 3.12)
REM  Crea el entorno virtual e instala las dependencias del
REM  servidor local. Los motores no necesitan nada de esto.
REM ============================================================
setlocal
cd /d "%~dp0..\.."

echo.
echo [1/3] Comprobando Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo   ERROR: "python" no esta en el PATH. Instala Python 3.12.x de 64 bits
  echo   desde https://www.python.org/downloads/ marcando "Add python.exe to PATH".
  pause & exit /b 1
)
python --version

echo.
echo [2/3] Creando entorno virtual .venv-studio...
if not exist ".venv-studio\Scripts\python.exe" (
  python -m venv .venv-studio
  if errorlevel 1 ( echo   ERROR creando el venv & pause & exit /b 1 )
) else (
  echo   Ya existe: .venv-studio
)

echo.
echo [3/3] Instalando dependencias del servidor (fastapi + uvicorn)...
".venv-studio\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv-studio\Scripts\python.exe" -m pip install -r requirements-studio.txt
if errorlevel 1 ( echo   ERROR instalando dependencias & pause & exit /b 1 )

echo.
echo ============================================================
echo  Instalacion completada. Usa scripts\windows\START_STUDIO.bat
echo ============================================================
pause
