@echo off
REM ============================================================
REM  Himaya — ONE-CLICK INSTALLER BUILD
REM
REM  Produces:  installer\output\Himaya-Setup-1.0.0.exe
REM  Steps:     1) venv   2) pip install   3) PyInstaller
REM             4) Inno Setup (ISCC.exe)  -> single setup.exe
REM
REM  Prerequisite: Inno Setup 6+ (free) https://jrsoftware.org/isinfo.php
REM  (the script auto-detects it; or pass the path: build_installer.bat "C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "ISCC=%~1"

REM ---- locate Inno Setup compiler -----------------------------------------
if "%ISCC%"=="" (
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if "%ISCC%"=="" (
    if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)
if "%ISCC%"=="" (
    for /f "delims=" %%i in ('where ISCC.exe 2^>nul') do set "ISCC=%%i"
)
if "%ISCC%"=="" (
    echo.
    echo [ERROR] Inno Setup compiler not found.
    echo.
    echo   1. Install Inno Setup 6 (free): https://jrsoftware.org/isdl.php
    echo   2. Re-run this script, or pass the path:
    echo      build_installer.bat "C:\Program Files ^(x86^)\Inno Setup 6\ISCC.exe"
    echo.
    pause
    exit /b 1
)
echo Inno Setup found: %ISCC%

REM ---- 1/4 venv -------------------------------------------------------------
if not exist .venv\Scripts\python.exe (
    echo [1/4] Creating virtual environment...
    python -m venv .venv || goto :err
) else (
    echo [1/4] Virtual environment already exists.
)
call .venv\Scripts\activate.bat || goto :err

REM ---- 2/4 dependencies -------------------------------------------------------
echo [2/4] Installing dependencies...
python -m pip install --upgrade pip -q || goto :err
pip install -r requirements.txt pyinstaller -q || goto :err

REM ---- 3/4 portable build (dist\Himaya\Himaya.exe) -----------------------------
echo [3/4] Building Himaya.exe with PyInstaller...
pyinstaller --noconfirm himaya.spec || goto :err

REM ---- 4/4 installer (setup.exe) ------------------------------------------------
echo [4/4] Compiling installer with Inno Setup...
if not exist installer\output mkdir installer\output
"%ISCC%" "installer\himaya.iss" || goto :err

echo.
echo ============================================================
echo   DONE:  installer\output\Himaya-Setup-1.0.0.exe
echo.
echo   - Double-click it on any Windows 10/11 PC to install.
echo   - Silent install:
echo     Himaya-Setup-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES
echo   - Uninstaller keeps seller data by default (asks first).
echo ============================================================
pause
exit /b 0

:err
echo BUILD FAILED - see messages above.
pause
exit /b 1
