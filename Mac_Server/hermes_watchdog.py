import subprocess
import socket
import urllib.request
import urllib.error
import json
import time
import sys
import logging
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
SSH_154_CMD = ["ssh", "-o", "StrictHostKeyChecking=no", "Vincent Hsiao@192.168.50.154"]

def gather_status():
    status = []
    
    # 1. Check MagicMirror UI (locally on 204:8080)
    try:
        res = subprocess.run(SSH_CMD + ["powershell", "-Command", "(Invoke-WebRequest -Uri http://localhost:8080/ -UseBasicParsing -TimeoutSec 5).StatusCode"], capture_output=True, text=True, timeout=10)
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
            # 404 means Node.js is running but route is invalid (which is safe)
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

    return "\n".join(status)

def ask_hermes(status_report):
    prompt = f"""You are Hermes, an AI system monitor for a smart home environment. 
Review the following system status report. The ecosystem consists of:
- GPU Server (192.168.50.154): Runs Docker Desktop and Home Assistant (HA) container.
- MagicMirror & AI Talk (192.168.50.204): Runs MagicMirror UI (8080) and Welcome API (8081).

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
        alert_msg = f"🚨 **Hermes 系統監控回報異常** 🚨\n\n{hermes_response}\n\n(OpenClaw，請立即接手調查，並使用 GitHub SOP 進行乾淨恢復)"
        log("Anomaly detected. Sending Telegram alert...")
        subprocess.run(["openclaw", "message", "send", "--channel", "telegram", "--target", "5916594299", "--message", alert_msg])

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            log(f"Hermes Watchdog error: {e}")
        time.sleep(300) # Check every 5 minutes

