@echo off
REM ============================================================
REM  DMD COMPOSER - verificacion del sistema
REM  1) Comprueba Python y dependencias.
REM  2) Descubre el DMD real (ruta configurada o carpetas vecinas).
REM  3) Ejecuta la introspeccion y una validacion real de control.
REM ============================================================
setlocal
cd /d "%~dp0..\.."

if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)

echo ============================================================
echo  DMD COMPOSER - CHECK
echo ============================================================
%PY% --version
%PY% -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
  echo [FALTA] fastapi/uvicorn: ejecuta scripts\install.bat primero.
  pause & exit /b 1
)

echo.
echo --- Capacidades e integracion con el DMD real ---
%PY% -c "import sys; sys.path.insert(0, '.'); from composer import bridge, manifest, store; import json; m = manifest.get_manifest(bridge.discover_dmd(store.DATA_DIR, (store.DATA_DIR / 'composer_config.json').exists() and json.loads((store.DATA_DIR / 'composer_config.json').read_text(encoding='utf-8')).get('dmd_path') or None), store.DATA_DIR, refresh=True); print('origen manifiesto:', m.get('origen')); print('fingerprint:', manifest.fingerprint_of(m)); print('instrumentos:', ', '.join(m['catalogos']['instruments'])); print('tipos de seccion:', ', '.join(m['catalogos']['section_types'])); print('identidades con receta N1:', ', '.join(m['recetas'].keys())); print('perfiles de produccion:', ', '.join(m['perfiles']['nombres']))"

if errorlevel 1 (
  echo.
  echo [AVISO] No se pudo hablar con el DMD real. Composer puede arrancar con la
  echo instantanea incluida (manifests/dmd_manifest_builtin.json), pero para
  echo validar/compilar en vivo configura la ruta: crea composer_data\composer_config.json
  echo con {"dmd_path": "C:\\Users\\Homeless\\Documents\\Midi\\nucleo_engine_project"}
  pause & exit /b 1
)

echo.
echo CHECK OK. Arranca con scripts\start.bat
pause
