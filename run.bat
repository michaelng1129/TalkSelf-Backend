@echo off
set /p host=Input the host....（default: 127.0.0.1）: 
set host=%host: =%
if "%host%"=="" set host=127.0.0.1

set /p port=Input the port...（default: 8000）: 
set port=%port: =%
if "%port%"=="" set port=8000

python -m uvicorn main:app --host %host% --port %port% --reload
