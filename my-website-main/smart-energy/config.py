# config.py
import os

class Config:    
    # MySQL 資料庫連線設定
    # 
    # XAMPP 預設設定：
    # 帳號: root
    # 密碼: (空)
    # 主機: localhost
    # 資料庫: smart_home_db
    # 
    # 連線格式：mysql+pymysql://使用者名稱:密碼@主機位址/資料庫名稱
    # 
    # 範例：
    # - XAMPP (本地，空密碼): "mysql+pymysql://root:@localhost/smart_home_db"
    # - 本地 MySQL (有密碼): "mysql+pymysql://root:12345@localhost/smart_home_db"
    # - 遠端 MySQL: "mysql+pymysql://username:password@192.168.1.150/smart_home_db"
    
    # 預設使用 XAMPP 本地設定（空密碼）
    DEFAULT_DB_URI = "mysql+pymysql://root:@localhost/smart_home_db"
    
    # 如果環境變數有設定，優先使用環境變數
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or DEFAULT_DB_URI
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False