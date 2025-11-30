# 台電累進費率更新說明

## 📋 更新內容

已將 Flask 後端的電費計算從固定費率改為**台電住宅用電累進費率制度**。

## 🔧 主要變更

### 1. 新增費率結構 (`TAIPOWER_RATES`)

```python
TAIPOWER_RATES = {
    "summer": [      # 夏月（6-9月）
        (120, 1.68),      # 0-120度
        (330, 2.45),      # 121-330度
        (500, 3.61),      # 331-500度
        (700, 5.03),      # 501-700度
        (1000, 6.71),     # 701-1000度
        (float('inf'), 8.01)  # 1001度以上
    ],
    "non_summer": [  # 非夏月（10-5月）
        (120, 1.68),      # 0-120度
        (330, 2.15),      # 121-330度
        (500, 2.89),      # 331-500度
        (700, 3.94),      # 501-700度
        (1000, 5.03),     # 701-1000度
        (float('inf'), 6.41)  # 1001度以上
    ]
}
```

### 2. 核心函數

#### `calculate_taiwan_bill(total_kwh, usage_date)`
- **功能**：根據累積用電量與日期計算電費
- **邏輯**：
  - 自動判斷夏月/非夏月（6-9月為夏月）
  - 使用累進方式計算電費（前120度用最低費率，依此類推）
- **回傳**：總電費（元）

#### `get_monthly_total_kwh(target_date)`
- **功能**：取得指定日期當月的累積用電量（不含當日）
- **用途**：計算新紀錄的電費時，需要知道月初到目前的用電量
- **回傳**：累積度數（kWh）

### 3. 更新的 API 端點

#### `POST /add` - 新增用電紀錄
**變更前**：
```python
cost = kwh * fixed_rate  # 固定費率
```

**變更後**：
```python
# 1. 取得當月累積用電量（不含本筆）
month_total_before = get_monthly_total_kwh(day)

# 2. 計算加入本筆後的累積量
month_total_after = month_total_before + kwh

# 3. 計算電費差額（累進計算）
bill_before = calculate_taiwan_bill(month_total_before, day)
bill_after = calculate_taiwan_bill(month_total_after, day)
cost = bill_after - bill_before  # 本筆的實際電費
```

**新增回傳資訊**：
```json
{
  "ok": true,
  "new_data": { ... },
  "month_info": {
    "month_total_kwh_before": 250.5,
    "month_total_kwh_after": 255.6,
    "cumulative_bill": 1234.56
  }
}
```

#### `GET /bill` - 取得電費統計
**新增功能**：
- 按月份分別統計
- 顯示夏月/非夏月標記
- 顯示使用的計費方式

**回傳範例**：
```json
{
  "total_kwh": 1250.5,
  "total_cost": 5678.90,
  "billing_method": "台電累進費率",
  "months": [
    {
      "month": "2025-06",
      "kwh": 350.2,
      "cost": 1234.56,
      "season": "夏月"
    },
    {
      "month": "2025-07",
      "kwh": 420.3,
      "cost": 1789.34,
      "season": "夏月"
    }
  ]
}
```

## 💡 重要概念

### 累進費率的運作方式

假設夏月已用電 300 度，現在新增 100 度：

1. **計算前**：300 度的電費
   - 前 120 度：120 × 1.68 = 201.60 元
   - 121-300 度：180 × 2.45 = 441.00 元
   - 小計：642.60 元

2. **計算後**：400 度的電費
   - 前 120 度：120 × 1.68 = 201.60 元
   - 121-330 度：210 × 2.45 = 514.50 元
   - 331-400 度：70 × 3.61 = 252.70 元
   - 小計：968.80 元

3. **本次電費**：968.80 - 642.60 = **326.20 元**
   - 平均費率：326.20 / 100 = 3.26 元/度

### 為什麼不能用固定費率？

因為台電採用**累進制**，用電越多，每度電的費用越高。如果用固定費率：
- ❌ 無法反映實際電費
- ❌ 無法鼓勵節約用電
- ❌ 與台電帳單不符

使用累進費率後：
- ✅ 準確計算每筆用電的實際成本
- ✅ 反映真實的邊際費率
- ✅ 幫助使用者了解節電的經濟效益

## 🧪 測試

已提供測試檔案 `test_taipower_billing.py`，可以執行：

```powershell
cd d:\逢甲功課\大三\大三_上\軟體工程開發實務\my-website\smart-energy
python test_taipower_billing.py
```

測試內容包括：
1. 顯示完整費率表
2. 測試不同用電量的計費
3. 模擬累進計算過程

## 📝 使用範例

### API 呼叫範例

```python
import requests

# 新增用電紀錄
response = requests.post("http://localhost:5000/add", json={
    "device_id": 1,
    "kwh": 50.5,
    "day": "2025-07-15"  # 夏月
})

print(response.json())
# {
#   "ok": true,
#   "new_data": {
#     "cost": 123.45,
#     "electricity_rate": 2.44  # 平均費率
#   },
#   "month_info": {
#     "month_total_kwh_after": 300.5,
#     "cumulative_bill": 789.12
#   }
# }
```

## ⚠️ 注意事項

1. **CSV 格式兼容**：原有的 `power_logs.csv` 格式不需要改變
2. **歷史資料**：舊資料的 `electricity_rate` 欄位會被更新為平均費率
3. **日期格式**：支援字串 (`"2025-11-15"`) 或 `date` 物件
4. **費率更新**：如果台電調整費率，只需修改 `TAIPOWER_RATES` 字典

## 🎯 效益

1. **準確性**：符合台電實際計費方式
2. **即時性**：自動判斷夏月/非夏月
3. **透明性**：回傳詳細的累積資訊
4. **教育性**：幫助使用者理解節電的經濟效益

## 📚 參考資料

- [台電官網 - 電價表](https://www.taipower.com.tw/tc/page.aspx?mid=238)
- 夏月期間：每年 6 月 1 日至 9 月 30 日
- 非夏月期間：每年 10 月 1 日至隔年 5 月 31 日
