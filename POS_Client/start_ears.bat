@echo off
cd C:\Users\magic\WelcomeAPI
set OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
:loop
echo [%date% %time%] Starting Ears... >> C:\Users\magic\ears_log2.txt
C:\Users\magic\AppData\Local\Programs\Python\Python311\python.exe ears.py >> C:\Users\magic\ears_log2.txt 2>&1
echo [%date% %time%] Ears crashed, restarting in 2 seconds... >> C:\Users\magic\ears_log2.txt
timeout /t 2 /nobreak >nul
goto loop
