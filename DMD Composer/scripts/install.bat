@echo off
REM ============================================================
REM  DMD COMPOSER - instalacion (Windows 10, Python 3.12)
REM  Crea el venv local e instala SOLO las dependencias web
REM  (fastapi + uvicorn, las mismas de DMD STUDIO). Los motores
REM  DMD son 100%% libreria estandar y no se tocan.
REM ============================================================
setlocal
cd /d "%~dp0..\.."

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python no esta en el PATH. Instala Python 3.12 de python.org.
  pause & exit /b 1
)

python --version
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creando entorno virtual .venv ...
  python -m venv .venv
)
echo [2/3] Actualizando pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
echo [3/3] Instalando dependencias web (fastapi + uvicorn) ...
".venv\Scripts\python.exe" -m pip install fastapi==0.115.6 uvicorn==0.34.0 --quiet

echo.
echo Instalacion completada.
echo Siguiente paso: scripts\check.bat  (verifica el DMD real y las capacidades)
pause
