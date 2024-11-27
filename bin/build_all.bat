@echo off

REM Set variables
SET CurrentDir=%CD%
SET SIGNTOOL=C:\Program Files (x86)\Microsoft SDKs\ClickOnce\SignTool

REM Build app
call build.bat

cd "%CurrentDir%"

"%SIGNTOOL%\signtool.exe" sign /t http://time.certum.pl "%CD%\..\dist\Windows\pygpt.exe"

REM Create installer
call build_installer.bat
"%SIGNTOOL%\signtool.exe" sign /t http://time.certum.pl "%CD%\..\dist\pygpt-%ProductVersion%.msi"
