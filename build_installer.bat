@echo off
REM ============================================================
REM  Himaya — ONE-CLICK ALL-IN-ONE INSTALLER BUILD
REM
REM  Produces:  installer\output\Himaya-Setup-1.0.0.exe
REM             (app + Python runtime + OCR engine, everything
REM              bundled — install = Suivant, Suivant, Terminé)
REM
REM  Steps:  1) venv   2) pip   3) PyInstaller (portable exe)
REM          4) stage Tesseract OCR bundle   5) Inno Setup
REM
REM  Prerequisite: Inno Setup 6+ (free) https://jrsoftware.org/isdl.php
REM  Optional at build time (one-time internet): Tesseract, staged
REM  automatically if not installed locally.
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
    echo   1. Install Inno Setup 6 ^(free^): https://jrsoftware.org/isdl.php
    echo   2. Re-run this script, or pass the path:
    echo      build_installer.bat "C:\Program Files ^(x86^)\Inno Setup 6\ISCC.exe"
    echo.
    pause
    exit /b 1
)
echo Inno Setup found: %ISCC%

REM ---- 1/5 venv -------------------------------------------------------------
if not exist .venv\Scripts\python.exe (
    echo [1/5] Creating virtual environment...
    python -m venv .venv || goto :err
) else (
    echo [1/5] Virtual environment already exists.
)
call .venv\Scripts\activate.bat || goto :err

REM ---- 2/5 dependencies -------------------------------------------------------
echo [2/5] Installing dependencies...
python -m pip install --upgrade pip -q || goto :err
pip install -r requirements.txt pyinstaller -q || goto :err

REM ---- 3/5 portable build (dist\Himaya\Himaya.exe) -----------------------------
echo [3/5] Building Himaya.exe with PyInstaller...
pyinstaller --noconfirm himaya.spec || goto :err

REM ---- 4/5 stage Tesseract OCR bundle -------------------------------------------
set "BUNDLE=installer\bundle\tesseract"
echo [4/5] Staging Tesseract OCR (fra+eng)...
if exist "%BUNDLE%\tesseract.exe" (
    echo        OCR bundle already staged.
    goto :ocr_done
)
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo        Copying from local Tesseract installation...
    robocopy "C:\Program Files\Tesseract-OCR" "%BUNDLE%" /E /NFL /NDL /NJH /NJS /NP >nul
    if errorlevel 8 goto :err
    call :prune_tessdata
    goto :ocr_done
)
echo        Tesseract not found locally - downloading ^(build PC only, one time^)...
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.0.20221219/tesseract-ocr-w64-setup-v5.3.0.20221219.exe' -OutFile \"$env:TEMP\tess-setup.exe\" -UseBasicParsing}catch{exit 1}"
if errorlevel 1 (
    echo        WARNING: download failed - installer will ship WITHOUT bundled OCR.
    echo        Himaya still works ^(hash + metadata + pixel forensics^);
    echo        install Tesseract later and set its path in Settings.
    goto :ocr_done
)
"%TEMP%\tess-setup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /DIR="%CD%\%BUNDLE%"
call :prune_tessdata
:ocr_done
if exist "%BUNDLE%\tesseract.exe" (echo        OCR bundle OK.) else (echo        OCR bundle: NONE.)

REM ---- 5/5 installer (setup.exe) ------------------------------------------------
echo [5/5] Compiling installer with Inno Setup...
if not exist installer\output mkdir installer\output
"%ISCC%" "installer\himaya.iss" || goto :err

echo.
echo ============================================================
echo   DONE:  installer\output\Himaya-Setup-1.0.0.exe
echo.
echo   One file. Double-click on any Windows 10/11 PC:
echo   Suivant -^> Suivant -^> Terminer. Everything is included
echo   ^(app + Python + OCR^). No internet, no prerequisites.
echo.
echo   Silent:  Himaya-Setup-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES
echo ============================================================
pause
exit /b 0

:prune_tessdata
REM keep only eng+fra(+osd) traineddata, add fra if missing
powershell -NoProfile -Command "Get-ChildItem '%BUNDLE%\tessdata\*.traineddata' -Exclude eng.traineddata,fra.traineddata,osd.traineddata -ErrorAction SilentlyContinue | Remove-Item -Force"
if not exist "%BUNDLE%\tessdata\fra.traineddata" powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/fra.traineddata' -OutFile '%BUNDLE%\tessdata\fra.traineddata' -UseBasicParsing}catch{exit 0}"
goto :eof

:err
echo BUILD FAILED - see messages above.
pause
exit /b 1
