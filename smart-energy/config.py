# config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ANY_SECRET_KEY"
    
    # XAMPP 預設設定
    # 帳號: root
    # 密碼: (空)
    # 主機: localhost
    # 資料庫: smart_home_db
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:@localhost/smart_home_db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False