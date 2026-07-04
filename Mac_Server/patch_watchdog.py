import re
with open('/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/living_room_watchdog.py', 'r') as f:
    content = f.read()

new_func = """def check_adb_sniffer():
    try:
        # Check if the bridge.log has recent heartbeat
        res = subprocess.run(SSH_154_CMD + ["powershell", "-Command", "Get-Content C:\\bridge.log -Tail 20 | Select-String 'ADB_HEARTBEAT' | Select-Object -Last 1"], capture_output=True, timeout=10)
        stdout_str = res.stdout.decode('utf-8', errors='ignore').strip()
        if not stdout_str:
            return False
            
        # Parse timestamp [HH:MM:SS]
        import datetime
        import time
        m = re.search(r'\\[(\\d{2}:\\d{2}:\\d{2})\\]', stdout_str)
        if m:
            time_str = m.group(1)
            now = datetime.datetime.now()
            log_time = datetime.datetime.strptime(time_str, "%H:%M:%S").replace(year=now.year, month=now.month, day=now.day)
            
            # If log crosses midnight
            if log_time > now + datetime.timedelta(minutes=5):
                log_time -= datetime.timedelta(days=1)
                
            if (now - log_time).total_seconds() > 900:  # 15 minutes
                log("ADB Sniffer heartbeat is older than 15 minutes!")
                return False
        return True
    except Exception as e:
        log(f"ADB Sniffer Probe Error: {e}")
        return False
"""

content = re.sub(r'def check_adb_sniffer\(\):.*?return False\n', new_func, content, flags=re.DOTALL)

with open('/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/living_room_watchdog.py', 'w') as f:
    f.write(content)
