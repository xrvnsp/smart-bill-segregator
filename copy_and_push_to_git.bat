@echo off
setlocal enabledelayedexpansion
title Copy Files & Push to GitHub - Smart Bill Segregator
color 0A

:: Target Project Directory on Drive H:
set "TARGET_DIR=H:\SP\My Projects\Smart Bill Segregator"

:: Source Directory is wherever this .bat file is executed from (e.g. Downloads or staging folder)
set "SOURCE_DIR=%~dp0"
if "%SOURCE_DIR:~-1%"=="\" set "SOURCE_DIR=%SOURCE_DIR:~0,-1%"

echo ======================================================================
echo   Smart Bill Segregator - One-Click Sync & Git Deployment
echo ======================================================================
echo.
echo   [Source]  "%SOURCE_DIR%"
echo   [Target]  "%TARGET_DIR%"
echo.

:: ----------------------------------------------------------------------
:: STEP 1: Validate Target Drive Existence (Drive H:)
:: ----------------------------------------------------------------------
for /f "tokens=1 delims=:" %%D in ("%TARGET_DIR%") do set "DRIVE_LETTER=%%D:"
if not exist "%DRIVE_LETTER%\" (
    color 0C
    echo [ERROR] Drive %DRIVE_LETTER% is not accessible or not connected.
    echo Please make sure drive %DRIVE_LETTER% is plugged in and accessible in File Explorer.
    echo.
    pause
    exit /b 1
)

:: ----------------------------------------------------------------------
:: STEP 2: Ensure Target Directory Exists
:: ----------------------------------------------------------------------
if not exist "%TARGET_DIR%" (
    echo [INFO] Target folder does not exist. Creating "%TARGET_DIR%"...
    mkdir "%TARGET_DIR%" 2>nul
)

:: ----------------------------------------------------------------------
:: STEP 3: Copy and Replace All Project Files to Target Directory
:: ----------------------------------------------------------------------
echo [1/3] Copying and replacing all files to "%TARGET_DIR%"...
echo.

:: Use Robocopy to copy all files and subdirectories, replacing older/same files
:: /E   : Copy subdirectories, including empty ones
:: /IS  : Include same files (total overwrite)
:: /IT  : Include tweaked files
:: /R:2 : Retry 2 times on file lock
:: /W:1 : Wait 1 second between retries
:: /XD .git : Do not overwrite the target's .git repository folder
robocopy "%SOURCE_DIR%" "%TARGET_DIR%" /E /IS /IT /R:2 /W:1 /XD ".git"

if %ERRORLEVEL% LEQ 7 (
    echo.
    echo   [OK] All project files successfully copied to "%TARGET_DIR%".
) else (
    echo.
    echo   [NOTICE] Robocopy code %ERRORLEVEL%. Running fallback xcopy...
    xcopy "%SOURCE_DIR%\*" "%TARGET_DIR%\" /E /H /Y /C /R /Q
    if %ERRORLEVEL% EQU 0 (
        echo   [OK] Files copied successfully via xcopy.
    ) else (
        color 0C
        echo   [ERROR] File copy failed. Please close open files in "%TARGET_DIR%".
        pause
        exit /b 1
    )
)

echo.
echo ======================================================================
echo   STEP 2: Navigating to Target Directory & Pushing to GitHub
echo ======================================================================
echo.

:: ----------------------------------------------------------------------
:: STEP 4: Switch Working Directory to Target Folder on Drive H:
:: ----------------------------------------------------------------------
cd /d "%TARGET_DIR%"
echo   Current Working Directory: %CD%
echo.

:: ----------------------------------------------------------------------
:: STEP 5: Verify Git Installation
:: ----------------------------------------------------------------------
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERROR] Git is not installed or not in your Windows PATH.
    echo Please install Git for Windows from: https://git-scm.com/download/win
    echo All files were copied to "%TARGET_DIR%", but could not be pushed to GitHub.
    echo.
    pause
    exit /b 1
)

:: ----------------------------------------------------------------------
:: STEP 6: Initialize Git in Target Directory if Needed
:: ----------------------------------------------------------------------
if not exist ".git" (
    echo [INFO] Initializing new Git repository in "%TARGET_DIR%"...
    git init
    echo.
)

:: ----------------------------------------------------------------------
:: STEP 7: Security Guard: Ensure .gitignore Blocks Credentials & Hardcoded HTML
:: ----------------------------------------------------------------------
echo [2/3] Checking security guard and credentials protection...

:: Remove any tracked sensitive files from Git cache
git rm --cached passwords.json >nul 2>&1
git rm --cached Statement_Dashboard.html >nul 2>&1

:: Ensure passwords.json is empty template on disk
if exist "passwords.json" (
    findstr /C:"sara" "passwords.json" >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo [SECURITY] Clearing sensitive credentials from passwords.json...
        (
            echo {
            echo   "hdfc": "",
            echo   "icici": ""
            echo }
        ) > passwords.json
    )
)

:: ----------------------------------------------------------------------
:: STEP 8: Prompt for Commit Message or Use Default
:: ----------------------------------------------------------------------
echo.
set "COMMIT_MSG=Update Smart Bill Segregator: Apple Design System, card facia graphics, multi-bank Streamlit app & private session security"
set /p "USER_MSG=Enter commit message (Press ENTER for default): "
if defined USER_MSG (
    if not "!USER_MSG!"=="" set "COMMIT_MSG=!USER_MSG!"
)

:: ----------------------------------------------------------------------
:: STEP 9: Stage, Commit, and Push to GitHub from Target Directory
:: ----------------------------------------------------------------------
echo.
echo [3/3] Staging and pushing to GitHub repository from "%TARGET_DIR%"...
git add .

:: Commit
git commit -m "!COMMIT_MSG!"
if %ERRORLEVEL% neq 0 (
    echo [NOTE] No uncommitted changes detected. Proceeding to push branch...
)

:: Set main branch and remote URL
git branch -M main
git remote add origin https://github.com/xrvnsp/smart-bill-segregator.git 2>nul
git remote set-url origin https://github.com/xrvnsp/smart-bill-segregator.git

:: Push to remote main branch
echo Pushing to origin main...
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo   SUCCESS! Project updated and pushed to GitHub:
    echo   Repository: https://github.com/xrvnsp/smart-bill-segregator
    echo   Live App  : https://smartbills.streamlit.app
    echo ======================================================================
) else (
    echo.
    echo [NOTICE] Push rejected due to remote updates. Attempting rebase...
    git pull --rebase origin main
    git push -u origin main
    if %ERRORLEVEL% equ 0 (
        echo.
        echo ======================================================================
        echo   SUCCESS! Synced and pushed to GitHub.
        echo   Live App: https://smartbills.streamlit.app
        echo ======================================================================
    ) else (
        color 0C
        echo.
        echo [ERROR] Push failed. If authentication is needed, run: gh auth login
    )
)

echo.
echo You can run your local app anytime with:
echo   "%TARGET_DIR%\run_streamlit.bat"
echo.
pause
