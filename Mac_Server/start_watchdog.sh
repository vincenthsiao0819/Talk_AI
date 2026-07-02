#!/bin/bash
# 統一管理的 Watchdog 啟動腳本
# 確保每次啟動前先殺死舊的 Watchdog 行程，防止多重分身 (Session leak) 吃光資源

HERMES_SCRIPT="/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/hermes_watchdog.py"
HERMES_LOG="/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/hermes_watchdog.log"
LIVING_SCRIPT="/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/living_room_watchdog.py"
LIVING_LOG="/Users/vincenthsiao/.openclaw/workspace/Talk_AI/Mac_Server/watchdog.log"

echo "Terminating existing watchdog processes..."
pkill -f "living_room_watchdog.py" || true
pkill -f "hermes_watchdog.py" || true
sleep 2

echo "Verifying no leftover watchdog processes..."
pgrep -f "hermes_watchdog.py" && echo "Warning: Hermes survived!"
pgrep -f "living_room_watchdog.py" && echo "Warning: Living Room survived!"

echo "Starting new Hermes watchdog process in background..."
nohup python3 "$HERMES_SCRIPT" > "$HERMES_LOG" 2>&1 &

echo "Starting new Living Room watchdog process in background..."
nohup python3 "$LIVING_SCRIPT" > "$LIVING_LOG" 2>&1 &

echo "Watchdogs started successfully."
