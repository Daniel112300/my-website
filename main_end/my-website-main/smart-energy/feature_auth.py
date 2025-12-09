from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db
# 管理登入登出
bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # 如果已經登入，直接導向首頁
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('登入成功！歡迎回來。', 'success')
            
            # 檢查是否有 next 參數 (登入後導向原本想去的頁面)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('ui_device'))
        else:
            flash('登入失敗。請檢查帳號密碼。', 'error')
            
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('auth.login'))