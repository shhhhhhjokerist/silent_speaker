@echo off
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

echo ================================================
echo   TTS Virtual Mic - Build exe
echo ================================================
echo.

REM ========== Specify Python path ==========
set "PYTHON_EXE=C:\Users\shhhhhh\AppData\Local\Programs\Python\Python39\python.exe"
set "PIP_EXE=C:\Users\shhhhhh\AppData\Local\Programs\Python\Python39\Scripts\pip.exe"
set "PYINSTALLER_EXE=C:\Users\shhhhhh\AppData\Local\Programs\Python\Python39\Scripts\pyinstaller.exe"

echo [INFO] Using Python: %PYTHON_EXE%
%PYTHON_EXE% --version
echo.

echo [1/3] Installing dependencies...
%PYTHON_EXE% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Dependency install failed
    pause
    exit /b 1
)

echo.
echo [2/3] Building tts_mic_gui.exe (GUI version)...

%PYINSTALLER_EXE% --noconfirm --onefile --windowed --name tts_mic_gui ^
    --hidden-import=miniaudio ^
    --hidden-import=sounddevice ^
    --hidden-import=pyttsx3 ^
    --hidden-import=edge_tts ^
    --hidden-import=gtts ^
    --hidden-import=pydub ^
    --hidden-import=numpy ^
    --hidden-import=tkinter ^
    --hidden-import=asyncio ^
    --hidden-import=aiohttp ^
    --hidden-import=requests ^
    --hidden-import=json ^
    --hidden-import=typing ^
    --add-data "config.json;." ^
    --collect-all=edge_tts ^
    --collect-all=miniaudio ^
    --collect-all=sounddevice ^
    tts_mic_gui.py

if errorlevel 1 (
    echo [ERROR] Build failed for GUI version
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Build complete!
echo   Output: dist\tts_mic_gui.exe
echo ================================================
echo.
echo Tips:
echo   - Copy dist\tts_mic_gui.exe to any location
echo   - Keep config.json in the same folder
echo   - Install VB-Cable first: https://vb-audio.com/Cable/
echo.
pause