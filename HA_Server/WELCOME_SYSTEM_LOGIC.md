# 歡迎系統判斷邏輯說明 (Welcome System Logic)

> 最後更新：2026-06-26

## 系統架構

```
電子門鎖 APP → 推播通知 → 三星平板 (Vincent Pad)
                              ↓
                    Home Assistant Companion APP
                              ↓
              sensor.sm_x936b_vincent_pad_last_notification
                              ↓
                    automations.yaml (觸發 + 判斷)
                              ↓
              REST API → http://192.168.50.204:8081/welcome
                              ↓
                    客廳喇叭語音廣播 + 螢幕顯示
```

## 觸發條件 (Trigger)

- **唯一觸發源**：三星平板 `sensor.sm_x936b_vincent_pad_last_notification` 狀態變更
- **攔截條件**：通知的 **標題 (state)** 或 **內文 (android.text)** 中，包含以下任一關鍵字：
  - `用戶：`、`Vincent`、`Anna`、`Sunny`、`千晴`、`親愛的`、`Ray`

## 家人識別與名稱對照表

| 門鎖 / 雷達關鍵字 | 廣播名稱 | 備註 |
|---|---|---|
| `Vincent` | Vincent | 門鎖 + iPhone 雷達 |
| `Anna` | Anna | 門鎖 + iPhone 雷達 |
| `千晴` (門鎖) 或 `Sunny` (手機雷達) | 千晴 | 門鎖用戶名已改為「千晴」，手機雷達仍為 Sunny |
| `Ray` | Ray | 門鎖 + iPhone 雷達 |
| `親愛的` | 親愛的 | **獨立家人身分**，僅門鎖判斷 |
| `用戶：XXX` | XXX (動態擷取) | 其他訪客 (如阿公、打掃阿姨) |

### ⚠️ 重要規則
1. **「親愛的」是獨立的家人**，絕對不可與「千晴」或「Sunny」合併。
2. **「親愛的」永遠排在廣播名單的最後一位**。
3. 每個家人都是**獨立判斷**，多人同時回家時會**合併廣播**。

## 判斷優先順序

### 第一優先：門鎖通知 (door_notif)
從通知的標題 + 內文中提取人名，依序加入名單：
1. `Vincent` → 加入 "Vincent"
2. `Anna` → 加入 "Anna"
3. `Sunny` 或 `千晴` → 加入 "千晴"
4. `Ray` → 加入 "Ray"

### 第二優先：iPhone 定位雷達 (device_tracker)
補充門鎖沒抓到的同行者。條件：最近 **3 分鐘內**狀態變為 `home`。
- `device_tracker.vincent_iphone` → 補充 "Vincent"
- `device_tracker.anna_iphone` → 補充 "Anna"
- `device_tracker.sunny_iphone` → 補充 "千晴"
- `device_tracker.ray_iphone` → 補充 "Ray"

### 第三優先：動態擷取 (用戶：)
若第一、二優先都沒中，但通知中包含「用戶：」，則動態擷取冒號後的名字。

### 最後：「親愛的」永遠排最後
在所有家人都判斷完畢後，才將「親愛的」加入名單末尾。

## 廣播範例

| 情境 | 廣播內容 |
|---|---|
| Vincent 一人回家 | 「Vincent... 歡迎回家」 |
| 千晴 + 親愛的 一起回家 | 「千晴、親愛的... 歡迎回家」 |
| 全家到齊 | 「Vincent、Anna、千晴、Ray、親愛的... 歡迎回家」 |

## 2026-06-26 Code Change 摘要

### 門鎖用戶名變更 (22:08)
- **變更內容**：電子門鎖的用戶名稱從 `Sunny` 改為 `千晴`
- **影響**：門鎖推播通知內文會直接顯示「用戶：千晴」而非「用戶：Sunny」
- **程式碼相容性**：automations.yaml 同時比對 `Sunny` 和 `千晴`，無論門鎖傳來哪個都能正確攔截並廣播為「千晴」
- **手機雷達**：iPhone 定位 (`device_tracker.sunny_iphone`) 仍以 Sunny 識別，不受門鎖改名影響

### 問題根因
1. **HA Docker 卡死**：Home Assistant 從 6/24 晚間起卡死，平板斷線 (顯示「無法連線至 Home Assistant」)，所有歡迎系統完全癱瘓。
2. **門鎖通知格式變更**：門鎖 APP 更新後，推播標題變成 MAC 位址 (`設備：40EDA2AD5E40 32`)，人名移到了通知內文 (`android.text`)。原本的 automations.yaml 只檢查標題，導致比對失敗。

### 修復內容
1. **修改通知攔截邏輯**：同時檢查通知的「標題 (`state`)」和「內文 (`android.text`）」。
2. **新增「親愛的」為獨立家人**：在攔截條件與名單建立中，將「親愛的」作為獨立判斷項目加入。
3. **新增「千晴」直接比對**：除了 `Sunny`，也同時比對中文名「千晴」，避免遺漏。
4. **「親愛的」強制排序至末位**：確保在所有家人名字加入後，「親愛的」才被追加至名單最後。
5. **部署 HA Docker 自動監控**：Watchdog 新增 `192.168.50.154:8123` 存活檢測，卡死時自動遠端 `docker restart homeassistant`。
6. **每日健康報告新增 HA 檢查項目**：Cron `healthcheck:security-audit` 加入 Home Assistant 連線狀態檢測。
7. **看板重啟腳本防誤殺**：所有 `.bat` 重啟腳本中的 `taskkill /f /im node.exe` 改為精準排除 `server.js`，避免殺死 Welcome API。
