@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\activate" (
    call .venv\Scripts\activate
    echo Virtual environment activated.
) else (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

uvicorn app:app --host 0.0.0.0 --port 8000

echo.
echo Press any key to exit.
pause > nul
