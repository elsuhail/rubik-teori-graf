@echo off
title Instalasi Virtual Rubik Web

echo =========================================
echo  INSTALASI KEBUTUHAN VIRTUAL RUBIK
echo =========================================
echo.

echo [1/3] Membuat Lingkungan Virtual Python (venv)...
python -m venv venv

echo [2/3] Menginstall Library Python (FastAPI, OpenCV, MediaPipe)...
call .\venv\Scripts\activate
pip install -r requirements.txt
deactivate

echo [3/3] Menginstall Library Frontend (Node.js/React)...
cd frontend
call npm install
cd ..

echo.
echo =========================================
echo INSTALASI SELESAI!
echo Silakan klik ganda pada "start_app.bat" untuk menjalankan program.
echo =========================================
pause
