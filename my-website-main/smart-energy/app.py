# app.py
# ==========================================
# 主程式入口檔案
# 負責建立 Flask App、初始化資料庫、載入功能模組、啟動伺服器
# ==========================================

from flask import Flask, render_template  # 匯入 Flask 類別與模板函式
from config import Config                 # 匯入設定檔 (包含資料庫與信箱設定)
from models import db                     # 匯入資料庫物件 (SQLAlchemy)
from index import register_all_features   # 從 index.c 匯入功能註冊函式

# ------------------------------------------
# 函式名稱：create_app()
# 用途：建立並回傳 Flask 應用程式物件
# ------------------------------------------
def create_app():
    app = Flask(__name__)                 # 建立 Flask 應用程式物件
    app.config.from_object(Config)        # 載入 Config 類別中的設定

    db.init_app(app)                      # 初始化資料庫物件
    with app.app_context():               # 啟動應用程式上下文
        db.create_all()                   # 建立所有模型對應的資料表 (若不存在)

    register_all_features(app)            # 呼叫 index.c 中的函式來註冊所有功能模組

    # UI 路由：呈現剛建立的前端模板（與 API 分離）
    @app.route('/ui/device')
    def ui_device():
        return render_template('device_control.html')

    @app.route('/ui/usage')
    def ui_usage():
        return render_template('usage_daily.html')

    @app.route('/ui/auto')
    def ui_auto():
        return render_template('auto_decide.html')

    @app.route("/")                       # 建立首頁路由
    def index():
        return render_template("index.html")  # 顯示首頁模板

    return app                            # 回傳建立好的 Flask 應用程式

# ------------------------------------------
# 主執行區域
# ------------------------------------------
if __name__ == "__main__":
    app = create_app()                    # 呼叫函式建立 Flask 應用
    app.run(debug=True)                   # 啟動伺服器（debug 模式開啟）
