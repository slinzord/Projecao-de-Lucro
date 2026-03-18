@echo off
title Projeção Lucro - Backend
cd /d "%~dp0backend"
echo Verificando dependencias...
venv\Scripts\python.exe -m pip install -q -r requirements.txt
echo Backend iniciando em http://localhost:8000
echo.
venv\Scripts\python.exe -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
pause
