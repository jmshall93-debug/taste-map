@echo off
title Taste Map
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual env missing. Run: py -m venv .venv
    echo Then: .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo  Taste Map  ^>  http://localhost:8501
echo  Close this window to stop the app.
echo.

.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.headless false

pause
