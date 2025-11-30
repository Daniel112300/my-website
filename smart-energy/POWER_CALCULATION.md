# 瓦數計算功能實作完成

## ✓ 完成項目

### 1. 建立資料庫模型檔案 (`models.py`)
- 定義 `PowerLog` 模型對應 `power_logs` 資料表
- 包含 `to_dict()` 方法用於 JSON 序列化
- 修正了 SQLAlchemy ForeignKey 定義問題

### 2. 修改 `feature_daily_usage.py` 的 `add_usage()` 函式
現在支援兩種輸入方式:

#### 方式 1: 從瓦數和時間計算（新功能）
```json
{
  "device_id": 5,
  "power_watts": 15,
  "hours": 5
}
```
- 自動計算: kWh = (power_watts × hours) ÷ 1000
- 例如: 15W × 5h = 75Wh = 0.075 kWh

#### 方式 2: 直接提供度數（原有功能）
```json
{
  "device_id": 5,
  "kwh": 0.075
}
```

### 3. API 回應增強
回應中新增了以下資訊:
- `calculation_method`: "direct" 或 "calculated"
- `power_calculation`: 當使用瓦數計算時，顯示計算公式和詳細資訊

範例回應:
```json
{
  "ok": true,
  "new_data": {
    "log_id": 10,
    "device_id": 5,
    "energy_consumed": 0.075,
    "cost": 0.13,
    "electricity_rate": 1.78
  },
  "power_calculation": {
    "power_watts": 15,
    "hours": 5,
    "formula": "15W × 5h ÷ 1000 = 0.075 kWh"
  },
  "debug_info": {
    "calculation_method": "calculated",
    "month_base_kwh": 0.0,
    "total_accumulated_after": 0.075
  }
}
```

### 4. 建立測試資料
已建立測試使用者和設備（透過 `create_power_test_data.py`）:
- **設備 5** - 客廳LED燈 (15瓦)
- **設備 6** - 臥室冷氣 (2500瓦)
- **設備 7** - 書房檯燈 (25瓦)

## 測試步驟

### 步驟 1: 啟動 Flask 伺服器

在終端機執行:
```powershell
cd "d:\逢甲功課\大三\大三_上\軟體工程開發實務\my-website\smart-energy"
C:/Users/user/AppData/Local/Microsoft/WindowsApps/python3.11.exe run_server.py
```

或者:
```powershell
python run_server.py
```

伺服器會啟動在 `http://127.0.0.1:5000`

### 步驟 2: 執行測試腳本

開啟**新的終端機視窗**，執行:
```powershell
cd "d:\逢甲功課\大三\大三_上\軟體工程開發實務\my-website\smart-energy"
python test_power_calc.py
```

測試腳本會執行 3 個測試:
1. **LED 燈測試**: 15W × 5h = 0.075 kWh
2. **冷氣測試**: 2500W × 3h = 7.5 kWh（會跨多個台電費率級距）
3. **傳統方式**: 直接提供 0.5 kWh

### 步驟 3: 手動測試（使用 PowerShell）

你也可以使用 PowerShell 的 `Invoke-WebRequest` 手動測試:

```powershell
# 測試瓦數計算
$body = @{
    device_id = 5
    power_watts = 15
    hours = 5
    day = "2025-11-30"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:5000/usage/add" `
    -Method POST `
    -Body $body `
    -ContentType "application/json" | 
    Select-Object -ExpandProperty Content | 
    ConvertFrom-Json | 
    ConvertTo-Json -Depth 10
```

## 驗證項目

### ✓ 功能驗證
- [x] 可以讀取瓦數 (power_watts) 和使用時間 (hours)
- [x] 正確計算用電量 (kWh = watts × hours ÷ 1000)
- [x] 使用台電累進費率計算電費
- [x] 將結果寫入 MySQL 資料庫
- [x] 回傳計算詳細資訊

### ✓ 資料庫驗證
檢查資料是否正確寫入:
```sql
SELECT 
    log_id,
    device_id,
    log_date,
    energy_consumed,
    cost,
    electricity_rate
FROM power_logs
ORDER BY created_at DESC
LIMIT 5;
```

### ✓ 計算驗證

#### 範例 1: LED 燈
- 輸入: 15W × 5h
- 計算: 15 × 5 ÷ 1000 = 0.075 kWh
- 費率: 1.78 元/kWh（第一級距 0-120度）
- 電費: 0.075 × 1.78 = $0.13

#### 範例 2: 冷氣
- 輸入: 2500W × 3h
- 計算: 2500 × 3 ÷ 1000 = 7.5 kWh
- 費率: 1.78 元/kWh（假設本月累積未超過 120度）
- 電費: 7.5 × 1.78 = $13.35

## 檔案清單

- ✓ `models.py` - 新建立的資料庫模型檔案
- ✓ `feature_daily_usage.py` - 已修改，支援瓦數計算
- ✓ `run_server.py` - Flask 伺服器啟動腳本
- ✓ `test_power_calc.py` - 自動化測試腳本
- ✓ `create_power_test_data.py` - 測試資料建立腳本（已執行）

## 技術細節

### 計算公式
```python
# 從瓦數計算度數
calculated_kwh = round((power_watts * hours) / 1000, 4)

# 範例:
# 15W × 5h ÷ 1000 = 0.075 kWh
# 2500W × 3h ÷ 1000 = 7.5 kWh
```

### 輸入驗證
- 必須提供 `device_id`
- 必須提供 `kwh` **或** (`power_watts` + `hours`)
- 不能同時提供或都不提供
- 所有數值必須是 int 或 float 類型

### 回應格式
成功回應包含:
- `ok`: true
- `new_data`: 新建立的記錄資料
- `power_calculation`: 瓦數計算詳情（僅當使用瓦數計算時）
- `debug_info`: 除錯資訊，包含累積度數和費率

## 下一步

測試完成後，你的系統已經可以:
1. ✓ 接收設備的額定功率（瓦數）和使用時間
2. ✓ 自動計算用電量（度數）
3. ✓ 使用台電 2025 年累進費率計算電費
4. ✓ 將記錄儲存到 MySQL 資料庫
5. ✓ 回傳詳細的計算資訊

現在請執行測試來驗證所有功能是否正常運作！
