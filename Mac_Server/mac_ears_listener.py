import socket
import subprocess
import time
import sys
import json
import urllib.request
import urllib.error
import os
import logging
from logging.handlers import RotatingFileHandler

# Setup Rotating Log
logger = logging.getLogger("MacEars")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/mac_ears.log", maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

GATEWAY_URL = "http://127.0.0.1:18789"
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
TTS_URL = "http://192.168.50.204:8081/speak"
TELEGRAM_TARGET = "telegram:5916594299"

def log(msg):
    logger.info(msg)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [MacEars] {msg}")
    sys.stdout.flush()

def send_telegram(text):
    """Send notification to Telegram via Gateway tools/invoke (no CLI cold-start)"""
    try:
        payload = json.dumps({
            "tool": "message",
            "args": {
                "action": "send",
                "channel": "telegram",
                "target": TELEGRAM_TARGET,
                "message": text
            }
        }).encode('utf-8')
        req = urllib.request.Request(f"{GATEWAY_URL}/tools/invoke", data=payload)
        req.add_header('Content-Type', 'application/json')
        if GATEWAY_TOKEN:
            req.add_header('Authorization', f'Bearer {GATEWAY_TOKEN}')
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log(f"Telegram send failed: {e}")

def send_tts(text):
    """Send text to MagicMirror speaker"""
    try:
        payload = json.dumps({"text": text}).encode('utf-8')
        req = urllib.request.Request(TTS_URL, data=payload)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        urllib.request.urlopen(req, timeout=5)
        log(f"TTS sent: {text}")
    except Exception as e:
        log(f"TTS send failed: {e}")

def ask_openclaw(question):
    """Ask OpenClaw agent (full tool access: can execute tasks, not just answer questions)"""
    try:
        res = subprocess.run([
            "openclaw", "agent",
            "--model", "google/gemini-2.5-flash",
            "--session-key", "agent:main:telegram:direct:5916594299",
            "--message", f"[客廳語音] {question} (請將回覆濃縮在 30 字以內，以便加速語音播報)",
            "--json"
        ], capture_output=True, text=True, timeout=60)
        
        try:
            result = json.loads(res.stdout)
            return result.get("text", "").strip()
        except json.JSONDecodeError:
            # Try raw output
            raw = res.stdout.strip()
            if raw:
                return raw
    except subprocess.TimeoutExpired:
        log("OpenClaw agent timed out (60s)")
    except Exception as e:
        log(f"OpenClaw agent error: {e}")
    return None

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 5005))
s.listen(5)
log("Mac ears listener started on port 5005 (OpenClaw-brain mode)")

while True:
    try:
        c, a = s.accept()
        data = c.recv(4096).decode('utf-8').strip()
        c.close()
        if data:
            log(f"Received from POS: {data}")
            start_time = time.time()
            
            # 1. Telegram 通知 (non-blocking via Gateway API)
            send_telegram(f"🗣️ Lobster 聽到：{data}")
            
            # 2. 問 OpenClaw (完整大腦，能回答問題也能執行任務)
            reply = ask_openclaw(data)
            
            elapsed = time.time() - start_time
            
            if reply:
                log(f"Reply ({elapsed:.1f}s): {reply}")
                # 3. 發送到客廳喇叭
                send_tts(reply)
                # 4. 也發一份到 Telegram
                send_telegram(f"🦞 {reply}")
            else:
                log(f"No reply generated ({elapsed:.1f}s)")
                send_tts("抱歉，我暫時無法回答")
                
    except Exception as e:
        log(f"Socket or General Error: {e}")
