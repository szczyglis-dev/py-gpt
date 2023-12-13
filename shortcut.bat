@echo off
cd /d "%~dp0" 
call venv\Scripts\activate
call python src\pygpt_net\app.py