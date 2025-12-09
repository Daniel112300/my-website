# app.py
from flask import Flask, render_template, redirect, url_for
from config import Config
from models import db, User
from index import register_all_features
from flask_login import LoginManager, current_user, login_required

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 必須設定 SECRET_KEY
    app.config['SECRET_KEY'] = 'dev-secret-key-change-this-in-prod'

    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "請先登入以存取此頁面。"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    register_all_features(app)
    
    from feature_auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # UI 路由
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

    # --- 修改重點：首頁路由修正 ---
    @app.route("/")
    def index():
        # 如果沒登入，去登入頁
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
            
        # 如果已登入，顯示 index.html (而不是跳轉到 device)
        return render_template("index.html")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)