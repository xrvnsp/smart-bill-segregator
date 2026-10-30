@echo off
setlocal enabledelayedexpansion
title Sync Files to Smart Bill Segregator
color 0A

:: Target Project Directory
set "TARGET_DIR=H:\SP\My Projects\Smart Bill Segregator"

:: Source Directory is wherever this .bat file is executed from
set "SOURCE_DIR=%~dp0"
if "%SOURCE_DIR:~-1%"=="\" set "SOURCE_DIR=%SOURCE_DIR:~0,-1%"

echo ======================================================================
echo   Smart Bill Segregator - Project Updater & File Syncer
echo ======================================================================
echo.
echo   Source Folder : "%SOURCE_DIR%"
echo   Target Folder : "%TARGET_DIR%"
echo.

:: 1. Validate Target Drive Existence
for /f "tokens=1 delims=:" %%D in ("%TARGET_DIR%") do set "DRIVE_LETTER=%%D:"
if not exist "%DRIVE_LETTER%\" (
    color 0C
    echo [ERROR] Drive %DRIVE_LETTER% is not accessible or not connected.
    echo Please make sure drive %DRIVE_LETTER% is connected and accessible in File Explorer.
    echo.
    pause
    exit /b 1
)

:: 2. Ensure Target Directory Exists
if not exist "%TARGET_DIR%" (
    echo Target folder does not exist. Creating "%TARGET_DIR%"...
    mkdir "%TARGET_DIR%" 2>nul
)

echo Synchronizing and replacing all project files...
echo.

:: 3. Execute Robocopy (mirrors/overwrites existing files and copies all subdirectories)
:: /E  : Copy subdirectories, including empty ones
:: /IS : Include same files (ensures total replacement)
:: /IT : Include tweaked files
:: /R:2: Retry 2 times on locked files
:: /W:1: Wait 1 second between retries
:: /NFL /NDL : Clean scannable progress
robocopy "%SOURCE_DIR%" "%TARGET_DIR%" /E /IS /IT /R:2 /W:1

:: Robocopy exit code 0-7 means successful copy
if %ERRORLEVEL% LEQ 7 (
    echo.
    echo ======================================================================
    echo   SUCCESS! All project files have been copied and updated in:
    echo   "%TARGET_DIR%"
    echo ======================================================================
) else (
    echo.
    echo [NOTICE] Robocopy exited with code %ERRORLEVEL%. Running fallback xcopy...
    xcopy "%SOURCE_DIR%\*" "%TARGET_DIR%\" /E /H /Y /C /R /Q
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ======================================================================
        echo   SUCCESS! All files copied successfully via xcopy.
        echo ======================================================================
    ) else (
        color 0C
        echo.
        echo [ERROR] Copy failed. Please ensure files in the target directory are closed.
    )
)

echo.
echo You can now run the app from:
echo   "%TARGET_DIR%\run_streamlit.bat"
echo.
pause
