# app.py
from flask import Flask, render_template, redirect, url_for
from config import Config
from models import db, User
from index import register_all_features
from flask_login import LoginManager, current_user, login_required

# ------------------------------------------
# 函式名稱：create_app()
# 用途：建立並回傳 Flask 應用程式物件
# ------------------------------------------
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 必須設定 SECRET_KEY 才能使用 session (Flask-Login 依賴它)
    # 在 config.py 裡應該要有，如果沒有，這裡設一個預設值
    app.config['SECRET_KEY'] = 'dev-secret-key-change-this-in-prod'

    db.init_app(app)
    
    # 初始化 Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' # 未登入時導向的路由
    login_manager.login_message = "請先登入以存取此頁面。"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    # 註冊原本的功能模組
    register_all_features(app)
    
    # 註冊認證模組 (等一下我們會建立 feature_auth.py)
    from feature_auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # UI 路由：加上 @login_required 保護
    @app.route('/ui/device')
    @login_required
    def ui_device():
        return render_template('device_control.html')

    @app.route('/ui/usage')
    @login_required
    def ui_usage():
        return render_template('usage_daily.html')

    @app.route('/ui/auto')
    @login_required
    def ui_auto():
        return render_template('auto_decide.html')

    @app.route("/")
    def index():
        # 如果已登入，直接去電器控制頁面
        if current_user.is_authenticated:
            return redirect(url_for('ui_device'))
        return redirect(url_for('auth.login')) # 沒登入就去登入頁

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)