@echo off

REM Set variables
SET CurrentDir=%CD%
SET SIGNTOOL=C:\Program Files (x86)\Microsoft SDKs\ClickOnce\SignTool

REM Build app
call build.bat

cd "%CurrentDir%"

"%SIGNTOOL%\signtool.exe" sign /t http://time.certum.pl "%CD%\..\dist\Windows\pygpt.exe"

REM Create installer (download)
call build_installer.bat

REM Sign
IF EXIST "%CD%\..\dist\pygpt-%ProductVersion%.msi" (
    echo Installer standalone found, signing...
    "%SIGNTOOL%\signtool.exe" sign /t http://time.certum.pl "%CD%\..\dist\pygpt-%ProductVersion%.msi"
) ELSE (
    echo Installer standalone not found, aborting...
)

REM Create installer (MS Store)
call build_installer_store.bat

REM Sign
IF EXIST "%CD%\..\dist\store\pygpt-%ProductVersion%.msi" (
    echo Installer MS Store found, signing...
    "%SIGNTOOL%\signtool.exe" sign /t http://time.certum.pl "%CD%\..\dist\store\pygpt-%ProductVersion%.msi"
) ELSE (
    echo Installer MS Store not found, aborting...
)