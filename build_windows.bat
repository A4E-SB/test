@echo off
REM ============================================================
REM  Himaya — Windows build script (PyInstaller)
REM  Produces:  dist\Himaya\Himaya.exe   (portable folder)
REM  Add --onefile below if you prefer a single .exe file.
REM ============================================================
setlocal

echo [1/4] Creating virtual environment...
python -m venv .venv || goto :err
call .venv\Scripts\activate.bat || goto :err

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip || goto :err
pip install -r requirements.txt pyinstaller || goto :err

echo [3/4] Building Himaya.exe...
pyinstaller --noconfirm himaya.spec || goto :err

echo [4/4] Done.
echo.
echo    Executable : dist\Himaya\Himaya.exe
echo    Data file  : %%APPDATA%%\Himaya\himaya.db
echo.
echo    NOTE: install Tesseract-OCR on the target PC for the full
echo    OCR analysis (see README.md). The app works without it,
echo    using hash + metadata + pixel forensics only.
pause
exit /b 0

:err
echo BUILD FAILED - see messages above.
pause
exit /b 1
