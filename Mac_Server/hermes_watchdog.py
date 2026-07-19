import subprocess
import socket
import urllib.request
import urllib.error
import json
import time
import sys
import logging
import os
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("HermesWatchdog")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/hermes_watchdog.log", maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

def log(msg):
    logger.info(msg)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    sys.stdout.flush()

SSH_CMD = ["sshpass", "-p", "6611", "ssh", "-o", "StrictHostKeyChecking=no", "magic@192.168.50.204"]
SSH_154_CMD = ["sshpass", "-p", "6611", "ssh", "-o", "StrictHostKeyChecking=no", "Vincent Hsiao@192.168.50.154"]
OLLAMA_PATH = r"C:\Users\Vincent Hsiao\AppData\Local\Programs\Ollama\ollama.exe"

# ======== Rate Limit State ========
_last_alert_type = None
_last_alert_time = 0
ALERT_COOLDOWN_SECONDS = 1200  # 20 minutes cooldown before sending same type again

def should_alert(alert_type):
    """Rate limit: only send same alert type once per 20 minutes."""
    global _last_alert_type, _last_alert_time
    now = time.time()
    if alert_type == _last_alert_type and (now - _last_alert_time) < ALERT_COOLDOWN_SECONDS:
        return False
    _last_alert_type = alert_type
    _last_alert_time = now
    return True

def send_alert(alert_type, summary):
    """Send Telegram alert respecting rate limit."""
    if not should_alert(alert_type):
        log(f"Rate limited: skipping duplicate alert '{alert_type}'")
        return
    alert_msg = f"🚨 **Hermes 系統監控回報異常** 🚨\n\n{summary}\n\n(OpenClaw，已執行自動復原，請確認系統狀態)"
    log("Sending Telegram alert...")
    subprocess.run(["openclaw", "message", "send", "--channel", "telegram", "--target", "5916594299", "--message", alert_msg])

# ======== Ollama Auto-Recovery ========
def recover_ollama():
    """Kill hung Ollama processes on 154 and restart."""
    log("Ollama API unresponsive. Attempting remote kill + restart on 154...")
    try:
        # Kill hung processes
        kill = subprocess.run(SSH_154_CMD + ["taskkill", "/f", "/im", "ollama.exe"], 
                              capture_output=True, text=True, timeout=10)
        log(f"taskkill ollama.exe: {kill.stdout.strip()}")
        # Also kill launcher
        kill2 = subprocess.run(SSH_154_CMD + ["taskkill", "/f", "/im", "ollama app.exe"], 
                               capture_output=True, text=True, timeout=10)
        log(f"taskkill ollama app.exe: {kill2.stdout.strip()}")
        time.sleep(2)
        
        # Restart via PowerShell Start-Process (background)
        start = subprocess.run(SSH_154_CMD + ["powershell", "-NoProfile", "-Command",
            f"Start-Process -FilePath '{OLLAMA_PATH}' -ArgumentList 'serve' -WindowStyle Hidden"],
            capture_output=True, text=True, timeout=10)
        log(f"Ollama restart issued: {start.stdout.strip()}")
        
        # Wait for API to come up
        for i in range(5):
            time.sleep(3)
            try:
                req = urllib.request.Request("http://192.168.50.154:11434/api/tags")
                res = urllib.request.urlopen(req, timeout=5)
                if res.getcode() == 200:
                    log("Ollama API is back online!")
                    return True
            except:
                log(f"Waiting for Ollama... attempt {i+1}/5")
        
        log("Ollama recovery: API still unresponsive after 5 attempts")
        return False
    except Exception as e:
        log(f"Ollama recovery failed with error: {e}")
        return False

# ======== Status Gathering ========
def gather_status():
    status = []
    
    # 1. Check MagicMirror UI (locally on 204:8080)
    try:
        res = subprocess.run(SSH_CMD + ["powershell", "-Command", "(Invoke-WebRequest -Uri http://localhost:8080/ -UseBasicParsing -TimeoutSec 10).StatusCode"], capture_output=True, text=True, timeout=25)
        if "200" in res.stdout:
            status.append("MagicMirror (192.168.50.204:8080) HTTP Status: 200")
        else:
            status.append(f"MagicMirror (192.168.50.204:8080) HTTP Status: Failed - {res.stdout.strip()}")
    except Exception as e:
        status.append(f"MagicMirror (192.168.50.204:8080) Error: {e}")

    # 2. Check Welcome API (204:8081)
    try:
        req = urllib.request.Request("http://192.168.50.204:8081/")
        res = urllib.request.urlopen(req, timeout=5)
        status.append(f"Welcome API (192.168.50.204:8081) HTTP Status: {res.getcode()}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            status.append("Welcome API (192.168.50.204:8081) HTTP Status: 200")
        else:
            status.append(f"Welcome API (192.168.50.204:8081) HTTP Status: {e.code}")
    except Exception as e:
        status.append(f"Welcome API (192.168.50.204:8081) Error: {e}")

    # 3. Check Docker HA (154:8123)
    try:
        req = urllib.request.Request("http://192.168.50.154:8123/")
        res = urllib.request.urlopen(req, timeout=5)
        status.append(f"Home Assistant (192.168.50.154:8123) HTTP Status: {res.getcode()}")
    except urllib.error.HTTPError as e:
        status.append(f"Home Assistant (192.168.50.154:8123) HTTP Status: {e.code}")
    except Exception as e:
        status.append(f"Home Assistant (192.168.50.154:8123) Error: {e}")

    # 4. Check Docker Desktop Process on 154
    try:
        res = subprocess.run(SSH_154_CMD + ["tasklist", "|", "findstr", "Docker"], capture_output=True, text=True, timeout=10)
        if "Docker Desktop.exe" in res.stdout:
            status.append("Docker Desktop Process on 154: Running")
        else:
            status.append("Docker Desktop Process on 154: Not Found")
    except Exception as e:
        status.append(f"Docker Desktop Process check failed: {e}")

    # 5. Check HA Container State
    try:
        res = subprocess.run(SSH_154_CMD + ["docker", "ps", "--filter", "name=homeassistant", "--format", "{{.Status}}"], capture_output=True, text=True, timeout=10)
        if res.stdout.strip():
            status.append(f"HA Container Status: {res.stdout.strip()}")
        else:
            status.append("HA Container Status: Not Running")
    except Exception as e:
        status.append(f"HA Container Check failed: {e}")

    # 6. Check 154 to 204 connectivity (WSL bridge test)
    try:
        res = subprocess.run(SSH_154_CMD + ["powershell", "-Command", "Test-NetConnection -ComputerName 192.168.50.204 -Port 8081"], capture_output=True, text=True, timeout=15)
        if "TcpTestSucceeded : True" in res.stdout:
            status.append("154 to 204 TCP connection (Welcome API): Succeeded")
        else:
            status.append("154 to 204 TCP connection (Welcome API): Failed")
    except Exception as e:
        status.append(f"154 to 204 connectivity check failed: {e}")

    # 7. Check Samsung Tablet online (MacroDroid prerequisite)
    try:
        res = subprocess.run(["ping", "-c", "2", "-W", "3", "192.168.50.156"], capture_output=True, timeout=10)
        if res.returncode == 0:
            status.append("Samsung Tablet (192.168.50.156) Ping: Online")
        else:
            status.append("Samsung Tablet (192.168.50.156) Ping: OFFLINE - MacroDroid 歡迎系統可能已失效")
    except Exception as e:
        status.append(f"Samsung Tablet Ping Error: {e}")

    # 8. Check HA Welcome Automation heartbeat (last_triggered within 24h)
    try:
        from datetime import datetime, timezone
        res = subprocess.run(SSH_154_CMD + ["type", "C:\\ha_token.txt"], capture_output=True, timeout=10)
        ha_token = res.stdout.decode('utf-8', errors='ignore').strip()
        if ha_token:
            req = urllib.request.Request(
                "http://192.168.50.154:8123/api/states/automation.ke_ting_guang_bo_quan_fang_wei_lei_da_yu_men_suo_hun_he_huan_ying_xi_tong",
                headers={"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            last_triggered = data.get('attributes', {}).get('last_triggered', '')
            if last_triggered:
                last_dt = datetime.fromisoformat(last_triggered.replace('Z', '+00:00'))
                age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if age_hours > 24:
                    status.append(f"HA Welcome Automation: STALE - 超過 {age_hours:.0f} 小時未觸發，MacroDroid 可能已失效")
                else:
                    status.append(f"HA Welcome Automation: OK - {age_hours:.1f}h ago")
            else:
                status.append("HA Welcome Automation: Never triggered")
        else:
            status.append("HA Welcome Automation: Cannot read HA token")
    except Exception as e:
        status.append(f"HA Welcome Automation Heartbeat Error: {e}")

    return "\n".join(status)

def ask_hermes(status_report):
    prompt = f"""You are Hermes, an AI system monitor for a smart home environment. 
Review the following system status report. The ecosystem consists of:
- GPU Server (192.168.50.154): Runs Docker Desktop and Home Assistant (HA) container.
- MagicMirror & AI Talk (192.168.50.204): Runs MagicMirror UI (8080) and Welcome API (8081).
- Samsung Tablet (192.168.50.156): Runs MacroDroid to intercept door lock notifications and POST to HA webhook. Ping OFFLINE alone is NOT an anomaly (tablet Wi-Fi may sleep but MacroDroid still works internally). Only flag anomaly if BOTH tablet is OFFLINE AND HA Welcome Automation is STALE (>24h).

Status Report:
{status_report}

Instructions:
1. Analyze the components. If any critical service (Docker, HA, MagicMirror, Welcome API, or network connectivity) is failing or returning an error, consider it an anomaly.
2. If the system is completely healthy, reply exactly with: "STATUS: OK".
3. If there is an anomaly, reply with: "STATUS: ANOMALY" followed by a newline and a concise explanation of the failure. Do not hallucinate. Be extremely brief and professional. Use Traditional Chinese for the explanation."""

    try:
        req = urllib.request.Request("http://192.168.50.154:11434/api/generate", data=json.dumps({
            "model": "hermes3:8b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        res = urllib.request.urlopen(req, timeout=45)
        result = json.loads(res.read().decode('utf-8'))
        return result.get('response', '').strip()
    except Exception as e:
        return f"STATUS: ANOMALY\nFailed to contact Hermes API: {e}"

def main():
    log("Gathering system status...")
    status_report = gather_status()
    log(f"Raw Status:\n{status_report}")
    
    log("Asking Hermes for analysis...")
    hermes_response = ask_hermes(status_report)
    log(f"Hermes Response:\n{hermes_response}")
    
    if hermes_response.startswith("STATUS: ANOMALY"):
        # Check if the anomaly is specifically Hermes/Ollama API down
        if "Failed to contact Hermes API" in hermes_response:
            log("Hermes/Ollama API is down. Attempting auto-recovery...")
            recovered = recover_ollama()
            if recovered:
                log("Auto-recovery succeeded. Supressing alert.")
                # After recovery, do one more clean check
                status_report2 = gather_status()
                hermes_response2 = ask_hermes(status_report2)
                log(f"Post-recovery Hermes response: {hermes_response2}")
                if "STATUS: OK" in hermes_response2:
                    log("All systems normal after recovery. No alert needed.")
                    return
                else:
                    send_alert("hermes_unrecoverable", 
                               f"Ollama 已手動重啟成功，但後續檢查仍有異常：\n\n{hermes_response2}")
            else:
                send_alert("hermes_unrecoverable", 
                           f"Ollama API 無法連線，且自動重啟失敗，需手動介入：\n\n{hermes_response}")
        else:
            # Other anomaly (not Ollama-specific)
            send_alert("hermes_other", hermes_response)
    else:
        log("STATUS: OK - All systems normal.")

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            log(f"Hermes Watchdog error: {e}")
        time.sleep(300) # Check every 5 minutes
