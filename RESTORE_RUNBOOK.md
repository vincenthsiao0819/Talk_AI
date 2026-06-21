# 🦞 Living Room Talk AI - 災難復原手冊 (Runbook)

此包包含 2026-06-21 最終調校完成的客廳語音助理 (STT + TTS + 螢幕黑幕顯示) 全套程式碼。

## 📁 檔案說明
*   `ears_lobster.py`: 核心監聽程式，包含 Hey Lobster 喚醒詞、Whisper 語音辨識、防呆 Timeout 與 Google STT 備援機制。
*   `hey_lobster.onnx`: 透過 openWakeWord 訓練出來的神經網路喚醒模型。
*   `server_remote.js`: 跑在 8081 port 的 Express 伺服器，負責接收 Mac 傳來的回答，產生 Edge TTS 語音並觸發畫面。
*   `Welcome_Chat.ps1`: 負責在 27 吋螢幕上蓋上一層黑幕，並以超大字體顯示你與 Lobster 的對話，播報完自動消失。
*   `Welcome.ps1`: 原始的家人回家歡迎畫面腳本 (備份防走鐘)。
*   `start_ears.bat` / `start_ears.vbs`: 用來開機自啟與崩潰自動重啟的守護腳本。

## 🛠️ 災難還原步驟

如果 192.168.50.204 (MagicMirror主機) 系統掛掉，或是程式碼被改壞，請依照以下步驟直接覆蓋：

1.  **上傳核心程式：**
    ```bash
    scp ears_lobster.py magic@192.168.50.204:C:/Users/magic/WelcomeAPI/ears.py
    scp server_remote.js magic@192.168.50.204:C:/Users/magic/WelcomeAPI/server.js
    scp Welcome_Chat.ps1 magic@192.168.50.204:C:/Users/magic/WelcomeAPI/Welcome_Chat.ps1
    scp Welcome.ps1 magic@192.168.50.204:C:/Users/magic/WelcomeAPI/Welcome.ps1
    scp start_ears.bat magic@192.168.50.204:C:/Users/magic/WelcomeAPI/start_ears.bat
    scp start_ears.vbs magic@192.168.50.204:C:/Users/magic/WelcomeAPI/start_ears.vbs
    ```
    *(密碼為 `6611`)*

2.  **上傳喚醒詞模型：**
    ```bash
    scp hey_lobster.onnx magic@192.168.50.204:C:/Users/magic/WelcomeAPI/models/hey_lobster.onnx
    ```

3.  **重啟服務：**
    *   砍掉現有的 ears.py: `taskkill /f /im python.exe`
    *   砍掉現有的 server.js: `taskkill /f /im node.exe` (注意這可能會連 MagicMirror 本身一起砍，需確認)
    *   重新執行 `C:\Users\magic\WelcomeAPI\start_api.bat` 啟動 Node.js 伺服器
    *   重新執行 `C:\Users\magic\WelcomeAPI\start_ears.vbs` 啟動耳朵監聽

## ⚠️ 注意事項
*   `ears_lobster.py` 裡面寫死了 OpenAI 的 API Key (sk-proj...TeMA)，如果未來金鑰失效，請記得更新檔案內的 `OPENAI_API_KEY` 變數。
*   `Welcome_Chat.ps1` 必須保持極簡的全螢幕 Label 排版，不要使用 `TableLayoutPanel`，否則會導致 PowerShell 背景解析失敗無法彈出。
