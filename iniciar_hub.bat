@echo off
title DuoHub - English Mastery System
cd /d "%~dp0"

echo ===================================================
echo     DUOHUB - ENGLISH MASTERY & TRAINING SYSTEM
echo ===================================================
echo.

if not exist "venv" (
    echo [*] Creando entorno virtual (venv)...
    python -m venv venv
)

echo [*] Activando entorno virtual...
call venv\Scripts\activate

echo [*] Verificando dependencias...
pip install -r requirements.txt --quiet

echo [*] Inicializando base de datos...
python database.py

echo [*] Abriendo DuoHub en tu navegador...
start http://localhost:5000

echo [*] Servidor iniciado en http://localhost:5000
echo [*] Presiona CTRL+C para detener el servidor.
echo.
python app.py
pause
