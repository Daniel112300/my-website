# 📊 資料模擬器系統說明

## 🎯 系統已完成的功能

### ✅ 1. 核心模擬邏輯 (`feature_simulator.py`)
- **電量模擬**: 根據設備類型、季節、溫度、使用時段模擬真實用電行為
- **溫度模擬**: 正弦波模型模擬日夜溫差、室內外溫度、冷氣降溫效果
- **隨機性**: 加入功率因數變化、隨機雜訊，避免資料過於規律
- **設備行為設定檔**: 冷氣與燈具各有獨立的使用模式

### ✅ 2. API 端點（已註冊到 `/simulate`）
| 端點 | 方法 | 功能 |
|------|------|------|
| `/simulate/daily` | POST | 模擬單日所有設備用電 |
| `/simulate/range` | POST | 批量生成時間範圍資料 |
| `/simulate/temperature` | GET | 查詢指定時刻的溫度 |
| `/simulate/config` | GET | 查看當前設備行為設定 |
| `/simulate/stats` | GET | 資料庫統計資訊 |

### ✅ 3. 資料庫整合
- 直接存入 `power_logs` 資料表
- 新增 `EnvironmentLog` 模型（供未來擴充）
- 與現有計費系統完全相容

### ✅ 4. 文件系統
- **SIMULATOR_GUIDE.md**: 完整運作原理（17 頁）
- **SIMULATOR_QUICKSTART.md**: 3 分鐘快速上手
- 包含 PowerShell、JavaScript、Python 範例

---

## 🧪 測試結果

### ✅ 測試 1: 單日模擬（預覽模式）
```powershell
POST /simulate/daily
Body: {"date":"2025-12-01","save_to_db":false,"seed":2025}
```

**結果**: 
- ✅ 5 個設備生成記錄
- ✅ 室外溫度 23.4°C（符合 12 月平均）
- ✅ 總用電 35.9 kWh（合理範圍）
- ✅ 功率、時數、kWh 計算正確

---

### ✅ 測試 2: 時間範圍模擬（存入資料庫）
```powershell
POST /simulate/range
Body: {"start_date":"2025-12-01","end_date":"2025-12-03","save_to_db":true}
```

**結果**:
- ✅ 3 天生成 15 筆記錄
- ✅ 資料成功存入 MySQL
- ✅ 總用電 105.6 kWh

---

### ✅ 測試 3: 整合既有 API
```powershell
GET /usage/daily?start_date=2025-12-01&end_date=2025-12-03
```

**結果**:
- ✅ 正確讀取模擬資料
- ✅ 台電累進費率計算正確
  - 12/01: 35.9 kWh → 63.94 元
  - 12/02: 35.8 kWh → 63.75 元
  - 12/03: 33.8 kWh → 60.23 元

---

### ✅ 測試 4: 溫度模擬
```powershell
GET /simulate/temperature?date=2025-07-15&hour=14
```

**結果**:
- ✅ 室外溫度 32.8°C（夏季高溫）
- ✅ 室內溫度 30.8°C（無冷氣）
- ✅ 符合正弦波模型（下午 2 點最熱）

---

## 📐 運作原理簡述

### 電量計算公式
```
實際用電量 = 額定功率 × 功率因數 × 使用時數 × 季節因子 × 溫度因子
```

### 設備行為範例（冷氣）
- **基礎時數**: 4-10 小時/天
- **夏季加成**: × 1.2
- **高溫加成**: >28°C 時 × 1.5
- **功率變化**: 60%-95%（模擬啟停）
- **使用機率**: 70%（有些天不使用）

### 溫度模型
```python
# 室外溫度
outdoor = 月平均 + 6 × sin((時刻-4)/12 × π) + 隨機(-2~2°C)

# 室內溫度
indoor = outdoor × 0.7 + 26 × 0.3 - (開冷氣 ? 3 : 0)
```

---

## 💡 使用場景

### 🎯 場景 1: 前端開發測試
**目的**: 提供完整資料讓前端同學開發圖表頁面

```powershell
# 生成 2025 年全年資料（固定種子確保一致性）
Invoke-RestMethod -Uri "http://localhost:5000/simulate/range" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"start_date":"2025-01-01","end_date":"2025-12-31","save_to_db":true,"seed":2025}'
```

---

### 🎯 場景 2: 演算法驗證
**目的**: 測試台電累進費率在不同用電量下的計算

```powershell
# 生成低用電月份（春季）
POST /simulate/range
{"start_date":"2025-03-01","end_date":"2025-03-31","seed":1001}

# 生成高用電月份（夏季）
POST /simulate/range
{"start_date":"2025-07-01","end_date":"2025-07-31","seed":1001}

# 比較電費差異
GET /usage/compare?period_type=month&date1=2025-03&date2=2025-07
```

---

### 🎯 場景 3: 壓力測試
**目的**: 測試系統處理大量資料的效能

```python
# Python 腳本：生成 10 年資料
for year in range(2015, 2025):
    for month in range(1, 13):
        requests.post("http://localhost:5000/simulate/range", json={
            "start_date": f"{year}-{month:02d}-01",
            "end_date": f"{year}-{month:02d}-28",
            "save_to_db": True
        })
```

---

### 🎯 場景 4: 極端情境測試
**目的**: 驗證系統在異常情況下的穩健性

```python
# 修改 DEVICE_PROFILES 模擬極端用電
"base_usage_hours": (20, 24),  # 24小時運轉
"power_factor": (1.0, 1.0),    # 全功率
"active_probability": 1.0       # 每天使用

# 修改 TEMPERATURE_CONFIG 模擬極端氣候
"base_temp": {7: 45, 8: 45}    # 極端高溫
```

---

## 🔧 調整參數指南

### 提高資料真實性
```python
# feature_simulator.py

# 1. 擴大功率變化範圍
"power_factor": (0.4, 1.0)  # 從 (0.6, 0.95) 改成更大

# 2. 增加溫度雜訊
TEMPERATURE_CONFIG["random_noise"] = 4  # 從 2 改成 4

# 3. 調整使用機率
"active_probability": 0.85  # 介於 0.7-0.95 之間較自然
```

---

### 模擬特定家庭類型

#### 節能家庭
```python
"air_conditioner": {
    "base_usage_hours": (2, 5),
    "active_probability": 0.5,
    "power_factor": (0.5, 0.7)
}
```

#### 高耗能家庭
```python
"air_conditioner": {
    "base_usage_hours": (8, 16),
    "active_probability": 0.95,
    "power_factor": (0.9, 1.0)
}
```

---

## 🚨 注意事項

### ⚠️ 資料覆蓋問題
模擬器會**覆蓋**已存在的 `(device_id, log_date)` 記錄。

**建議做法**:
1. 真實資料與模擬資料使用不同日期範圍
2. 或在 `power_logs` 表新增 `source_type ENUM('real','simulated')`

---

### ⚠️ 效能考量
生成大量資料時（如整年）可能較慢。

**優化方案**:
```python
# 批量插入（在 feature_simulator.py 中實作）
records = []
for day in date_range:
    records.append(generate_record(day))

db.session.bulk_insert_mappings(PowerLog, records)
db.session.commit()  # 只在最後 commit 一次
```

---

### ⚠️ 隨機種子 (seed)
- 相同 seed = 完全相同的資料（適合團隊協作）
- 不提供 seed = 每次生成不同資料（適合多次測試）

```json
// 團隊共用資料
{"seed": 2025, "start_date": "2025-01-01", ...}

// 多樣化測試
{"start_date": "2025-01-01", ...}  // 不加 seed
```

---

## 🔮 未來擴充方向

### 1. 環境資料記錄
```python
# 使用 EnvironmentLog 模型儲存溫度歷史
env_log = EnvironmentLog(
    log_datetime=datetime.now(),
    outdoor_temp=outdoor_temp,
    indoor_temp=indoor_temp,
    source_type='simulated'
)
db.session.add(env_log)
```

### 2. 真實硬體整合
```python
# mqtt_listener.py
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    # 接收 ESP32 傳來的真實數據
    data = json.loads(msg.payload)
    
    # 標記為真實資料
    log = PowerLog(
        device_id=data['device_id'],
        power_watts=data['watts'],
        source_type='real'  # 區分真實與模擬
    )
    db.session.add(log)
```

### 3. 機器學習預測
```python
# 使用模擬資料訓練預測模型
from sklearn.ensemble import RandomForestRegressor

X = df[['month', 'hour', 'outdoor_temp', 'device_type']]
y = df['kwh']

model = RandomForestRegressor()
model.fit(X, y)

# 預測明天用電量
tomorrow_usage = model.predict([[12, 14, 25, 'air_conditioner']])
```

---

## 📚 相關文件

| 文件 | 用途 | 頁數 |
|------|------|------|
| **SIMULATOR_GUIDE.md** | 完整運作原理、API 文件、進階用法 | 17 頁 |
| **SIMULATOR_QUICKSTART.md** | 3 分鐘快速上手、常用指令 | 5 頁 |
| **前端整合指南.md** | 所有 API 端點（含模擬器） | 15 頁 |
| **feature_simulator.py** | 原始碼（含詳細註解） | 620 行 |

---

## ✅ 驗收清單

### 功能驗收
- [x] 單日模擬功能正常
- [x] 批量生成功能正常
- [x] 溫度模擬功能正常
- [x] 資料成功存入資料庫
- [x] 與既有 API 整合成功
- [x] 台電費率計算正確

### 文件驗收
- [x] 運作原理說明完整
- [x] API 使用範例充足
- [x] PowerShell/JavaScript/Python 範例齊全
- [x] 參數調整指南清楚
- [x] 疑難排解方案完善

### 測試驗收
- [x] 12 月資料生成測試通過
- [x] 夏季高溫情境測試通過
- [x] 資料品質檢查通過
- [x] 電費計算驗證通過

---

## 🎓 使用建議

### 👨‍💻 給前端開發者
1. 使用 `seed=2025` 生成固定資料集
2. 先用 `/simulate/daily` 預覽，確認格式符合需求
3. 再用 `/simulate/range` 生成完整月份資料
4. 透過 `/usage/*` API 取得計費資料做圖表

### 🧪 給測試人員
1. 使用不同 seed 生成多組測試資料
2. 調整 `DEVICE_PROFILES` 測試邊界情況
3. 驗證極端氣候下的系統穩定性
4. 壓力測試：生成數年資料驗證效能

### 🔬 給演算法開發者
1. 使用模擬器快速驗證計費邏輯
2. 批量生成資料訓練機器學習模型
3. 調整參數測試不同用戶行為模式
4. 使用固定 seed 確保實驗可重現

---

## 📞 技術支援

如有問題，請參考：
- `SIMULATOR_GUIDE.md` - 詳細原理與 FAQ
- `feature_simulator.py` - 原始碼註解
- 團隊開發文件

---

---

## 🎓 常見問題 FAQ

### ❓ Q1: 執行 `python app.py` 會自動產生數據嗎？
**A:** ❌ 不會！啟動伺服器只是監聽 API 請求，不會主動產生任何數據。

### ❓ Q2: 模擬器產生的數據會出現在 `/usage/daily` 嗎？
**A:** ✅ 會！模擬器寫入的是真實資料庫記錄，與真實數據完全一樣。

### ❓ Q3: 為什麼資料庫有 12 月數據，但 `/usage/daily` 沒顯示？
**A:** 因為預設只顯示**近 7 天**（今天往前推 6 天）。需要手動指定日期範圍：
```
GET /usage/daily?start_date=2025-12-01&end_date=2025-12-07
```

### ❓ Q4: 模擬數據與真實數據會混在一起嗎？
**A:** ✅ 會！因為都存在同一個 `power_logs` 表，系統無法區分來源。

### ❓ Q5: 如何區分模擬數據和真實數據？
**A:** 目前無法自動區分。建議：
- 方案 1：真實數據和模擬數據使用不同日期範圍
- 方案 2：在 `power_logs` 表新增 `source_type ENUM('real','simulated')` 欄位

### ❓ Q6: 模擬器會定時自動產生數據嗎？
**A:** ❌ 不會！除非您自己寫排程任務（如 cron job 或 Windows Task Scheduler）定時呼叫 API。

---

**系統版本**: v1.1  
**完成日期**: 2025-11-30  
**更新日期**: 2025-11-30  
**開發團隊**: Smart Energy Backend Team  
**技術棧**: Flask + SQLAlchemy + MySQL + Python 3.11
