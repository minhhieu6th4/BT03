@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================================
echo     KHOI DONG BACKEND API UET ALGORITHM BATTLE
echo ===================================================
echo Thu muc lam viec: %CD%
echo.

echo Dang khoi dong Backend API Server tren cong 5000...
echo - Backend API:            http://127.0.0.1:5000/
echo - Tai lieu API Swagger:   http://127.0.0.1:5000/docs
echo - Giao dien Web (Live):   http://127.0.0.1:5500/frontend/index.html
echo.
echo Dang mo giao dien web tren trinh duyet...
start http://127.0.0.1:5500/frontend/index.html
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 5000
