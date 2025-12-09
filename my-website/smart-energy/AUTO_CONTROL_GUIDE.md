# 🌡️ 自動溫度控制系統使用指南

## 📋 系統功能

### ✅ 新增功能
1. **自動讀取資料庫溫度** - 不需要手動輸入
2. **自動判斷開關冷氣** - 超過 26°C 自動開啟
3. **背景監控模式** - 每 3 分鐘自動檢查一次
4. **控制所有冷氣設備** - 同時控制多台冷氣
5. **彈性設定** - 可調整目標溫度與檢查間隔

---

## 🚀 快速開始

### 步驟 1: 啟動伺服器
```powershell
cd "d:\逢甲功課\大三\大三_上\軟體工程開發實務\my-website\smart-energy"
python app.py
```

### 步驟 2: 立即檢查一次溫度
```powershell
# 從資料庫讀取溫度並判斷是否開關冷氣
Invoke-RestMethod -Uri "http://localhost:5000/auto/check"
```

**輸出範例**：
```json
{
  "ok": true,
  "timestamp": "2025-11-30 15:30:00",
  "current_temp": 28.5,
  "target_temp": 26.0,
  "action": "turn_on",
  "reason": "Temperature 28.5°C > 26.0°C",
  "devices_controlled": [
    {
      "device_id": 1,
      "device_name": "客廳冷氣",
      "action": "turn_on",
      "success": true
    },
    {
      "device_id": 2,
      "device_name": "臥室冷氣",
      "action": "turn_on",
      "success": true
    }
  ]
}
```

### 步驟 3: 啟動自動監控（每 3 分鐘檢查）
```powershell
# 啟動背景監控
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" -Method POST
```

**輸出**：
```json
{
  "ok": true,
  "msg": "Auto monitor started",
  "interval": 180,
  "target_temp": 26.0
}
```

**伺服器會每 3 分鐘自動輸出**：
```
🌡️ Auto temperature monitor started (interval: 180s)
[2025-11-30 15:30:00] Temp: 28.5°C, Action: turn_on
[2025-11-30 15:33:00] Temp: 27.2°C, Action: turn_on
[2025-11-30 15:36:00] Temp: 25.8°C, Action: turn_off
```

---

## 📡 API 端點說明

### 1. **立即檢查溫度** - `GET /auto/check`
從資料庫讀取溫度，立即執行一次判斷並控制設備。

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/auto/check"
```

**用途**：測試功能、手動觸發一次檢查

---

### 2. **啟動自動監控** - `POST /auto/monitor/start`
啟動背景執行緒，每隔指定時間自動檢查。

```powershell
# 使用預設間隔（180 秒 = 3 分鐘）
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" -Method POST

# 自訂間隔（例如 5 分鐘 = 300 秒）
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"interval": 300}'
```

**注意**：監控會在背景持續運行，直到手動停止或伺服器重啟。

---

### 3. **停止自動監控** - `POST /auto/monitor/stop`
停止背景監控執行緒。

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/stop" -Method POST
```

---

### 4. **查看監控狀態** - `GET /auto/monitor/status`
檢查監控是否正在運行。

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/status"
```

**輸出**：
```json
{
  "ok": true,
  "enabled": true,
  "interval": 180,
  "target_temp": 26.0
}
```

---

### 5. **查看/修改設定** - `GET/POST /auto/config`

#### 查看目前設定
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/auto/config"
```

#### 修改目標溫度
```powershell
# 改成 25°C
Invoke-RestMethod -Uri "http://localhost:5000/auto/config" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"target_temp": 25.0}'
```

#### 修改檢查間隔
```powershell
# 改成每 5 分鐘（300 秒）
Invoke-RestMethod -Uri "http://localhost:5000/auto/config" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"interval": 300}'
```

---

### 6. **手動判斷** - `GET/POST /auto/decide`（原有功能保留）
手動輸入溫度進行判斷（不讀資料庫）。

```powershell
# 方式 1: URL 參數
Invoke-RestMethod -Uri "http://localhost:5000/auto/decide?temp=28"

# 方式 2: JSON Body
Invoke-RestMethod -Uri "http://localhost:5000/auto/decide" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"temp": 28}'
```

---

## 🎯 使用情境

### 情境 1: 開發測試
```powershell
# 1. 立即測試一次
Invoke-RestMethod -Uri "http://localhost:5000/auto/check"

# 2. 確認設備狀態已改變
Invoke-RestMethod -Uri "http://localhost:5000/device/state"
```

---

### 情境 2: 生產環境自動化
```powershell
# 1. 啟動伺服器
python app.py

# 2. 啟動自動監控（每 3 分鐘）
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" -Method POST

# 3. 系統會自動運行，無需人工干預
# 4. 如需停止，執行：
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/stop" -Method POST
```

---

### 情境 3: 搭配溫度模擬器
```powershell
# 1. 生成一筆環境溫度資料（未來擴充）
# 假設有 POST /simulate/environment API

# 2. 立即檢查並控制設備
Invoke-RestMethod -Uri "http://localhost:5000/auto/check"
```

---

## 🧠 運作原理

### 溫度來源優先順序

1. **EnvironmentLog 表**（如果有建立）
   - 從 `environment_logs` 表讀取最新的 `indoor_temp`
   
2. **即時模擬**（Fallback）
   - 使用模擬器根據當前時間計算溫度
   - 公式：`室內溫度 = 室外溫度 × 0.7 + 26 × 0.3`

### 判斷邏輯

```
if 目前溫度 > 目標溫度 (26°C):
    開啟所有冷氣
else:
    關閉所有冷氣
```

### 設備控制

- 自動查詢 `device_type = 'air_conditioner'` 的所有設備
- 更新 `device_status` 表的 `is_on` 欄位
- 支援同時控制多台冷氣

---

## 🔧 進階設定

### 調整目標溫度
```powershell
# 改成 24°C（更涼爽）
Invoke-RestMethod -Uri "http://localhost:5000/auto/config" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"target_temp": 24.0}'
```

### 調整檢查頻率
```powershell
# 每 1 分鐘檢查（60 秒）
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"interval": 60}'

# 每 10 分鐘檢查（600 秒）
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"interval": 600}'
```

---

## ⚠️ 注意事項

### 1. 監控會在伺服器重啟後停止
每次重啟 `python app.py` 後，需要重新啟動監控：
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" -Method POST
```

### 2. 背景執行緒是 daemon
伺服器關閉時，監控執行緒會自動停止，不會留下殭屍程序。

### 3. 溫度資料來源
- 如果沒有真實感測器資料，系統會使用模擬器計算即時溫度
- 未來可整合 MQTT 接收真實溫度感測器資料

### 4. 資料庫連線
背景執行緒會每次檢查時連接資料庫，確保使用 Flask 的 `app_context`。

---

## 🔍 疑難排解

### ❌ 錯誤：`Unable to get temperature from database`
**原因**: 沒有溫度資料來源  
**解法**: 系統會自動使用模擬器計算，這是正常的

### ❌ 監控啟動失敗
**原因**: 監控已在運行  
**解法**: 先停止再重啟
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/stop" -Method POST
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" -Method POST
```

### ❌ 設備狀態沒改變
**原因**: 設備可能不是 `air_conditioner` 類型或 `is_active=False`  
**解法**: 檢查設備資料
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/device/state"
```

---

## 📊 完整使用流程

```powershell
# 1. 啟動伺服器
python app.py

# 2. 測試立即檢查
Invoke-RestMethod -Uri "http://localhost:5000/auto/check"

# 3. 確認設備狀態改變
Invoke-RestMethod -Uri "http://localhost:5000/device/state"

# 4. 啟動自動監控（每 3 分鐘）
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/start" -Method POST

# 5. 查看監控狀態
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/status"

# 6. 如需修改設定
Invoke-RestMethod -Uri "http://localhost:5000/auto/config" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"target_temp": 25.0, "interval": 300}'

# 7. 停止監控（如需要）
Invoke-RestMethod -Uri "http://localhost:5000/auto/monitor/stop" -Method POST
```

---

## 🎓 與前端整合

### JavaScript 範例

```javascript
// 啟動自動監控
async function startAutoMonitor() {
  const response = await fetch('http://localhost:5000/auto/monitor/start', {
    method: 'POST'
  });
  const data = await response.json();
  console.log(data.msg); // "Auto monitor started"
}

// 立即檢查溫度
async function checkNow() {
  const response = await fetch('http://localhost:5000/auto/check');
  const data = await response.json();
  console.log(`目前溫度: ${data.current_temp}°C`);
  console.log(`執行動作: ${data.action}`);
}

// 查看監控狀態
async function getStatus() {
  const response = await fetch('http://localhost:5000/auto/monitor/status');
  const data = await response.json();
  return data.enabled; // true/false
}
```

---

## ✅ 驗收清單

- [ ] `/auto/check` 能讀取溫度並控制設備
- [ ] `/auto/monitor/start` 成功啟動背景監控
- [ ] 伺服器 console 每 3 分鐘顯示檢查結果
- [ ] `/device/state` 顯示設備狀態已改變
- [ ] `/auto/monitor/stop` 能成功停止監控
- [ ] `/auto/config` 能修改目標溫度與間隔

---

**版本**: v2.0  
**更新日期**: 2025-11-30  
**功能**: 自動溫度監控與設備控制
