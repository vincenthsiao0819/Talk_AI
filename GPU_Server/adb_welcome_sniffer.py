#!/usr/bin/env python3
# ADB-to-HA Bridge v3 - 乾淨版，只轉發推播到 HA sensor

import subprocess, re, json, time, urllib.request
from datetime import datetime

ADB = r"C:\platform-tools\adb.exe"
DEV = "192.168.50.156:44009"
HA_API = "http://127.0.0.1:8123/api/states/sensor.sm_x936b_vincent_pad_last_notification"
TOKEN_FILE = r"C:\ha_token.txt"
LOG = r"C:\bridge.log"

ts = lambda: datetime.now().strftime("%H:%M:%S")

def log(msg):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def call_ha(state_text):
    if not state_text:
        return
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
    except:
        log("No token")
        return
    attrs = {
        "android.text": state_text,
        "android.bigText": state_text,
        "package": "com.shyh_yih.household",
        "source": "adb_bridge"
    }
    payload = json.dumps({"state": state_text, "attributes": attrs}).encode()
    req = urllib.request.Request(HA_API, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=10)
        log(f"HA updated: {state_text[:60]}")
    except Exception as e:
        log(f"HA failed: {e}")

# Init
subprocess.run([ADB, "connect", DEV], capture_output=True, timeout=10)
time.sleep(2)
log("Bridge v3 ready - waiting for door lock notification...")
call_ha("ADB_BRIDGE_READY")

last_wake = 0
last_state = ""
HEARTBEAT_COUNT = 0

while True:
    now_t = time.time()
    try:
        # ============ 方法 A: dumpsys notification ============
        r = subprocess.run(
            [ADB, "-s", DEV, "shell", "dumpsys", "notification", "--noredact"],
            capture_output=True, text=True, timeout=15
        )
        payload = ""
        raw_out = r.stdout

        # 找 shyh_yih 的 NotificationRecord
        blocks = raw_out.split('NotificationRecord(')
        for b in blocks:
            if 'pkg=com.shyh_yih.household' in b:
                title = ""
                text = ""
                
                # 最強防呆抓法：不管 dumpsys 的 String/null 結構
                # 直接在整個 notification block 裡面找「設備：...」和「用戶：...」
                m_dev = re.search(r'設備：([^\n\)]+)', b)
                m_usr = re.search(r'用戶：([^\n\)]+)', b)
                
                parts = []
                if m_dev:
                    parts.append(f"設備：{m_dev.group(1).strip()}")
                if m_usr:
                    parts.append(f"用戶：{m_usr.group(1).strip()}")
                    
                if parts:
                    payload = " | ".join(parts)
                else:
                    m = re.search(r'tick=(.*?)\)', b)
                    if m and m.group(1) not in ('null', 'None', ''):
                        payload = m.group(1).strip()
                break

        # ============ 方法 B: 廢棄（會抓到 cancel 噪音） ============
        pass

        # 有新推播且跟上次不同 -> 送 HA
        if payload and payload != last_state and payload != "--":
            last_state = payload
            call_ha(payload)
            HEARTBEAT_COUNT = 0  # 重置心跳計數

        # ============ 每 30min 確認 App 存活（不用 force-stop/monkey 避免撤銷權限） ============
        if now_t - last_wake > 1800:
            # 檢查 App 是否在跑
            r3 = subprocess.run([ADB, "-s", DEV, "shell", "pidof", "com.shyh_yih.household"],
                              capture_output=True, text=True, timeout=10)
            pid = r3.stdout.strip()
            if not pid:
                # App 沒在跑，用 am start 溫和啟動
                subprocess.run([ADB, "-s", DEV, "shell", "am", "start", "-n",
                              "com.shyh_yih.household/com.kiwik.usmartgo.MainActivity"],
                              capture_output=True, timeout=15)
                log("App was dead, restarted with am start")
            else:
                log(f"App alive (pid={pid})")
            # 確認通知權限
            subprocess.run([ADB, "-s", DEV, "shell", "pm", "grant",
                          "com.shyh_yih.household", "android.permission.POST_NOTIFICATIONS"],
                          capture_output=True, timeout=10)
            last_wake = now_t

        # ============ 每 10min 發心跳 ============
        HEARTBEAT_COUNT += 1
        if HEARTBEAT_COUNT >= 75:  # 8*75 = 600s = 10min
            HEARTBEAT_COUNT = 0
            call_ha("ADB_HEARTBEAT")

    except subprocess.TimeoutExpired:
        log("Timeout, reconnecting...")
        subprocess.run([ADB, "connect", DEV], capture_output=True, timeout=10)
    except Exception as e:
        log(f"Error: {e}")
        time.sleep(5)
    time.sleep(8)
