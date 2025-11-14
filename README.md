# my-website
## Smart Energy（Flask）

多人協作骨架。每個功能一支檔案，統一由 `index.py` 掛載。

## 目錄

- 入口：`app.py`

- 功能總控：`index.py`

- 模型：`models.py`

- 設定：`config.py`

- 功能檔：

  - `feature_device_control.py`（電器控制）

  - `feature_daily_usage.py`（用電/電費）

  - `feature_temp_auto.py`（溫度自動控制）

- 前端：`templates/`、`static/`

## 快速開始（Windows / PowerShell）

```powershell
# 1) 進入專案
cd smart-energy

# 2) 建立 & 啟動虛擬環境（任一可）
python -m venv .venv

# PowerShell 可能沒有 Activate.ps1，就用 cmd 版本：
cmd /k ".\.venv\Scripts\activate.bat"

# 3) 安裝套件
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4) 先用 SQLite 跑起來（config.py 已支援）
# 若要改 MySQL，往下看設定說明
python app.py

開啟瀏覽器：http://127.0.0.1:5000/
```
