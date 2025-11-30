# MySQL 資料庫設定說明

## 📋 前置準備

### 1. 安裝 MySQL
- 下載並安裝 [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)
- 或使用 XAMPP / WAMP 等整合套件

### 2. 安裝 Python 套件
```powershell
pip install pymysql
```

### 3. 啟動 MySQL Server
- Windows: 在服務中啟動 MySQL80 服務
- XAMPP: 啟動 MySQL 模組
- 確認 MySQL 在 localhost:3306 運行

---

## 🚀 初始化資料庫 (三步驟)

### 步驟 1: 修改 MySQL 連線設定
編輯 `config.py`，根據你的 MySQL 設定修改連線字串：

```python
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://使用者名稱:密碼@主機/資料庫名稱"
```

**常見設定範例:**
- 預設 (無密碼): `mysql+pymysql://root:@localhost/smart_home_db`
- 有密碼: `mysql+pymysql://root:password123@localhost/smart_home_db`
- 自訂帳號: `mysql+pymysql://myuser:mypass@localhost/smart_home_db`

### 步驟 2: 執行資料庫初始化腳本
```powershell
cd smart-energy
python init_mysql_db.py
```

這會執行 `smart_home_db.sql`，自動建立:
- ✓ 資料庫 `smart_home_db`
- ✓ 4 個資料表 (users, devices, device_status, power_logs)
- ✓ 測試資料

### 步驟 3 (選用): 遷移 SQLite 舊資料
如果你之前使用 SQLite 並有資料需要保留:

```powershell
python migrate_sqlite_to_mysql.py
```

這會將 `instance/smart_home.db` 的資料複製到 MySQL。

---

## ✅ 驗證資料庫

### 方法 1: 使用測試腳本
```powershell
python test_database.py
```

### 方法 2: 使用 MySQL 命令列
```sql
mysql -u root -p
USE smart_home_db;
SHOW TABLES;
SELECT * FROM power_logs;
```

### 方法 3: 使用 GUI 工具
- [MySQL Workbench](https://dev.mysql.com/downloads/workbench/)
- [phpMyAdmin](https://www.phpmyadmin.net/) (如果使用 XAMPP)
- [DBeaver](https://dbeaver.io/)

---

## 🔧 資料庫結構

### 資料表說明

| 資料表 | 說明 | 主要欄位 |
|--------|------|----------|
| `users` | 使用者帳號 | user_id, username, password_hash, email, role |
| `devices` | 智慧家電設備 | device_id, user_id, device_name, device_type, rated_power |
| `device_status` | 設備即時狀態 | status_id, device_id, is_on, current_temperature, mode |
| `power_logs` | 電力使用記錄 | log_id, device_id, log_date, energy_consumed, cost |

### 預設測試資料

**使用者:**
- xiaoming (一般使用者)
- admin_user (管理員)

**設備:**
- Device 1: 客廳冷氣 (3.5 kW)
- Device 2: 臥室冷氣 (2.8 kW)
- Device 3: 餐廳主燈 (0.02 kW)

---

## 🐛 常見問題排解

### 問題 1: 無法連線到 MySQL
**錯誤訊息:** `Can't connect to MySQL server`

**解決方法:**
1. 確認 MySQL 服務已啟動
2. 檢查防火牆設定
3. 確認連接埠 3306 未被占用

### 問題 2: Access denied for user
**錯誤訊息:** `Access denied for user 'root'@'localhost'`

**解決方法:**
1. 確認密碼正確
2. 修改 `config.py` 和 `init_mysql_db.py` 中的密碼設定
3. 確認帳號有建立資料庫的權限

### 問題 3: Unknown database 'smart_home_db'
**錯誤訊息:** `Unknown database 'smart_home_db'`

**解決方法:**
重新執行 `init_mysql_db.py` 建立資料庫

### 問題 4: 套件缺少錯誤
**錯誤訊息:** `No module named 'pymysql'`

**解決方法:**
```powershell
pip install pymysql
```

---

## 📝 與 SQLite 的差異

| 項目 | SQLite | MySQL |
|------|--------|-------|
| 檔案 | instance/smart_home.db | MySQL Server |
| 連線字串 | `sqlite:///smart_home.db` | `mysql+pymysql://root:@localhost/smart_home_db` |
| 部署 | 單一檔案，易於攜帶 | 需要 MySQL Server |
| 效能 | 適合小型應用 | 適合多人使用、大量資料 |
| 並發 | 有限制 | 支援高並發 |

---

## 🔄 切換回 SQLite (如需要)

如果想切換回 SQLite，只需修改 `config.py`:

```python
SQLALCHEMY_DATABASE_URI = "sqlite:///smart_home.db"
```

---

## 📞 聯絡資訊

如有問題，請聯繫開發團隊。
