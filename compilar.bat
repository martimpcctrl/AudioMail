@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Compilando o AudioMail portatil...
set PY=
py -3 --version >nul 2>nul && set PY=py -3
if "%PY%"=="" python --version >nul 2>nul && set PY=python
if "%PY%"=="" (
  echo Nao encontrei o Python. Instale em python.org e marque "Add Python to PATH".
  pause
  exit /b 1
)
%PY% compilar.py
if errorlevel 1 (
  echo.
  echo A compilacao falhou. Leia a mensagem acima.
  pause
  exit /b 1
)
echo.
echo Tudo certo. A pasta saida_portatil sera aberta.
start "" "%~dp0saida_portatil"
pause
