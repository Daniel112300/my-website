# models.py
# ==========================================
# 負責定義資料庫模型 (資料表結構)
# ==========================================
    # 匯入 SQLAlchemy ORM
from werkzeug.security import generate_password_hash  # 匯入密碼加密函式

from flask_sqlalchemy import SQLAlchemy          
db = SQLAlchemy()                                   # 建立 SQLAlchemy 物件

# ------------------------------------------
# 類別名稱：User
# 用途：儲存使用者帳號與密碼資料
# ------------------------------------------
class User(db.Model):                               # 建立 User 資料表
    id = db.Column(db.Integer, primary_key=True)    # 主鍵
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)  # 使用者名稱
    password_hash = db.Column(db.String(256), nullable=False)  # 加密後的密碼

    def set_password(self, password: str):          # 定義設定密碼的函式
        self.password_hash = generate_password_hash(password, method="scrypt")  # 使用 scrypt 加密

# ------------------------------------------
# 類別名稱：Report
# 用途：儲存報表資料 (編號與檔名)
# ------------------------------------------
class Report(db.Model):                             # 建立 Report 資料表
    id = db.Column(db.Integer, primary_key=True)    # 主鍵
    serial = db.Column(db.String(80), unique=True, nullable=False, index=True)   # 報表序號
    filename = db.Column(db.String(120), nullable=False, index=True)             # 檔案名稱
