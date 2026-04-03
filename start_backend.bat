@echo off
echo Starting Document Scanner Backend Server...
cd /d "%~dp0backend"
call ..\venv\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080