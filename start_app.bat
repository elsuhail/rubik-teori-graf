@echo off
title Virtual Rubik Web Launcher

echo =========================================
echo  MEMULAI VIRTUAL RUBIK (VERSI WEB)
echo =========================================
echo.

echo [1/3] Menjalankan Server Backend (Python + AI Kamera)...
start "Rubik Backend AI" cmd /k ".\venv\Scripts\activate && cd backend && python server.py"

echo [2/3] Menjalankan Server Frontend (React Web)...
start "Rubik Frontend Web" cmd /k "cd frontend && npm run dev"

echo [3/3] Membuka Browser...
echo Tunggu 5 detik agar server siap...
timeout /t 5 /nobreak >nul

start http://localhost:5173

echo.
echo Selesai! Web akan otomatis terbuka di browser Anda.
echo Jika sudah selesai, Anda bisa menutup jendela hitam (terminal) yang terbuka.
pause
