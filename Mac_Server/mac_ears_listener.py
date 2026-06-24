import socket
import subprocess
import time
import sys
import logging
from logging.handlers import RotatingFileHandler

# Setup Rotating Log
logger = logging.getLogger("MacEars")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/mac_ears.log", maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

def log(msg):
    logger.info(msg)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [MacEars] {msg}")
    sys.stdout.flush()

s = socket.socket()
s.bind(("0.0.0.0", 5005))
s.listen(5)
log("Mac ears listener started on port 5005")

while True:
    try:
        c, a = s.accept()
        data = c.recv(4096).decode('utf-8').strip()
        c.close()
        if data:
            log(f"Received from POS: {data}")
            
            # 1. 雙向紀錄：發送 Telegram 訊息讓使用者知道 Lobster 聽到了什麼
            subprocess.Popen([
                "openclaw", "message", "send", 
                "--channel", "telegram", "--target", "telegram:5916594299", 
                "--message", f"🗣️ Lobster 聽到：{data}"
            ])
            
            # 2. 觸發極速大腦回答：覆寫模型為 google/gemini-2.5-flash，並強制字數限制在 30 字內
            subprocess.Popen([
                "openclaw", "agent", 
                "--model", "google/gemini-2.5-flash",
                "--session-key", "agent:main:telegram:direct:5916594299", 
                "--message", f"[客廳語音] {data} (請將回覆濃縮在 30 字以內，以便加速語音播報)", 
                "--deliver"
            ])
    except Exception as e:
        log(f"Error: {e}")
