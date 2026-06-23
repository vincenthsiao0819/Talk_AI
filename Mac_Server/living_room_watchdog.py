import subprocess
import socket
import urllib.request
import time
import base64
import sys
import os

# Secrets (Do NOT push this script to public GitHub, keep it local on Mac)
OPENAI_API_KEY = "sk-proj-7GstW6mU9qJ2Q5k4Kk3mZf0wX-tJqOq8rF6eH_R3M_l-w3zU4s2zR5eP6oV0qX1tM-yVzfwA" # Extracted from start_ears.bat

MUTE_FLAG_PATH = "/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/mute.flag"
SSH_CMD = ["sshpass", "-p", "6611", "ssh", "-o", "StrictHostKeyChecking=no", "magic@192.168.50.204"]

def log(msg):
    print(f"[Watchdog] {msg}")
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
    subprocess.run(["git", "pull"], cwd="/Users/vincenthsiao/.openclaw/workspace/HA_Welcome_home_Display_Sound", check=True)
    
    # 2. Kill existing node processes
    subprocess.run(SSH_CMD + ["wmic process where \"CommandLine LIKE '%server.js%'\" call terminate"], capture_output=True)
    
    # 3. Read clean baseline
    with open("/Users/vincenthsiao/.openclaw/workspace/HA_Welcome_home_Display_Sound/server.js", "rb") as f:
        content = f.read()
    b64_content = base64.b64encode(content).decode('utf-8')
    
    # 4. Deploy and restart
    with open("/Users/vincenthsiao/.openclaw/workspace/temp_api.b64", "w") as f:
        f.write(b64_content)
    subprocess.run(["sshpass", "-p", "6611", "scp", "-o", "StrictHostKeyChecking=no", 
                    "/Users/vincenthsiao/.openclaw/workspace/temp_api.b64", 
                    "magic@192.168.50.204:C:/Users/magic/WelcomeAPI/server.b64"])
    subprocess.run(SSH_CMD + ["certutil -f -decode C:\\Users\\magic\\WelcomeAPI\\server.b64 C:\\Users\\magic\\WelcomeAPI\\server.js"], capture_output=True)
    recover_magicmirror()

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
    recover_magicmirror()

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
    subprocess.run(["git", "restore", "server.js"], cwd="/Users/vincenthsiao/.openclaw/workspace/HA_Welcome_home_Display_Sound", check=True)
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

def check_magicmirror():
    try:
        res = subprocess.run(SSH_CMD + ["tasklist | findstr electron.exe"], capture_output=True, text=True, timeout=10)
        return "electron.exe" in res.stdout
    except Exception:
        return False

def recover_magicmirror():
    log("Recovering MagicMirror Dashboard via Full Reboot (Session boundary workaround)...")
    # Due to Windows SSH Session 0 isolation, schtasks and WMI cannot reliably launch a GUI app in Console Session 1.
    # The most robust way is to reboot the POS machine, which relies on AutoAdminLogon and mm_startup.bat.
    subprocess.run(SSH_CMD + ["shutdown /r /t 5 /f /c \"Watchdog Recovery\""], capture_output=True)
    log("Reboot command sent to 192.168.50.204. Waiting 60 seconds for it to come back up...")
    time.sleep(60)

def main():
    alerts = []
    
    # Check 1: Welcome API
    if not check_api():
        alerts.append("⚠️ Welcome API 斷線，正在從 GitHub 基準還原...")
        recover_api()
    else:
        log("Welcome API is OK.")

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
    welcome_api_status = subprocess.run(["git", "status", "--porcelain", "server.js"], cwd="/Users/vincenthsiao/.openclaw/workspace/HA_Welcome_home_Display_Sound", capture_output=True, text=True)
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

    if alerts:
        # Send Telegram alert
        msg = "\n".join(alerts) + "\n\n✅ 已根據 GitHub 乾淨版本完成自動還原！"
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
