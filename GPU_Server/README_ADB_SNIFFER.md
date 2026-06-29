# ADB Welcome Sniffer

部署於 Windows GPU Server (192.168.50.154)，透過 Wireless ADB 攔截三星平板 (192.168.50.156) 上被 Android FCM Defer 的電子鎖開門通知。

## 依賴
- Python 3.10
- ADB 工具 (`C:\platform-tools\adb.exe`)
- HA 長期 Token (`C:\ha_token.txt`)

## 自動啟動
已綁定 Windows 系統工作排程器 (Task Scheduler)：
- 任務名稱：`MM_ADB_Welcome_Sniffer`
- 觸發條件：系統啟動時
- 執行身分：最高權限

## 平板重啟還原指南 (Tablet Reboot Runbook)
如果三星平板重新啟動，Wireless ADB 的 Port 會改變，連線將會中斷，導致 Sniffer 抓不到推播。請依照以下步驟恢復：
1. 點亮平板螢幕，進入「設定」 > 「開發人員選項」 > 「無線偵錯」。
2. 記下畫面上的 `IP 位址和通訊埠` (例如 `192.168.50.156:44009`)。
3. 如果尚未配對，請點擊「使用配對碼配對裝置」，使用 `adb pair 192.168.50.156:PORT PIN` 進行配對。
4. 修改 `C:\bridge_v3.py` (或 `adb_welcome_sniffer.py`) 內的 `DEV = "192.168.50.156:XXXXX"`。
5. 在 Windows 重新啟動排程：`schtasks /Run /TN MM_ADB_Welcome_Sniffer`
