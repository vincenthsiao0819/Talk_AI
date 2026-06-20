@echo off
cd C:\Users\magic\WelcomeAPI
:loop
echo [%date% %time%] Starting API... >> C:\Users\magic\server_log2.txt
node server.js >> C:\Users\magic\server_log2.txt 2>&1
echo [%date% %time%] API crashed, restarting in 2 seconds... >> C:\Users\magic\server_log2.txt
timeout /t 2 /nobreak >nul
goto loop
