# 客廳語音看板系統 - 健康度檢測腳本 (Healthcheck Runbook)

這份文件記錄了如何透過 SSH 遠端驗證 192.168.50.204 客廳系統的健康度。可以被 Cron 排程或 OpenClaw 直接調用。

## 1. 核心行程存活檢查 (Process Check)
必須確保以下三個關鍵進程活著：
*   **Electron (MagicMirror):** `wmic process where "name='electron.exe'" get processid`
*   **Node.js (Server API):** `wmic process where "name='node.exe' and commandline like '%server.js%'" get processid`
*   **Python (Ears.py):** `wmic process where "name='python.exe' and commandline like '%ears.py%'" get processid`

## 2. 自動重啟防護網測試 (Self-Healing)
強制終止 ears.py，確保批次檔能將它救活：
```bash
# 取得 PID 並砍除
PID=$(sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "wmic process where \"name='python.exe' and commandline like '%ears.py%'\" get processid | findstr [0-9]")
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "taskkill /f /pid $PID"

# 等待 4 秒後檢查是否產生新 PID
sleep 4
NEW_PID=$(sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "wmic process where \"name='python.exe' and commandline like '%ears.py%'\" get processid | findstr [0-9]")
```

## 3. UI 與語音連動測試 (API & UI Check)
透過 API 觸發看板黑幕與發聲，並檢驗 PowerShell 進程是否順利彈出：
```bash
# 測試 AI 對話視窗
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 'curl -s -X POST http://127.0.0.1:8081/speak -H "Content-Type: application/json" -d "{\"userText\":\"健康檢查\",\"text\":\"測試完畢\"}"'
# 驗證 PowerShell 是否啟動 Welcome_Chat
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "wmic process where \"name='powershell.exe' and commandline like '%Welcome_Chat%'\" get processid"

# 測試門禁歡迎視窗
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 'curl -s "http://127.0.0.1:8081/welcome?name=%E6%B8%AC%E8%A9%A6"'
# 驗證 PowerShell 是否啟動 Welcome
sshpass -p 6611 ssh -o StrictHostKeyChecking=no magic@192.168.50.204 "wmic process where \"name='powershell.exe' and commandline like '%Welcome.ps1%'\" get processid"
```
