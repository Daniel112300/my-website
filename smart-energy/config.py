# config.py
import os
class Config:
    SECRET_KEY = "dev"
    # MySQL 資料庫連線設定
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:12345@localhost/smart_home_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 如果需要修改 MySQL 連線資訊，請修改以下格式：
    # SQLALCHEMY_DATABASE_URI = "mysql+pymysql://使用者名稱:密碼@主機位址/資料庫名稱"
    # 例如: "mysql+pymysql://root:password123@localhost/smart_home_db"

