@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

REM https://github.com/wixtoolset/wix3/releases/tag/wix3141rtm

REM Set variables
SET SourceDir=%CD%\..\dist\Windows
SET InstallerOutputFolder=%CD%\..\dist
SET ProductVersion=2.9.1
SET ProductUpgradeCode=3FCD39F6-4965-4B51-A185-FC6E53CA431B
SET WIX=C:\Program Files (x86)\WiX Toolset v3.14
SET SIGNTOOL=C:\Program Files (x86)\Microsoft SDKs\ClickOnce\SignTool

REM Keep large WiX temporary cabinets and validation copies on the build drive.
SET "TEMP=%CD%\..\build\wix-temp"
SET "TMP=%TEMP%"
if not exist "%TEMP%" mkdir "%TEMP%"
if errorlevel 1 goto :failed

REM Build the installer for download
IF EXIST "%SourceDir%\_internal\.ms_store" (
    del "%SourceDir%\_internal\.ms_store"
)

REM 1. Generate the components file using heat.exe
"%WIX%\bin\heat.exe" dir "%SourceDir%" -ag -sfrag -srd -sreg -scom -var var.SourceDir -dr INSTALLDIR -cg PYGPTFiles -out PYGPTFiles.wxs
if errorlevel 1 goto :failed

REM 2. Compile
"%WIX%\bin\candle.exe" ^
  -ext "%WIX%\bin\WixUIExtension.dll" ^
  -ext "%WIX%\bin\WixUtilExtension.dll" ^
  -dSourceDir="%SourceDir%" ^
  -dProductVersion="%ProductVersion%" ^
  Product.wxs PYGPTFiles.wxs
if errorlevel 1 goto :failed

REM 3. Link
REM Harvested files use file key paths in AppData, without per-file registry markers or directory cleanup.
"%WIX%\bin\light.exe" ^
  -sice:ICE38 -sice:ICE64 ^
  -ext "%WIX%\bin\WixUIExtension.dll" ^
  -ext "%WIX%\bin\WixUtilExtension.dll" ^
  -dSourceDir="%SourceDir%" ^
  -dProductVersion="%ProductVersion%" ^
  Product.wixobj PYGPTFiles.wixobj ^
  -o "%InstallerOutputFolder%\pygpt-%ProductVersion%.msi"
if errorlevel 1 goto :failed

echo Installer (download) has been built successfully.
popd
exit /b 0

:failed
echo Installer build failed.
popd
exit /b 1
