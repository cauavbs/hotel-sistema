@echo off
rem Inicia o sistema do hotel no Windows. De dois cliques neste arquivo.
cd /d "%~dp0"
title Sistema do Hotel

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao foi encontrado. Instale em python.org/downloads e marque "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Criando o ambiente virtual ^(so na primeira vez^)...
    python -m venv venv
    if errorlevel 1 ( echo Falha ao criar o ambiente virtual. & pause & exit /b 1 )
    set PRIMEIRA=1
)
call "venv\Scripts\activate.bat"

if defined PRIMEIRA (
    echo Instalando as dependencias ^(so na primeira vez, pode demorar^)...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 ( echo Falha ao instalar as dependencias. & pause & exit /b 1 )
)

echo.
echo === Diagnostico ===
python diagnostico.py
if errorlevel 1 (
    echo.
    echo O sistema nao foi aberto porque o diagnostico encontrou problema^(s^). Leia as linhas [FALHA] acima.
    echo Se precisar de ajuda, envie uma foto desta tela.
    pause
    exit /b 1
)

echo.
echo Abrindo o sistema em http://localhost:5000  ^(para parar, feche esta janela ou aperte Ctrl+C^)
start "" "http://localhost:5000/login"
python app.py
pause
