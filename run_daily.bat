@echo off
cd /d "%~dp0"
echo [%date% %time%] CoopsIndia Daily Job starting...
pip install -q -r requirements.txt 2>nul
python daily_job.py >> logs\scheduler_console.log 2>&1
exit /b %ERRORLEVEL%
