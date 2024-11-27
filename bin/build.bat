REM Set variables
SET BinDir=%CD%
SET BuildDir=%CD%\..\dist\Windows
SET ProjectDir=%CD%\..

REM Build app
cd %ProjectDir%
call venv\Scripts\activate
call pip install -r requirements.txt
call pyinstaller --noconfirm windows.spec

REM Copy ffmpg
copy "%BinDir%\ffmpeg.exe" "%BuildDir%\"
copy "%BinDir%\ffplay.exe" "%BuildDir%\"
copy "%BinDir%\ffprobe.exe" "%BuildDir%\"

