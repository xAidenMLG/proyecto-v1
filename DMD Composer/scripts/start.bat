
@echo off
setlocal

title DMD COMPOSER

REM ============================================================
REM DMD COMPOSER - START
REM ============================================================

set "ROOT=C:\Users\Homeless\Documents\PY\DMD_Composer\DMD_Pack\DMD_Composer"
set "PY=%ROOT%\.venv\Scripts\python.exe"

echo.
echo ========================================
echo       DMD COMPOSER - START
echo ========================================
echo.

REM Verificar entorno
if not exist "%PY%" (
    echo ERROR: No se encontro Python del entorno virtual.
    pause
    exit /b 1
)

REM Entrar a la raiz
cd /d "%ROOT%"

REM Verificar modulo
"%PY%" -c "import composer" >nul 2>&1

if errorlevel 1 (
    echo ERROR: El modulo composer no esta disponible.
    echo.
    echo Verifica el entorno virtual y la instalacion.
    pause
    exit /b 1
)

echo Iniciando servidor...
echo.

REM Iniciar servidor
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8898/"

"%PY%" -m composer --port 8898

pause
```