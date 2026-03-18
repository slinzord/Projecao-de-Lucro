@echo off
title Projeção Lucro - Frontend
cd /d "%~dp0frontend"
echo Instalando dependencias (primeira vez pode demorar)...
call npm install
echo.
echo Frontend iniciando em http://localhost:5173
echo.
call npx vite
pause
