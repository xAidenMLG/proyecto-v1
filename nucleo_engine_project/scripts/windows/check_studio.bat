@echo off
REM ============================================================
REM  DMD STUDIO - Verificacion del entorno (Windows 10)
REM  Comprueba versiones, dependencias, motores y audio WAV.
REM ============================================================
setlocal
cd /d "%~dp0..\.."

echo === DMD STUDIO: verificacion de entorno ===
echo.

if not exist ".venv-studio\Scripts\python.exe" (
  echo [X] No existe .venv-studio. Ejecuta scripts\windows\install_studio.bat
  pause & exit /b 1
)
set PY=.venv-studio\Scripts\python.exe

echo [1/4] Python del venv:
%PY% --version

echo.
echo [2/4] Dependencias del servidor:
%PY% -c "import fastapi, uvicorn; print('  fastapi', fastapi.__version__, '/ uvicorn', uvicorn.__version__)"
if errorlevel 1 ( echo [X] Falta instalar dependencias: ejecuta install_studio.bat & pause & exit /b 1 )

echo.
echo [3/4] Motores del proyecto (contrato + compilador + jazz_engine + forge):
%PY% -c "import sys; sys.path.insert(0,'.'); from dark_director import contract; import jazz_engine, forge; print('  ', contract.contract_info()); print('   jazz_engine', jazz_engine.__version__)"
if errorlevel 1 ( echo [X] Los motores no importan: revisa la carpeta del proyecto & pause & exit /b 1 )

echo.
echo [4/4] Audio WAV (FluidSynth + soundfont):
%PY% -c "import sys; sys.path.insert(0,'.'); from studio import capabilities; import json; a=capabilities.audio_status(); print('  fluidsynth:', a.get('fluidsynth')); print('  soundfont:', a.get('soundfont_encontrado')); print('  WAV', 'DISPONIBLE' if a.get('wav_posible') else 'no disponible (solo MIDI)')"

echo.
echo === Si todo aparece marcado arriba, ejecuta scripts\windows\start_studio.bat ===
pause
