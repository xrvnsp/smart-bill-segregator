@echo off
setlocal enabledelayedexpansion
title Push to GitHub - Smart Bill Segregator
color 0A

echo ======================================================================
echo   Smart Bill Segregator - Git Deployment & Sync
echo   Repository: https://github.com/xrvnsp/smart-bill-segregator
echo ======================================================================
echo.

:: 1. Verify Git Installation
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERROR] Git is not installed or not in your Windows PATH.
    echo Please install Git for Windows from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

:: 2. Ensure Git Repository is Initialized
if not exist ".git" (
    echo [INFO] Initializing new Git repository...
    git init
    echo.
)

:: 3. Double-check .gitignore Safety Protection
if not exist ".gitignore" (
    echo [WARNING] .gitignore not found. Creating safety .gitignore...
    (
        echo passwords.json
        echo emi_names.json
        echo *.env
        echo *.pdf
        echo Statements_*/
        echo temp_uploaded_statements/
        echo test_*/
        echo *.csv
        echo __pycache__/
        echo *.py[cod]
        echo .venv/
        echo venv/
    ) > .gitignore
)

:: 4. Prompt for Commit Message or Use Descriptive Default
echo.
set "COMMIT_MSG=Update Smart Bill Segregator: Apple Design System, card facia graphics, multi-bank Streamlit app & sync tools"
set /p "USER_MSG=Enter commit message (Press ENTER for default): "
if defined USER_MSG (
    if not "!USER_MSG!"=="" set "COMMIT_MSG=!USER_MSG!"
)

:: 5. Stage Files and Verify Safety
echo.
echo [1/4] Staging project files...
git add .

:: Safety check: ensure passwords.json is untracked
git status --porcelain | findstr /I "passwords.json" >nul
if %ERRORLEVEL% equ 0 (
    echo [SAFETY] Unstaging passwords.json to protect your credentials...
    git reset HEAD passwords.json >nul 2>&1
    git rm --cached passwords.json >nul 2>&1
)

:: 6. Commit Changes
echo [2/4] Committing updates: "!COMMIT_MSG!"...
git commit -m "!COMMIT_MSG!"
if %ERRORLEVEL% neq 0 (
    echo [NOTE] No new changes to commit. Proceeding to push...
)

:: 7. Configure Remote and Branch
echo [3/4] Configuring remote branch 'main'...
git branch -M main
git remote add origin https://github.com/xrvnsp/smart-bill-segregator.git 2>nul
git remote set-url origin https://github.com/xrvnsp/smart-bill-segregator.git

:: 8. Push to GitHub
echo [4/4] Pushing to GitHub (https://github.com/xrvnsp/smart-bill-segregator)...
echo.
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo   SUCCESS! Pushed latest changes to:
    echo   https://github.com/xrvnsp/smart-bill-segregator
    echo ======================================================================
) else (
    echo.
    echo [NOTICE] Push encountered a conflict or remote update.
    echo Attempting 'git pull --rebase origin main' and retrying push...
    git pull --rebase origin main
    git push -u origin main
    if %ERRORLEVEL% equ 0 (
        echo.
        echo ======================================================================
        echo   SUCCESS! Synced and pushed to GitHub.
        echo ======================================================================
    ) else (
        color 0C
        echo.
        echo [ERROR] Push failed. If this is a private repo, ensure you are authenticated:
        echo   Run: git credential-manager or gh auth login
    )
)

echo.
pause
