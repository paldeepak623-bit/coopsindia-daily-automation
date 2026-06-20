@echo off
cd /d "%~dp0"
echo CoopsIndia - Login + Excel Download + Logout
echo ============================================
echo IMPORTANT: Chrome sirf logout ke baad band hoga.
echo ============================================
pip install -q -r requirements.txt 2>nul
python coops_login.py
pause
