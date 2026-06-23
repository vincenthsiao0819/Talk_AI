#!/bin/bash
# 統一管理的 Watchdog 啟動腳本
# 確保每次啟動前先殺死舊的 Watchdog 行程，防止多重分身 (Session leak) 吃光資源

WATCHDOG_SCRIPT="/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/living_room_watchdog.py"
WATCHDOG_LOG="/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/watchdog.log"

echo "Terminating existing watchdog processes..."
pkill -f "living_room_watchdog.py" || true
sleep 2

echo "Verifying no leftover watchdog processes..."
pgrep -f "living_room_watchdog.py" && echo "Warning: Some processes survived!" || echo "Clean slate."

echo "Starting new watchdog process in background..."
nohup python3 "$WATCHDOG_SCRIPT" > "$WATCHDOG_LOG" 2>&1 &

echo "Watchdog started successfully."
