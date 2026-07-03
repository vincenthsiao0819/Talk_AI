import subprocess
import socket
import urllib.request
import time
import base64
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# Secrets (Do NOT push this script to public GitHub, keep it local on Mac)
OPENAI_API_KEY = "sk-proj-7GstW6mU9qJ2Q5k4Kk3mZf0wX-tJqOq8rF6eH_R3M_l-w3zU4s2zR5eP6oV0qX1tM-yVzfwA" # Extracted from start_ears.bat

MUTE_FLAG_PATH = "/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/mute.flag"
SSH_CMD = ["sshpass", "-p", "6611", "ssh", "-o", "StrictHostKeyChecking=no", "magic@192.168.50.204"]
SSH_154_CMD = ["ssh", "-o", "StrictHostKeyChecking=no", "Vincent Hsiao@192.168.50.154"]

# Setup Rotating Log
logger = logging.getLogger("Watchdog")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/watchdog.log", maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

def log(msg):
    logger.info(msg)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Watchdog] {msg}")
    sys.stdout.flush()

def check_tunnel():
    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect(("127.0.0.1", 5005))
        s.close()
        return True
    except:
        return False

def check_api():
    try:
        req = urllib.request.Request("http://192.168.50.204:8081/")
        # It should return 404 for root, but connection succeeds
        urllib.request.urlopen(req, timeout=3)
        return True
    except urllib.error.HTTPError as e:
        return True # 404 means server is up
    except Exception:
        return False

def recover_tunnel():
    log("Recovering SSH Tunnel...")
    subprocess.run(["pkill", "-f", "keep_ears_tunnel.sh"], capture_output=True)
    subprocess.run(["pkill", "-f", "ssh.*192.168.50.204"], capture_output=True)
    subprocess.Popen(["bash", "/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/keep_ears_tunnel.sh"], 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

def recover_api():
    log("Recovering Welcome API from GitHub baseline...")
    # 1. Pull latest from GitHub
    subprocess.run(["git", "pull"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", check=True)
    
    # 2. Kill existing node processes
    subprocess.run(SSH_CMD + ["wmic process where \"CommandLine LIKE '%server.js%'\" call terminate"], capture_output=True)
    
    # 3. Read clean baseline
    with open("/Users/vincenthsiao/.openclaw/workspace/Talk_AI/POS_Client/server.js", "rb") as f:
        content = f.read()
    b64_content = base64.b64encode(content).decode('utf-8')
    
    # 4. Deploy and restart
    with open("/Users/vincenthsiao/.openclaw/workspace/temp_api.b64", "w") as f:
        f.write(b64_content)
    subprocess.run(["sshpass", "-p", "6611", "scp", "-o", "StrictHostKeyChecking=no", 
                    "/Users/vincenthsiao/.openclaw/workspace/temp_api.b64", 
                    "magic@192.168.50.204:C:/Users/magic/WelcomeAPI/server.b64"])
    subprocess.run(SSH_CMD + ["certutil -f -decode C:\\Users\\magic\\WelcomeAPI\\server.b64 C:\\Users\\magic\\WelcomeAPI\\server.js"], capture_output=True)
    subprocess.run(SSH_CMD + ["schtasks /run /tn \"RunWelcomeAPI\""], capture_output=True)
    log("Triggered RunWelcomeAPI task.")

def recover_ears():
    log("Recovering Ears Python from GitHub baseline...")
    # 1. Pull latest from GitHub
    subprocess.run(["git", "pull"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", check=True)
    
    # 2. Kill existing python processes
    subprocess.run(SSH_CMD + ["taskkill /f /im python.exe"], capture_output=True)
    
    # 3. Read clean baseline and inject key
    with open("/Users/vincenthsiao/.openclaw/workspace/Talk_AI/POS_Client/ears.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace("YOUR_OPENAI_API_KEY_HERE", OPENAI_API_KEY)
    b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    # 4. Deploy and restart
    with open("/Users/vincenthsiao/.openclaw/workspace/temp_ears.b64", "w") as f:
        f.write(b64_content)
    subprocess.run(["sshpass", "-p", "6611", "scp", "-o", "StrictHostKeyChecking=no", 
                    "/Users/vincenthsiao/.openclaw/workspace/temp_ears.b64", 
                    "magic@192.168.50.204:C:/Users/magic/WelcomeAPI/ears.b64"])
    subprocess.run(SSH_CMD + ["certutil -f -decode C:\\Users\\magic\\WelcomeAPI\\ears.b64 C:\\Users\\magic\\WelcomeAPI\\ears.py"], capture_output=True)
    subprocess.run(SSH_CMD + ["schtasks /run /tn \"RunEars\""], capture_output=True)
    log("RunEars task triggered.")

def recover_mac_ears():
    log("Reverting Mac Ears Python to GitHub baseline...")
    subprocess.run(["git", "restore", "Mac_Server/mac_ears_listener.py"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", check=True)
    subprocess.run(["git", "pull"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", check=True)
    subprocess.run(["pkill", "-f", "mac_ears_listener.py"])
    subprocess.Popen(["nohup", "python3", "/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/mac_ears_listener.py"], 
                     cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server",
                     stdout=open("/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/mac_ears.log", "a"), 
                     stderr=subprocess.STDOUT)
    time.sleep(2)

def recover_ha_automations():
    log("Reverting HA automations to GitHub baseline...")
    subprocess.run(["git", "restore", "HA_Server/automations.yaml"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", check=True)
    subprocess.run(["git", "pull"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", check=True)
    subprocess.run(["cp", "/Users/vincenthsiao/.openclaw/workspace/Talk_AI/HA_Server/automations.yaml", "/Users/vincenthsiao/.openclaw/workspace/automations.yaml"])
    # Restart not possible automatically, require user action

def recover_welcome_api_integrity():
    log("Reverting Welcome API to GitHub baseline...")
    subprocess.run(["git", "restore", "POS_Client/server.js"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", check=True)
    recover_api()


def recover_magicmirror_config():
    log("Reverting MagicMirror config_normal.js to GitHub baseline...")
    subprocess.run(["git", "restore", "config_normal.js"], cwd="/Users/vincenthsiao/.openclaw/workspace/MagicMirror_normal-_setting_value_27inch_Display", check=True)
    subprocess.run(["git", "pull"], cwd="/Users/vincenthsiao/.openclaw/workspace/MagicMirror_normal-_setting_value_27inch_Display", check=True)
    
    # Push the clean config to the remote machine
    subprocess.run(["sshpass", "-p", "6611", "scp", "-o", "StrictHostKeyChecking=no", 
                    "/Users/vincenthsiao/.openclaw/workspace/MagicMirror_normal-_setting_value_27inch_Display/config_normal.js", 
                    "magic@192.168.50.204:C:/Users/magic/MagicMirror/config/config_normal.js"])
    
    # Restart MagicMirror to apply
    recover_magicmirror()



def check_zombie_ears():
    try:
        res = subprocess.run(SSH_CMD + ["wmic process where \"Name='python.exe' and CommandLine LIKE '%ears.py%'\" get ProcessId"], capture_output=True, timeout=10)
        stdout_str = res.stdout.decode('utf-8', errors='ignore')
        lines = [line.strip() for line in stdout_str.splitlines() if line.strip() and "ProcessId" not in line]
        if len(lines) > 1:
            log(f"Detected {len(lines)} ears.py python processes (Expected 1). Cleaning up...")
            subprocess.run(SSH_CMD + ["taskkill /f /im python.exe"], capture_output=True, timeout=10)
            return len(lines)
        return 0
    except Exception as e:
        log(f"Error checking zombie ears.py: {e}")
        return 0

def check_zombie_node():
    try:
        # PM2 spawns multiple nodes, but if we exceed 6, something is wrong
        res = subprocess.run(SSH_CMD + ["wmic process where \"Name='node.exe'\" get ProcessId"], capture_output=True, timeout=10)
        stdout_str = res.stdout.decode('utf-8', errors='ignore')
        lines = [line.strip() for line in stdout_str.splitlines() if line.strip() and "ProcessId" not in line]
        if len(lines) >= 8:
            log(f"Detected {len(lines)} node.exe processes (Abnormal). Triggering recovery...")
            return len(lines)
        return 0
    except Exception:
        return 0

def check_zombie_powershell():
    try:
        res = subprocess.run(SSH_CMD + ["wmic process where \"Name='powershell.exe' and CommandLine LIKE '%Welcome%ps1%'\" get ProcessId"], capture_output=True, timeout=10)
        stdout_str = res.stdout.decode('utf-8', errors='ignore')
        lines = [line.strip() for line in stdout_str.splitlines() if line.strip() and "ProcessId" not in line]
        if len(lines) >= 2:
            log(f"Detected {len(lines)} zombie Welcome PowerShell processes. Cleaning up...")
            subprocess.run(SSH_CMD + ["wmic process where \"Name='powershell.exe' and CommandLine LIKE '%Welcome%ps1%'\" call terminate"], capture_output=True, timeout=10)
            return len(lines)
        return 0
    except Exception as e:
        log(f"Error checking zombie powershell: {e}")
        return 0

def check_magicmirror():
    try:
        # Liveness Probe: ping local web server
        res = subprocess.run(SSH_CMD + ["powershell", "-Command", "(Invoke-WebRequest -Uri http://localhost:8080/ -UseBasicParsing -TimeoutSec 5).StatusCode"], capture_output=True, text=True, timeout=15)
        if "200" in res.stdout:
            return True
        else:
            return False
    except Exception as e:
        log(f"MagicMirror Liveness Probe Error: {e}")
        return False

def recover_magicmirror():
    log("Recovering MagicMirror Dashboard via Full Reboot (Session 0 cannot launch GUI in Session 1)...")
    subprocess.run(SSH_CMD + ["taskkill /F /IM electron.exe /T"], capture_output=True)
    subprocess.run(SSH_CMD + ["wmic process where \"Name='node.exe' and not CommandLine like '%server.js%'\" call terminate"], capture_output=True)
    # Clear Electron cache to prevent white screen deadlock
    subprocess.run(SSH_CMD + ["powershell -Command \"Remove-Item -Path 'C:\\Users\\magic\\AppData\\Roaming\\Electron\\Cache\\*' -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -Path 'C:\\Users\\magic\\AppData\\Roaming\\Electron\\Code Cache\\*' -Recurse -Force -ErrorAction SilentlyContinue\""], capture_output=True)
    # Reboot: AutoAdminLogon + mm_startup.bat will auto-launch MagicMirror in Session 1
    subprocess.run(SSH_CMD + ["shutdown /r /t 10 /f /c \"Watchdog Recovery\""], capture_output=True)
    log("Reboot command sent to 192.168.50.204. Waiting 90 seconds for it to come back up...")
    time.sleep(90)

def check_ha_server():
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect(("192.168.50.154", 8123))
        s.close()
        return True
    except:
        return False

def recover_ha_server():
    log("Home Assistant is down. Attempting to restart Docker container on 192.168.50.154...")
    subprocess.run(SSH_154_CMD + ["docker restart homeassistant"], capture_output=True)

def check_tablet_online():
    """Ping Samsung tablet (192.168.50.156) to verify it's on the network."""
    try:
        res = subprocess.run(["ping", "-c", "2", "-W", "3", "192.168.50.156"], capture_output=True, timeout=10)
        return res.returncode == 0
    except Exception as e:
        log(f"Tablet Ping Error: {e}")
        return False

def check_ha_welcome_heartbeat():
    """Check if HA welcome automation was triggered in the last 24 hours."""
    try:
        import json
        from datetime import datetime, timezone, timedelta
        
        # Read HA token
        res = subprocess.run(SSH_154_CMD + ["type", "C:\\ha_token.txt"], capture_output=True, timeout=10)
        ha_token = res.stdout.decode('utf-8', errors='ignore').strip()
        if not ha_token:
            log("Cannot read HA token.")
            return 'error'
        
        req = urllib.request.Request(
            "http://192.168.50.154:8123/api/states/automation.ke_ting_guang_bo_quan_fang_wei_lei_da_yu_men_suo_hun_he_huan_ying_xi_tong",
            headers={"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        
        last_triggered = data.get('attributes', {}).get('last_triggered')
        if not last_triggered:
            log("HA automation has never been triggered.")
            return 'stale'
        
        # Parse ISO timestamp
        last_dt = datetime.fromisoformat(last_triggered.replace('Z', '+00:00'))
        now_utc = datetime.now(timezone.utc)
        age_hours = (now_utc - last_dt).total_seconds() / 3600
        
        log(f"HA Welcome Automation last triggered {age_hours:.1f} hours ago.")
        if age_hours > 24:
            return 'stale'
        return 'ok'
    except Exception as e:
        log(f"HA Welcome Heartbeat Error: {e}")
        return 'error'

def main():
    alerts = []
    
    # Check 1: Welcome API
    if not check_api():
        alerts.append("⚠️ Welcome API 斷線，正在從 GitHub 基準還原...")
        recover_api()
    else:
        log("Welcome API is OK.")

    # Check 1.5: Home Assistant Server on 154
    if not check_ha_server():
        alerts.append("⚠️ Home Assistant 伺服器 (192.168.50.154:8123) 斷線或卡死，Watchdog 正在嘗試遠端重啟 Docker 容器...")
        recover_ha_server()
    else:
        log("Home Assistant Server is OK.")

    # Check 2: Ears Process
    if os.path.exists(MUTE_FLAG_PATH):
        log("維護模式 (mute.flag) 已開啟，跳過 Ears 語音程式檢查。")
    else:
        python_check = subprocess.run(SSH_CMD + ["tasklist | findstr python"], capture_output=True, text=True)
        if "python.exe" not in python_check.stdout:
            alerts.append("⚠️ Ears 語音程式 (Python) 崩潰，正在從 GitHub 基準還原並注入金鑰...")
            recover_ears()
        else:
            log("Ears Python process is OK.")

    # Check 3: Tunnel
    if not check_tunnel():
        alerts.append("⚠️ SSH 逆向隧道斷線，正在重新啟動...")
        recover_tunnel()
    else:
        log("SSH Tunnel is OK.")

    # Check 4: Mac Ears Integrity and Process
    mac_ears_status = subprocess.run(["git", "status", "--porcelain", "Mac_Server/mac_ears_listener.py"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", capture_output=True, text=True)
    is_modified = "M " in mac_ears_status.stdout or " M" in mac_ears_status.stdout
    
    is_running = False
    try:
        proc = subprocess.run(["pgrep", "-f", "mac_ears_listener.py"], capture_output=True, text=True)
        if proc.stdout.strip():
            is_running = True
    except:
        pass

    if is_modified:
        alerts.append("⚠️ 偵測到 Mac_Server/mac_ears_listener.py 有未經授權的修改！正在還原回 GitHub 乾淨版本並重啟...")
        recover_mac_ears()
    elif not is_running:
        alerts.append("⚠️ 偵測到 Mac Ears Listener 未啟動，正在重新啟動...")
        recover_mac_ears()
    else:
        log("Mac Ears Listener is running and integrity is OK.")

    # Check 5: HA Automations Integrity
    ha_auto_status = subprocess.run(["git", "status", "--porcelain", "HA_Server/automations.yaml"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", capture_output=True, text=True)
    if "M " in ha_auto_status.stdout or " M" in ha_auto_status.stdout:
        alerts.append("⚠️ 偵測到 HA_Server/automations.yaml 有未經授權的修改！正在還原回 GitHub 乾淨版本...")
        recover_ha_automations()
    else:
        log("HA Automations integrity is OK.")

    # Check 6: Welcome API Source Integrity
    welcome_api_status = subprocess.run(["git", "status", "--porcelain", "POS_Client/server.js"], cwd="/Users/vincenthsiao/.openclaw/workspace/Talk_AI", capture_output=True, text=True)
    if "M " in welcome_api_status.stdout or " M" in welcome_api_status.stdout:
        alerts.append("⚠️ 偵測到 Welcome API (server.js) 有未經授權的修改！正在還原回 GitHub 乾淨版本並重啟...")
        recover_welcome_api_integrity()
    else:
        log("Welcome API source integrity is OK.")

    # Check 7: MagicMirror Dashboard System
    if not check_magicmirror():
        alerts.append("⚠️ 看板系統 (MagicMirror) 崩潰或未啟動，正在遠端重啟 Electron...")
        recover_magicmirror()
    else:
        log("MagicMirror Dashboard process is OK.")



    # Check 8: MagicMirror Config Integrity
    mm_config_status = subprocess.run(["git", "status", "--porcelain", "config_normal.js"], cwd="/Users/vincenthsiao/.openclaw/workspace/MagicMirror_normal-_setting_value_27inch_Display", capture_output=True, text=True)
    if "M " in mm_config_status.stdout or " M" in mm_config_status.stdout:
        alerts.append("⚠️ 偵測到 看板設定檔 (config_normal.js) 有未經授權的修改！正在還原回 GitHub 乾淨版本並重啟看板...")
        recover_magicmirror_config()
    else:
        log("MagicMirror config integrity is OK.")

    # Check 9: Zombie PowerShell Process Patrol
    zombie_count = check_zombie_powershell()
    if zombie_count > 0:
        alerts.append(f"⚠️ 偵測到客廳主機卡了 {zombie_count} 個 Welcome.ps1 殭屍行程，Watchdog 已成功強制撲殺清理！")
    else:
        log("Zombie PowerShell patrol passed (No zombies found).")


    # Check 10: Zombie Python / Node.js
    zombie_ears_count = check_zombie_ears()
    if zombie_ears_count > 1:
        alerts.append(f"⚠️ 偵測到客廳麥克風卡了 {zombie_ears_count} 個 ears.py 分身！Watchdog 已強制屠魔清場，即將透過排程自動重生。")
    
    zombie_node_count = check_zombie_node()
    if zombie_node_count >= 8:
        alerts.append(f"⚠️ 偵測到客廳看板底層 Node.exe 堆疊了 {zombie_node_count} 個殭屍行程！Watchdog 已發動屠魔清場並透過排程重啟看板。")
        recover_magicmirror()

    # Check 11: 平板在線狀態 (MacroDroid 前提)
    if not check_tablet_online():
        alerts.append("⚠️ 三星平板 (192.168.50.156) 離線！MacroDroid 歡迎系統可能已失效，請檢查平板電源與 Wi-Fi。")
    else:
        log("Samsung Tablet (192.168.50.156) is online.")

    # Check 12: HA 歡迎系統 Automation 心跳 (24 小時內是否有觸發過)
    ha_heartbeat_status = check_ha_welcome_heartbeat()
    if ha_heartbeat_status == 'stale':
        alerts.append("⚠️ HA 歡迎系統 Automation 超過 24 小時未觸發！MacroDroid 或 HA Companion App 可能已失效，請檢查平板上的 MacroDroid 是否正常運作。")
    elif ha_heartbeat_status == 'error':
        alerts.append("⚠️ 無法查詢 HA 歡迎系統 Automation 心跳狀態，HA API 可能異常。")
    else:
        log("HA Welcome Automation heartbeat is OK.")

    if alerts:
        # Determine if we actually did a git restore
        did_restore = any("還原回 GitHub 乾淨版本" in a for a in alerts) or any("還原" in a for a in alerts)

        msg = "\n".join(alerts)
        if did_restore:
            msg += "\n\n✅ 已根據 GitHub 乾淨版本完成自動還原！"

        # Send Telegram alert
        subprocess.run(["openclaw", "message", "send", "--channel", "telegram", "--target", "5916594299", "--message", msg])
    else:
        log("All systems normal.")

if __name__ == "__main__":
    log("Starting 24/7 Watchdog Monitoring Service (Checking every 3 minutes)...")
    while True:
        try:
            main()
        except Exception as e:
            log(f"Watchdog main loop error: {e}")
        time.sleep(180)  # 每 3 分鐘巡邏一次
