# 🎯 智慧家庭資料模擬器使用指南

## 📋 目錄
1. [系統概述](#系統概述)
2. [運作原理](#運作原理)
3. [API 使用說明](#api-使用說明)
4. [實際操作範例](#實際操作範例)
5. [參數調整指南](#參數調整指南)
6. [常見問題](#常見問題)

---

## 🎪 系統概述

### 為什麼需要資料模擬器？

在智慧家庭系統開發過程中，**不需要一開始就購買硬體**。資料模擬器可以：

✅ **快速開發**: 不用等待硬體採購，立即開始開發與測試  
✅ **成本節省**: 前期開發完全免費，驗證可行性後再投入硬體  
✅ **壓力測試**: 輕鬆生成數千筆資料，測試系統效能  
✅ **邊界測試**: 模擬極端情境（超高溫、超低耗電等）  
✅ **團隊協作**: 所有成員都能使用相同的測試資料  

### 何時需要真實硬體？

- ✨ 需要驗證感測器整合
- ✨ 測試實際的網路延遲與斷線情境
- ✨ 展示或法規要求真實數據
- ✨ 實際部署到用戶家中

---

## 🧠 運作原理

### 1️⃣ 電量模擬邏輯

模擬器根據以下因素計算設備用電量：

```
實際用電量 = 額定功率 × 功率因數 × 使用時數 × 季節因子 × 溫度因子
```

#### **設備行為模型**

系統為每種設備類型定義了行為設定檔：

**冷氣 (air_conditioner)**
- 基礎使用時數: 4-10 小時/天
- 尖峰時段: 13-15, 19-22 點
- 使用機率: 70%
- 功率因數: 60%-95% (壓縮機啟停)
- 季節因子:
  - 夏季 (6-9月): 120%（使用率高）
  - 春秋季: 30-40%
  - 冬季: 80%（暖氣需求）
- 溫度影響:
  - >28°C: 使用時數 × 1.5
  - 25-28°C: 使用時數 × 1.2
  - <20°C: 使用時數 × 0.5

**燈具 (light)**
- 基礎使用時數: 3-8 小時/天
- 尖峰時段: 6-7, 18-23 點
- 使用機率: 95%（幾乎每天使用）
- 功率因數: 90%-100%（LED 穩定）
- 季節因子:
  - 夏季: 80%（日照長）
  - 冬季: 130%（日照短）
  - 春秋: 100%

#### **隨機性與真實感**

- 每個數值都加入 **隨機雜訊**，避免過於規律
- 使用 **機率模型** 決定設備是否當日使用
- 功率因數變化模擬 **設備老化** 與負載變化

---

### 2️⃣ 溫度模擬邏輯

#### **室外溫度**

使用 **正弦波模型** 模擬日夜溫差：

```
室外溫度 = 月平均溫度 + 日夜振幅 × sin((時刻-4)/12 × π) + 隨機雜訊
```

- **月平均溫度** (台灣氣候):
  - 1月: 16°C, 2月: 17°C, ..., 7月: 31°C, 8月: 31°C
- **日夜振幅**: ±6°C
- **最熱時刻**: 下午 2 點
- **最冷時刻**: 清晨 4 點
- **隨機雜訊**: ±2°C

#### **室內溫度**

考慮建築隔熱與空調影響：

```
室內溫度 = 室外溫度 × 0.7 + 26 × 0.3 - (冷氣運轉 ? 3°C : 0°C)
```

- **隔熱因子**: 室內溫度受室外影響 70%
- **冷氣降溫**: 運轉時降低 3°C
- **舒適溫度**: 無冷氣時趨近 26°C

---

### 3️⃣ 資料存儲

模擬資料直接儲存到 `power_logs` 資料表：

| 欄位 | 說明 | 範例 |
|------|------|------|
| `device_id` | 設備 ID | 1 |
| `power_watts` | 功率（瓦） | 3200.5 |
| `hours` | 使用時數 | 6.5 |
| `log_date` | 日期 | 2025-12-01 |
| `energy_consumed` | 耗電量（度） | 20.8 |

**注意**: 
- `cost` 與 `electricity_rate` 由計費 API 自動計算
- 可加 `source_type` 欄位區分真實/模擬資料（未來擴充）

---

## 🚀 API 使用說明

模擬器提供 5 個 API 端點：

### 1. **模擬單日用電** - `POST /simulate/daily`

生成指定日期所有設備的用電記錄。

#### 請求範例

```json
POST http://localhost:5000/simulate/daily
Content-Type: application/json

{
  "date": "2025-12-01",
  "save_to_db": true,
  "seed": 12345
}
```

#### 參數說明

| 參數 | 必填 | 說明 |
|------|------|------|
| `date` | ✅ | 日期 (YYYY-MM-DD) |
| `save_to_db` | ❌ | 是否存入資料庫，預設 `false` |
| `seed` | ❌ | 隨機種子（用於可重現性） |

#### 回應範例

```json
{
  "ok": true,
  "date": "2025-12-01",
  "outdoor_temp": 25.3,
  "devices": [
    {
      "device_id": 1,
      "device_name": "客廳冷氣",
      "power_watts": 3200.5,
      "hours": 6.5,
      "kwh": 20.8,
      "simulated": true
    },
    {
      "device_id": 3,
      "device_name": "餐廳主燈",
      "power_watts": 19.5,
      "hours": 5.2,
      "kwh": 0.1014,
      "simulated": true
    }
  ],
  "total_kwh": 45.6,
  "device_count": 5,
  "saved": true,
  "saved_count": 5
}
```

---

### 2. **模擬時間範圍** - `POST /simulate/range`

批量生成一段時間的用電記錄。

#### 請求範例

```json
POST http://localhost:5000/simulate/range
Content-Type: application/json

{
  "start_date": "2025-12-01",
  "end_date": "2025-12-07",
  "save_to_db": true,
  "seed": 2025
}
```

#### 參數說明

| 參數 | 必填 | 說明 |
|------|------|------|
| `start_date` | ✅ | 開始日期 |
| `end_date` | ✅ | 結束日期 |
| `save_to_db` | ❌ | 是否存入資料庫 |
| `seed` | ❌ | 隨機種子 |

#### 回應範例

```json
{
  "ok": true,
  "start_date": "2025-12-01",
  "end_date": "2025-12-07",
  "days_simulated": 7,
  "total_records": 35,
  "total_kwh": 320.5,
  "saved": true
}
```

---

### 3. **模擬溫度** - `GET /simulate/temperature`

取得指定日期與時刻的室內外溫度。

#### 請求範例

```
GET http://localhost:5000/simulate/temperature?date=2025-12-01&hour=14&ac_running=false
```

#### 參數說明

| 參數 | 必填 | 說明 |
|------|------|------|
| `date` | ❌ | 日期，預設今天 |
| `hour` | ❌ | 時刻 (0-23)，預設 12 |
| `ac_running` | ❌ | 冷氣是否運轉，預設 `false` |

#### 回應範例

```json
{
  "ok": true,
  "date": "2025-12-01",
  "hour": 14,
  "outdoor_temp": 26.5,
  "indoor_temp": 23.2,
  "ac_running": false
}
```

---

### 4. **查看設定** - `GET /simulate/config`

取得目前的設備行為與溫度設定檔。

#### 請求範例

```
GET http://localhost:5000/simulate/config
```

#### 回應範例

```json
{
  "ok": true,
  "device_profiles": {
    "air_conditioner": {
      "base_usage_hours": [4, 10],
      "peak_hours": [13, 14, 15, 19, 20, 21, 22],
      "active_probability": 0.7,
      ...
    },
    "light": {...}
  },
  "temperature_config": {
    "base_temp": {1: 16, 2: 17, ...},
    "daily_amplitude": 6,
    ...
  }
}
```

---

### 5. **統計資料** - `GET /simulate/stats`

查看資料庫中的模擬資料統計。

#### 請求範例

```
GET http://localhost:5000/simulate/stats
```

#### 回應範例

```json
{
  "ok": true,
  "total_records": 991,
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-11-30"
  },
  "devices": [
    {
      "device_name": "客廳冷氣",
      "record_count": 210,
      "total_kwh": 4500.5
    },
    ...
  ]
}
```

---

## 💡 實際操作範例

### 🔹 範例 1: 生成單日測試資料（不存入資料庫）

**用途**: 快速測試模擬器邏輯，預覽生成結果

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/simulate/daily" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"date":"2025-12-01","save_to_db":false}'
```

---

### 🔹 範例 2: 生成 12 月整個月的資料

**用途**: 為前端開發提供完整月份測試資料

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/simulate/range" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"start_date":"2025-12-01","end_date":"2025-12-31","save_to_db":true,"seed":2025}'
```

✨ **固定 seed=2025** 確保團隊成員生成相同資料

---

### 🔹 範例 3: 填補資料缺口

**用途**: 發現 11/15-11/29 沒資料，快速補齊

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/simulate/range" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"start_date":"2025-11-15","end_date":"2025-11-29","save_to_db":true}'
```

---

### 🔹 範例 4: 測試極端氣溫情境

**用途**: 驗證冷氣在不同溫度下的行為

```powershell
# 測試炎熱天氣（35°C）
Invoke-RestMethod -Uri "http://localhost:5000/simulate/temperature?date=2025-07-15&hour=14&ac_running=false"

# 測試寒冷天氣（10°C）
Invoke-RestMethod -Uri "http://localhost:5000/simulate/temperature?date=2025-01-15&hour=4&ac_running=false"
```

---

### 🔹 範例 5: 使用 JavaScript 前端整合

```javascript
// 生成今天的資料
async function simulateToday() {
  const today = new Date().toISOString().split('T')[0];
  
  const response = await fetch('http://localhost:5000/simulate/daily', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      date: today,
      save_to_db: true
    })
  });
  
  const data = await response.json();
  console.log(`生成 ${data.device_count} 筆記錄，總用電 ${data.total_kwh} 度`);
}

// 查詢資料庫統計
async function checkStats() {
  const response = await fetch('http://localhost:5000/simulate/stats');
  const data = await response.json();
  console.log(`資料庫共有 ${data.total_records} 筆記錄`);
  console.log(`日期範圍: ${data.date_range.start} ~ ${data.date_range.end}`);
}
```

---

### 🔹 範例 6: Python 批量生成腳本

```python
import requests
from datetime import date, timedelta

# 生成 2025 年 1-12 月完整資料
def generate_full_year():
    base_url = "http://localhost:5000/simulate/range"
    
    for month in range(1, 13):
        start = date(2025, month, 1)
        
        # 計算該月最後一天
        if month == 12:
            end = date(2025, 12, 31)
        else:
            end = date(2025, month + 1, 1) - timedelta(days=1)
        
        payload = {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "save_to_db": True,
            "seed": 2025  # 固定種子
        }
        
        response = requests.post(base_url, json=payload)
        result = response.json()
        
        print(f"✅ {month}月: 生成 {result['total_records']} 筆，{result['total_kwh']:.2f} 度")

generate_full_year()
```

---

## ⚙️ 參數調整指南

### 如何調整設備行為？

編輯 `feature_simulator.py` 中的 `DEVICE_PROFILES`：

```python
DEVICE_PROFILES = {
    "air_conditioner": {
        "base_usage_hours": (6, 12),  # 改成 6-12 小時（更頻繁使用）
        "active_probability": 0.9,    # 提高使用機率到 90%
        "seasonal_factor": {
            "summer": 1.5,  # 夏季使用率更高
            ...
        }
    }
}
```

### 如何調整溫度模型？

編輯 `TEMPERATURE_CONFIG`：

```python
TEMPERATURE_CONFIG = {
    "base_temp": {
        7: 33,  # 將 7 月平均溫度提高到 33°C（極端氣候測試）
    },
    "daily_amplitude": 8,  # 日夜溫差擴大到 8°C
    "cooling_effect": 5    # 冷氣降溫效果提升到 5°C
}
```

### 常見調整情境

#### 🎯 情境 1: 模擬節能家庭

```python
"base_usage_hours": (2, 5),  # 減少使用時數
"active_probability": 0.5,   # 降低使用頻率
"power_factor": (0.5, 0.7)   # 使用較低功率模式
```

#### 🎯 情境 2: 模擬高耗能家庭

```python
"base_usage_hours": (8, 16),  # 大幅增加使用時數
"active_probability": 1.0,    # 每天都使用
"power_factor": (0.9, 1.0)    # 全功率運轉
```

#### 🎯 情境 3: 測試極端氣候

```python
TEMPERATURE_CONFIG["base_temp"] = {
    1: 5, 2: 6, ..., 7: 40, 8: 41  # 極冷冬天、極熱夏天
}
```

---

## 🔧 常見問題

### Q1: 生成的資料太規律，不夠真實？

**A**: 調整隨機範圍：

```python
"power_factor": (0.4, 1.0),  # 擴大功率變化範圍
TEMPERATURE_CONFIG["random_noise"] = 4  # 增加溫度雜訊
```

### Q2: 某個設備完全沒生成資料？

**A**: 檢查 `active_probability`：

```python
"active_probability": 0.3  # 只有 30% 機率使用，可能連續多天沒資料
```

改成 `0.8` 以上較穩定。

### Q3: 如何確保團隊成員生成相同資料？

**A**: 使用固定的 `seed`：

```json
{
  "seed": 2025,
  "start_date": "2025-01-01",
  "end_date": "2025-12-31"
}
```

相同 seed + 相同日期範圍 = 完全相同的資料

### Q4: 模擬資料會覆蓋真實資料嗎？

**A**: 會！如果該 `(device_id, log_date)` 已存在，模擬器會**更新**該記錄。

建議：
- 真實資料與模擬資料使用不同日期範圍
- 或在 `power_logs` 表新增 `source_type` 欄位區分

### Q5: 如何刪除所有模擬資料？

**A**: 使用 SQL 或新增清除 API：

```sql
-- 刪除 12 月的所有資料
DELETE FROM power_logs WHERE log_date >= '2025-12-01' AND log_date <= '2025-12-31';
```

或建立清除 API：

```python
@bp.route("/clear", methods=["DELETE"])
def clear_simulated_data():
    # 實作清除邏輯
    pass
```

### Q6: 效能問題？生成 1 年資料太慢？

**A**: 優化策略：

1. **批量插入**: 改用 `db.session.bulk_insert_mappings()`
2. **關閉自動提交**: 在迴圈外統一 commit
3. **多執行緒**: 用 `concurrent.futures` 平行處理不同月份

範例：

```python
# 原本: 每筆都 commit（慢）
for day in range(365):
    save_data(...)
    db.session.commit()

# 優化: 批量 commit（快）
for day in range(365):
    save_data(...)
db.session.commit()  # 只在最後 commit 一次
```

---

## 🎓 進階使用

### 整合計費邏輯

模擬器可直接使用 `feature_daily_usage.py` 的計費函式：

```python
from feature_daily_usage import calculate_taiwan_bill

# 在 simulate_range 中加入電費計算
total_kwh = ...  # 當月累積用電
cost = calculate_taiwan_bill(total_kwh, target_date)
```

### 結合真實硬體

當你購買硬體後（例如 ESP32 + PZEM-004T）：

1. 建立 `mqtt_listener.py` 接收真實數據
2. 在 `power_logs` 加入 `source_type` 欄位
3. 真實資料標記為 `'real'`，模擬資料標記為 `'simulated'`
4. 前端可篩選顯示不同來源的資料

---

## 📊 資料品質檢查

使用 `/simulate/stats` 驗證資料合理性：

```python
# 檢查清單
✅ 總記錄數是否符合預期（7設備 × 30天 = 210筆/月）
✅ 日期範圍是否完整
✅ 每個設備的用電量是否在合理範圍
✅ 夏季冷氣用電 > 冬季冷氣用電
✅ 燈具用電相對穩定
```

---

## 🚀 快速開始檢查清單

- [ ] 確認 Flask 伺服器已啟動
- [ ] 測試 `/simulate/config` 確認設定正確
- [ ] 使用 `/simulate/daily` 生成單日測試（不存資料庫）
- [ ] 檢查輸出是否合理
- [ ] 調整參數後重新測試
- [ ] 使用 `/simulate/range` 生成完整測試資料
- [ ] 用 `/simulate/stats` 驗證資料品質
- [ ] 整合到前端頁面

---

## 📞 支援

如有問題，請聯絡開發團隊或參考：
- `feature_daily_usage.py` - 計費邏輯
- `models.py` - 資料模型
- `前端整合指南.md` - API 文件

---

**版本**: v1.0  
**最後更新**: 2025-11-30  
**維護者**: Smart Energy 開發團隊
