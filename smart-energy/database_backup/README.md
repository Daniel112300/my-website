# 資料庫備份與匯入說明

本資料夾包含 Smart Energy 系統的資料庫備份檔案，供組員快速建立開發環境使用。

## 📁 檔案說明

| 檔案名稱 | 說明 | 資料筆數 |
|----------|------|----------|
| `smart_home_db.sql` | 資料庫表格結構定義 | - |
| `users_data.sql` | 使用者帳號資料 | 4 筆 |
| `devices_data.sql` | 設備資料 | 7 筆 |
| `device_status_data.sql` | 設備狀態資料 | 2 筆 |
| `power_logs_data.sql` | 用電記錄資料 (2025年1月-11月) | 921 筆 |

## 🛠️ 環境需求

- **MySQL 8.0+** 或 **MariaDB 10.5+**
- 預設連線設定：
  - Host: `localhost`
  - Port: `3306`
  - Username: `root`
  - Password: `12345`

> ⚠️ 如果你的 MySQL 密碼不同，請修改 `smart-energy/config.py` 中的 `SQLALCHEMY_DATABASE_URI`

## 📥 匯入步驟

### 方法一：使用 MySQL 命令列

1. **開啟 MySQL 命令列**
   ```bash
   mysql -u root -p
   ```
   輸入密碼：`12345`

2. **建立資料庫**
   ```sql
   CREATE DATABASE IF NOT EXISTS smart_home_db;
   USE smart_home_db;
   ```

3. **依序匯入資料（順序很重要！）**
   ```sql
   SOURCE smart_home_db.sql;
   SOURCE users_data.sql;
   SOURCE devices_data.sql;
   SOURCE device_status_data.sql;
   SOURCE power_logs_data.sql;
   ```

### 方法二：使用 VS Code MySQL 擴充套件

1. 安裝擴充套件：`MySQL` by Weijan Chen
2. 建立連線到 `localhost:3306`
3. 右鍵點擊連線 → `New Query`
4. 輸入並執行：
   ```sql
   CREATE DATABASE IF NOT EXISTS smart_home_db;
   ```
5. 依序開啟每個 `.sql` 檔案並執行

### 方法三：使用 MySQL Workbench

1. 連線到 MySQL Server
2. 建立新資料庫 `smart_home_db`
3. 選擇該資料庫
4. `File` → `Run SQL Script...`
5. 依序選擇並執行每個 `.sql` 檔案

## ✅ 驗證匯入成功

執行以下 SQL 確認資料已匯入：

```sql
USE smart_home_db;

SELECT 'users' AS table_name, COUNT(*) AS count FROM users
UNION ALL
SELECT 'devices', COUNT(*) FROM devices
UNION ALL
SELECT 'device_status', COUNT(*) FROM device_status
UNION ALL
SELECT 'power_logs', COUNT(*) FROM power_logs;
```

預期結果：
| table_name | count |
|------------|-------|
| users | 4 |
| devices | 7 |
| device_status | 2 |
| power_logs | 921 |

## 🚀 啟動專案

匯入完成後，即可啟動 Flask 專案：

```bash
cd smart-energy
pip install -r requirements.txt
python app.py
```

然後開啟瀏覽器訪問：http://127.0.0.1:5000

## 📊 測試 API

| 功能 | 網址 |
|------|------|
| 首頁 | http://127.0.0.1:5000/ |
| 每日用電 | http://127.0.0.1:5000/usage/daily |
| 月份統計 | http://127.0.0.1:5000/usage/monthly/2025/11 |
| 年度統計 | http://127.0.0.1:5000/usage/yearly/2025 |
| 電費帳單 | http://127.0.0.1:5000/usage/bill |

## ❓ 常見問題

### Q: 出現 "Access denied for user 'root'@'localhost'"
A: 請確認 MySQL 密碼是否正確，或修改 `config.py` 中的密碼設定

### Q: 出現 "Unknown database 'smart_home_db'"
A: 請先執行 `CREATE DATABASE smart_home_db;`

### Q: 出現 "Foreign key constraint fails"
A: 請確認按照順序匯入：users → devices → device_status → power_logs

---
📅 最後更新：2025-11-30
