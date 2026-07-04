import re
with open('/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/living_room_watchdog.py', 'r') as f:
    content = f.read()

# We want to comment out the ADB check in the main loop
content = re.sub(r'(if not check_adb_sniffer\(\):)', r'# \1', content)
content = re.sub(r'(log\("ADB Sniffer is down, restarting..."\))', r'# \1', content)
content = re.sub(r'(subprocess\.run\(SSH_154_CMD \+ \["schtasks", "/run", "/tn", "MM_ADB_Welcome_Sniffer"\]\))', r'# \1', content)

with open('/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/living_room_watchdog.py', 'w') as f:
    f.write(content)
