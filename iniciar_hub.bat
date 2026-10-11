@echo off
title DuoHub - English Mastery System
cd /d "%~dp0"

echo =======================================================
echo        DUOHUB - ENGLISH MASTERY SYSTEM
echo =======================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [*] Configurando entorno virtual por primera vez...
    python -m venv venv
    call .\venv\Scripts\activate.bat
    pip install -r requirements.txt
)

echo [*] Verificando base de datos...
.\venv\Scripts\python.exe database.py

echo.
echo [*] Iniciando servidor local en http://127.0.0.1:5005 ...
echo [*] Abriendo tu navegador predeterminado...
echo [*] Para detener el servidor, simplemente cierra esta ventana o presiona Ctrl + C.
echo =======================================================
echo.

:: Abre el navegador tras 2 segundos en segundo plano
start /b cmd /c "ping 127.0.0.1 -n 3 >nul & start http://127.0.0.1:5005"

:: Inicia Flask con el entorno virtual del proyecto
.\venv\Scripts\python.exe app.py

if errorlevel 1 (
    echo.
    echo Ocurrio un error al ejecutar el servidor.
    pause
)
