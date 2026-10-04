@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "HASH_SCRIPT=%SCRIPT_DIR%..\src\pygpt_net\core\extensions\integrity.py"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%HASH_SCRIPT%" %*
) else (
    python "%HASH_SCRIPT%" %*
)
exit /b %ERRORLEVEL%
