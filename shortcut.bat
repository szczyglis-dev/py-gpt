:: This script is used to run the app using the virtual environment
@echo off
cd /d "%~dp0" 
call venv\Scripts\activate
call python run.py %*