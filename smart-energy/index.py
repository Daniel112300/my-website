# index.py
# ==========================================
# 功能調度檔案（主控程式）
# 功能：統一載入並註冊所有 Flask 功能模組
# 每個功能模組都是一個獨立的檔案（feature_*.py）
# ==========================================

from flask import Flask                   # 匯入 Flask 類別，用來建立主應用程式
from models import db                     # 匯入資料庫物件 (SQLAlchemy)

# ------------------------------------------
# 匯入各功能模組的 Blueprint（藍圖）
# Blueprint 是 Flask 用來模組化路由的機制
# 每個模組由不同同學負責維護
# ------------------------------------------
from feature_device_control import bp as device_bp   # 功能1：電器開關與遠端控制
from feature_daily_usage import bp as usage_bp       # 功能2：每日用電與電費統計
from feature_temp_auto import bp as temp_bp          # 功能3：溫度判斷與自動開關
from feature_simulator import bp as simulator_bp     # 功能4：資料模擬器


# ------------------------------------------
# 函式名稱：register_all_features()
# 用途：將所有 Blueprint 模組註冊進 Flask 主應用
# 呼叫時機：由 app.py 中 create_app() 呼叫
# ------------------------------------------
def register_all_features(app: Flask):
    # 掛載 功能1：電器控制模組
    app.register_blueprint(device_bp, url_prefix="/device")

    # 掛載 功能2：每日用電與電費統計模組
    app.register_blueprint(usage_bp, url_prefix="/usage")

    # 掛載 功能3：溫度自動判斷模組
    app.register_blueprint(temp_bp, url_prefix="/auto")
    
    # 掛載 功能4：資料模擬器模組
    app.register_blueprint(simulator_bp, url_prefix="/simulate")


    # 備註：
    # 若日後新增功能模組，只要：
    # ① 在此檔案頂端匯入新模組 (from feature_xxx import bp as xxx_bp)
    # ② 在此函式內再 app.register_blueprint(xxx_bp, url_prefix="/xxx")
    # 就能讓新功能自動掛進系統。
