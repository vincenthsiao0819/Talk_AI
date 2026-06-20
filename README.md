# Talk AI - 客廳語音大腦系統

這是一套基於 HP ElitePOS (Windows) 與 Jabra 喇叭所打造的「全離線喚醒、隱形發聲、突破內網」的智慧客廳大腦系統。

## 架構說明

本系統分為兩個端點：**POS_Client (客廳端)** 與 **Mac_Server (大腦端)**。

### 1. 客廳端 (POS_Client)
負責聽與說，所有服務皆具備自動重啟(無限迴圈)防護機制。
* **`ears.py` (聽覺神經)**: 
  - 使用 `openWakeWord` 進行全離線喚醒（喚醒詞：`Hey Long Xia` / `Hey Jarvis` 等）。
  - 喚醒後使用 Google STT 進行語音轉文字。
  - 將轉換後的文字透過 Port 5005 拋轉給 Mac 大腦。
* **`server.js` (發聲大腦)**: 
  - 跑在 Port 8081 的 Node.js API。
  - 接收來自 Mac 大腦的純文字，使用 Microsoft Edge TTS 生成高音質語音 (微軟曉臻)。
  - 生成 `.mp3` 後呼叫 `Welcome.ps1` 進行播放，並具備 60 秒自動清除舊音檔機制。
* **`Welcome.ps1` (隱形嘴巴)**: 
  - 負責調用 Windows Media Player COM 元件播放語音。
  - 具備 `-HideUI` 無痕模式，將視窗縮至 1x1 像素並藏於螢幕外 (-2000, -2000)，解決背景播放發不出聲音的問題，且不干擾 MagicMirror 看板畫面。
* **`start_*.bat` / `start_*.vbs`**:
  - `bat` 負責包裝成無窮迴圈，防止 API 或 Ears 閃退。
  - `vbs` 負責以隱藏視窗 (WindowStyle 0) 的方式啟動 `bat`。

### 2. 大腦端 (Mac_Server)
負責接收客廳傳來的語句，並由 OpenClaw AI 進行理解與回覆。
* **`mac_ears_listener.py`**:
  - 在 Mac 上監聽 Port 5005。接收到字串後，加上 `[客廳語音]` 標籤並觸發 `openclaw agent`。
* **`keep_ears_tunnel.sh`**:
  - 建立一條 SSH Reverse Tunnel (`-R 5005:127.0.0.1:5005`)。
  - 讓客廳端可以直接打向本地的 5005 port，無縫穿透防火牆將資料送進 Mac。

## 部署與啟動方式

1. **Mac 端**:
   - 執行 `nohup ./keep_ears_tunnel.sh &`
   - 執行 `nohup python3 mac_ears_listener.py &`
2. **POS 端**:
   - 點擊執行 `start_api.vbs` (啟動嘴巴)
   - 點擊執行 `start_ears.vbs` (啟動耳朵)

---
*Created by Vincent & OpenClaw - 2026/06/20*
