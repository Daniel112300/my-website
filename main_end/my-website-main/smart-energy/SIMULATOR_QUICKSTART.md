# 🚀 模擬器快速上手指南

## 第一步：啟動伺服器

```powershell
cd "d:\逢甲功課\大三\大三_上\軟體工程開發實務\my-website\smart-energy"
python app.py
```

看到以下訊息表示成功：
```
* Running on http://127.0.0.1:5000
```

⚠️ **重要提醒**：
- ❌ 啟動伺服器**不會**自動產生數據
- ❌ 重啟伺服器**不會**增加新天數
- ✅ 需要**手動呼叫** API 才會產生數據

---

## 第二步：測試模擬器（3 個最常用指令）

### 1️⃣ 預覽單日資料（不存資料庫）

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/simulate/daily" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"date":"2025-12-15","save_to_db":false}' | ConvertTo-Json -Depth 10
```

✅ **看到什麼**: 
- 5-7 個設備的模擬用電記錄
- 室外溫度（例如 23.4°C）
- 總用電量（例如 35.9 kWh）

---

### 2️⃣ 生成一週資料並存入資料庫

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/simulate/range" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"start_date":"2025-12-01","end_date":"2025-12-07","save_to_db":true}' | ConvertTo-Json
```

✅ **看到什麼**:
```json
{
  "days_simulated": 7,
  "total_records": 35,  // 7天 × 5設備 = 35筆
  "total_kwh": 250.5,
  "saved": true
}
```

---

### 3️⃣ 驗證資料已存入

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/usage/daily?start_date=2025-12-01&end_date=2025-12-07" | ConvertTo-Json -Depth 10
```

✅ **看到什麼**: 每日用電明細 + 台電累進費率電費

---

## 第三步：常見應用場景

### 場景 A: 前端開發需要測試資料

```powershell
# 生成整個 12 月
Invoke-RestMethod -Uri "http://localhost:5000/simulate/range" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"start_date":"2025-12-01","end_date":"2025-12-31","save_to_db":true,"seed":2025}'
```

💡 **seed=2025** 確保所有組員生成相同資料

---

### 場景 B: 測試夏季高溫用電

```powershell
# 生成 7 月（夏季費率）
Invoke-RestMethod -Uri "http://localhost:5000/simulate/range" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"start_date":"2025-07-01","end_date":"2025-07-31","save_to_db":true}'

# 查看 7 月電費（應該比 12 月高）
Invoke-RestMethod -Uri "http://localhost:5000/usage/monthly/2025/7"
```

---

### 場景 C: 測試溫度對冷氣的影響

```powershell
# 測試 35°C 高溫
Invoke-RestMethod -Uri "http://localhost:5000/simulate/temperature?date=2025-07-20&hour=14&ac_running=false"

# 測試冷氣開啟效果
Invoke-RestMethod -Uri "http://localhost:5000/simulate/temperature?date=2025-07-20&hour=14&ac_running=true"
```

---

## 第四步：理解模擬邏輯

### 🔹 冷氣用電規則
- **夏季（6-9月）**: 使用率 120%，耗電量高
- **高溫天氣（>28°C）**: 使用時數 × 1.5
- **功率變化**: 60%-95%（模擬壓縮機啟停）

### 🔹 燈具用電規則
- **冬季（12-2月）**: 使用率 130%（日照短）
- **夏季（6-9月）**: 使用率 80%（日照長）
- **尖峰時段**: 18:00-23:00

### 🔹 溫度計算
```
室外溫度 = 月平均 + 6°C × sin((時刻-4)/12 × π) + 隨機雜訊
室內溫度 = 室外溫度 × 0.7 + 26°C × 0.3 - (開冷氣?3°C:0°C)
```

---

## 疑難排解

### ❌ 錯誤：`Connection refused`
**原因**: Flask 伺服器未啟動  
**解法**: 執行 `python app.py`

### ❌ 資料太規律、不真實
**原因**: 隨機範圍太小  
**解法**: 編輯 `feature_simulator.py`，調大 `power_factor` 範圍：
```python
"power_factor": (0.4, 1.0)  # 從 (0.6, 0.95) 改成更大範圍
```

### ❌ 某個設備完全沒資料
**原因**: `active_probability` 太低  
**解法**: 提高使用機率：
```python
"active_probability": 0.9  # 從 0.7 改成 0.9
```

---

## 📚 完整文件

詳細說明請參考：
- **SIMULATOR_GUIDE.md** - 完整運作原理與進階用法
- **前端整合指南.md** - 所有 API 文件
- **API使用指南.md** - 計費與統計 API

---

## ✅ 快速檢查清單

- [ ] Flask 伺服器已啟動（port 5000）
- [ ] 測試 `/simulate/daily` 預覽資料
- [ ] 測試 `/simulate/range` 生成 3 天資料
- [ ] 用 `/usage/daily` 確認資料已存入
- [ ] 用 `/simulate/temperature` 測試溫度模擬
- [ ] 閱讀 SIMULATOR_GUIDE.md 理解原理

---

## 💡 重要觀念澄清

### ❓ 模擬器會自動產生數據嗎？
**❌ 不會！** 執行 `python app.py` 只會：
- ✅ 啟動 HTTP 伺服器
- ✅ 註冊 API 路由
- ✅ 連接資料庫
- ❌ **不會**自動產生數據
- ❌ **不會**自動呼叫模擬器
- ❌ **不會**定時增加記錄

### 📊 數據何時產生？
只有在您**手動呼叫 API** 時：
```powershell
# 這時才會產生數據並寫入資料庫
POST /simulate/daily {"date": "2025-12-01", "save_to_db": true}
POST /simulate/range {"start_date": "2025-12-01", "end_date": "2025-12-07", "save_to_db": true}
```

### 🔄 模擬數據與真實數據
- ✅ 模擬器寫入的是**真實的資料庫記錄**
- ✅ `/usage/daily` **會顯示**模擬器產生的數據
- ✅ 系統**無法區分**數據來源（都存在 `power_logs` 表）
- ⚠️ 模擬數據會與真實數據**混在一起**

### 📅 `/usage/daily` 預設顯示範圍
- 📌 **預設**：今天往前推 7 天（共 7 天）
- 📌 今天是 11/30 → 顯示 11/24 ~ 11/30
- ⚠️ 即使資料庫有 12 月數據，預設**不會顯示**
- ✅ 需要手動指定 `?start_date=2025-12-01&end_date=2025-12-07`

---

**版本**: v1.1  
**作者**: Smart Energy 開發團隊  
**更新日期**: 2025-11-30
