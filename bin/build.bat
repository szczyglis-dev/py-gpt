REM Set variables
SET BinDir=%CD%
SET BuildDir=%CD%\..\dist\Windows
SET ProjectDir=%CD%\..

REM Build app
cd %ProjectDir%
call venv\Scripts\activate
call pip install -r requirements.txt
call pyinstaller --noconfirm windows.spec

REM Copy VC runtime DLLs
copy "%BuildDir%\_internal\msvcp100.dll" "%BuildDir%\"
copy "%BuildDir%\_internal\msvcr100.dll" "%BuildDir%\"
copy "%BuildDir%\_internal\pywin32_system32\pywintypes310.dll" "%BuildDir%\_internal\"
copy "%BuildDir%\_internal\pywin32_system32\pythoncom310.dll" "%BuildDir%\_internal\"
copy "%BuildDir%\_internal\pywin32_system32\pywintypes310.dll" "%BuildDir%\"
copy "%BuildDir%\_internal\pywin32_system32\pythoncom310.dll" "%BuildDir%\"

mkdir "%BuildDir%\_internal\win32\lib"
copy "%BuildDir%\_internal\pywin32_system32\pywintypes310.dll" "%BuildDir%\_internal\win32\"
copy "%BuildDir%\_internal\pywin32_system32\pythoncom310.dll" "%BuildDir%\_internal\win32\"
copy "%BuildDir%\_internal\pywin32_system32\pywintypes310.dll" "%BuildDir%\_internal\win32\lib\"
copy "%BuildDir%\_internal\pywin32_system32\pythoncom310.dll" "%BuildDir%\_internal\win32\lib\"

REM Copy ffmpg
copy "%BinDir%\ffmpeg.exe" "%BuildDir%\"
copy "%BinDir%\ffplay.exe" "%BuildDir%\"
copy "%BinDir%\ffprobe.exe" "%BuildDir%\"

