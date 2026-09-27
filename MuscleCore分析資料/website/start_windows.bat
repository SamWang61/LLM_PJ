@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (
  echo [錯誤] 尚未安裝 Python 3.11 以上版本。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt || goto :error
if not exist ".env" copy ".env.example" ".env" >nul

where docker >nul 2>nul && docker compose up -d
python seed_mongodb.py || goto :mongo_error

echo.
echo MuscleCore 啟動完成：http://127.0.0.1:5000
python run.py
exit /b 0

:mongo_error
echo.
echo [錯誤] MongoDB 尚未啟動。請啟動 MongoDB 服務或 Docker Desktop 後重試。
pause
exit /b 1

:error
echo.
echo [錯誤] Python 套件安裝失敗，請確認網路連線後重試。
pause
exit /b 1

