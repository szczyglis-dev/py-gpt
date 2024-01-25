@echo off
cd /d "%~dp0" 
call venv\Scripts\activate
call python run.py %*