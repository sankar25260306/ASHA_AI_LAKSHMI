@echo off
setlocal
start "ASHA AI Frontend Server" cmd /k "cd /d ""%~dp0frontend"" && py -m http.server 5173 --bind 127.0.0.1"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5173
echo Frontend server should be available at http://127.0.0.1:5173
