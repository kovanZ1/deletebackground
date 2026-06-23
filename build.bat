@echo off
REM CaseCutoutTool - Windows build script. ASCII only by design.
setlocal enabledelayedexpansion

echo [1/4] Creating virtual environment...
python -m venv .venv
if errorlevel 1 goto :err

echo [2/4] Activating and upgrading pip...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [3/4] Installing dependencies + PyInstaller...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :err

echo [4/4] Building EXE...
pyinstaller --noconfirm casecut.spec
if errorlevel 1 goto :err

echo.
echo BUILD OK. Run: dist\CaseCutoutTool\CaseCutoutTool.exe
goto :end

:err
echo.
echo BUILD FAILED. See messages above.

:end
endlocal
pause
