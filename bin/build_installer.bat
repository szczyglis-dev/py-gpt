@echo off

REM https://github.com/wixtoolset/wix3/releases/tag/wix3141rtm

REM Set variables
SET SourceDir=%CD%\..\dist\Windows
SET InstallerOutputFolder=%CD%\..\dist
SET ProductVersion=2.8.32
SET ProductUpgradeCode=3FCD39F6-4965-4B51-A185-FC6E53CA431B
SET WIX=C:\Program Files (x86)\WiX Toolset v3.14
SET SIGNTOOL=C:\Program Files (x86)\Microsoft SDKs\ClickOnce\SignTool

REM Build the installer for download
IF EXIST "%SourceDir%\_internal\.ms_store" (
    del "%SourceDir%\_internal\.ms_store"
)

REM 1. Generate the components file using heat.exe
"%WIX%\bin\heat.exe" dir "%SourceDir%" -ag -sfrag -srd -sreg -scom -var var.SourceDir -dr INSTALLDIR -cg PYGPTFiles -out PYGPTFiles.wxs

REM 2. Compile
"%WIX%\bin\candle.exe" ^
  -ext "%WIX%\bin\WixUIExtension.dll" ^
  -ext "%WIX%\bin\WixUtilExtension.dll" ^
  -dSourceDir="%SourceDir%" ^
  -dProductVersion="%ProductVersion%" ^
  Product.wxs PYGPTFiles.wxs

REM 3. Link
"%WIX%\bin\light.exe" ^
  -ext "%WIX%\bin\WixUIExtension.dll" ^
  -ext "%WIX%\bin\WixUtilExtension.dll" ^
  -dSourceDir="%SourceDir%" ^
  -dProductVersion="%ProductVersion%" ^
  Product.wixobj PYGPTFiles.wixobj ^
  -o "%InstallerOutputFolder%\pygpt-%ProductVersion%.msi"

echo Installer (download) has been built successfully.


