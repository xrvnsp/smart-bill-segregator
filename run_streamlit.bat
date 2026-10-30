@echo off
title Smart Bill Segregator - Streamlit Web App
echo =======================================================
echo   Smart Bill Segregator - Mobile & PC Web App
echo =======================================================
echo.
echo Checking dependencies...
python -c "import streamlit" 2>NUL
if errorlevel 1 (
    echo Installing Streamlit...
    pip install streamlit>=1.35.0
)
echo.
echo Launching Streamlit web application...
echo   - On this PC: http://localhost:8501
echo   - On your Mobile phone: Use the Network URL shown below
echo.
streamlit run app.py
pause
