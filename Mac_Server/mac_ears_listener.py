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

def ask_hermes(question):
    """Ask Hermes on GPU server for quick answers (sub-second, no cloud)"""
    try:
        payload = json.dumps({
            "model": "hermes3:8b",
            "prompt": f"你是龍蝦沙拉，一個家庭語音助理。請用繁體中文在30字以內簡潔回答以下問題：\n{question}",
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 100}
        }).encode('utf-8')
        req = urllib.request.Request("http://192.168.50.154:11434/api/generate", data=payload)
        req.add_header('Content-Type', 'application/json')
        res = urllib.request.urlopen(req, timeout=15)
        result = json.loads(res.read().decode('utf-8'))
        return result.get('response', '').strip()
    except Exception as e:
        log(f"Hermes failed: {e}")
        return None

def ask_gateway(question):
    """Fallback: Ask OpenClaw Gateway via tools/invoke → openclaw agent (slower but smarter)"""
    try:
        res = subprocess.run([
            "openclaw", "agent",
            "--model", "google/gemini-2.5-flash",
            "--session-key", "agent:main:telegram:direct:5916594299",
            "--message", f"[客廳語音] {question} (請將回覆濃縮在 30 字以內，以便加速語音播報)",
            "--deliver", "--json"
        ], capture_output=True, text=True, timeout=30)
        
        try:
            result = json.loads(res.stdout)
            return result.get("text", "").replace("<final>", "").replace("</final>", "").strip()
        except:
            # Try to extract from raw output
            raw = res.stdout.strip()
            if raw:
                return raw
    except Exception as e:
        log(f"Gateway agent failed: {e}")
    return None

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 5005))
s.listen(5)
log("Mac ears listener started on port 5005 (Hermes-first mode)")

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
            
            # 2. 先問 Hermes (極速 GPU Local)
            reply = ask_hermes(data)
            
            if not reply:
                # 3. Hermes 掛了才走 Gateway (慢但聰明)
                log("Hermes unavailable, falling back to Gateway agent...")
                reply = ask_gateway(data)
            
            elapsed = time.time() - start_time
            
            if reply:
                log(f"Reply ({elapsed:.1f}s): {reply}")
                # 4. 發送到客廳喇叭
                send_tts(reply)
                # 5. 也發一份到 Telegram
                send_telegram(f"🦞 {reply}")
            else:
                log(f"No reply generated ({elapsed:.1f}s)")
                send_tts("抱歉，我暫時無法回答")
                
    except Exception as e:
        log(f"Socket or General Error: {e}")
