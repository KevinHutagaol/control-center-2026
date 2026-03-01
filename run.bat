@echo off
setlocal enabledelayedexpansion

set "VENV_DIR=.venv"
set "MAIN_SCRIPT=-m pages.Home.main"
set "UI_COMPILER=utils/compileUIFiles.py"
set "REQUIREMENTS=requirements.txt"
set "TARGET_PY_VER=3.11"

echo [INFO] Checking for Python %TARGET_PY_VER%...

py -%TARGET_PY_VER% --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -%TARGET_PY_VER%"
    goto :FOUND_PYTHON
)

python --version 2>&1 | findstr "3.11" >nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :FOUND_PYTHON
)

cls
echo ========================================================
echo [ERROR] Python %TARGET_PY_VER% is missing!
echo ========================================================
echo This application requires specifically Python 3.11.
echo.
echo Please download and install it from:
echo https://www.python.org/downloads/release/python-3119/
echo.
echo IMPORTANT: During installation, check the box that says:
echo "Add Python.exe to PATH"
echo ========================================================
pause
exit /b

:FOUND_PYTHON
echo [INFO] Found Python: !PY_CMD!

:: --- CHECKS ---
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed. Please install Git for Windows.
    pause
    exit /b
)

:: --- VENV ---
if not exist "%VENV_DIR%" (
    echo [INFO] Creating Python Virtual Environment using !PY_CMD!...
    !PY_CMD! -m venv "%VENV_DIR%"
)


call "%VENV_DIR%\Scripts\activate.bat"

:: --- UPDATE ---
set UPDATED=0

if exist ".dev_mode" (
    echo [WARN] '.dev_mode' file detected.
    echo [WARN] Skipping Git Update/Reset to protect local changes.
) else (
    echo [INFO] Checking for updates...

    for /f %%i in ('git rev-parse HEAD') do set PREV_HEAD=%%i

    git fetch origin
    git reset --hard origin/main
    git pull

    for /f %%i in ('git rev-parse HEAD') do set NEW_HEAD=%%i

    if "!PREV_HEAD!" neq "!NEW_HEAD!" (
        echo [INFO] Update detected!
        set UPDATED=1
    ) else (
        echo [INFO] Already up to date.
    )
)

:: --- BUILD ---
set "FIRST_RUN=0"
if not exist ".setup_complete" set "FIRST_RUN=1"

if "!UPDATED!"=="1" (
    set "DO_BUILD=1"
) else (
    if "!FIRST_RUN!"=="1" (
        set "DO_BUILD=1"
    ) else (
        set "DO_BUILD=0"
    )
)

if "!DO_BUILD!"=="1" (
    echo [INFO] Installing/Updating dependencies...
    pip install -r "%REQUIREMENTS%"

    echo [INFO] Compiling UI files...
    python "%UI_COMPILER%"
)

if "!FIRST_RUN!"=="1" (
    echo [INFO] First run detected. Creating shortcuts...
    python "utils\createShortcuts.py"

    echo Setup Complete > ".setup_complete"
)

if "!UPDATED!"=="1" (
    echo [INFO] Installing/Updating dependencies...
    pip install -r "%REQUIREMENTS%"

    echo [INFO] Compiling UI files...
    python "%UI_COMPILER%"
)

:: --- LAUNCH ---
echo [INFO] Starting Application...
echo python %MAIN_SCRIPT%
python %MAIN_SCRIPT%

if %errorlevel% neq 0 pause