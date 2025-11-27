# models.py
# ==========================================
# 負責定義資料庫模型 (資料表結構)
# ==========================================
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ------------------------------------------
# 類別名稱：User
# 用途：儲存使用者帳號、密碼與角色資料
# 修改：為了配合 smart_home_db.sql，主鍵改為 user_id，並新增 email/role
# ------------------------------------------
class User(db.Model):
    __tablename__ = 'users'  # 指定對應資料庫中的表名
    
    # [差異說明] 這裡改用 user_id 以對應 SQL 檔，若你舊程式是用 .id，需對應修改
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # [新增] 來自 SQL 檔的新欄位
    email = db.Column(db.String(100), unique=True)
    role = db.Column(db.Enum('admin', 'user'), default='user')

    # [新增] 關聯：一個使用者有多個裝置
    devices = db.relationship('Device', backref='owner', lazy=True)

    def set_password(self, password: str):
        """設定密碼 (保留原本的 scrypt 加密設定)"""
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        """檢查密碼"""
        return check_password_hash(self.password_hash, password)

# ------------------------------------------
# 類別名稱：Report
# 用途：儲存報表資料 (保留原本功能)
# ------------------------------------------
class Report(db.Model):
    # 如果希望對應特定的表名，也可以加 __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(80), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(120), nullable=False, index=True)

# ==========================================
# 以下為新增的智慧家電功能模型
# ==========================================

# ------------------------------------------
# 類別名稱：Device (設備)
# ------------------------------------------
class Device(db.Model):
    __tablename__ = 'devices'
    device_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.Enum('air_conditioner', 'light'), nullable=False)
    model_number = db.Column(db.String(50))
    location = db.Column(db.String(100))
    rated_power = db.Column(db.Numeric(6, 2))
    is_active = db.Column(db.Boolean, default=True)

    # 關聯
    status = db.relationship('DeviceStatus', backref='device', uselist=False, lazy=True)
    logs = db.relationship('PowerLog', backref='device', lazy=True)

# ------------------------------------------
# 類別名稱：DeviceStatus (設備狀態)
# ------------------------------------------
class DeviceStatus(db.Model):
    __tablename__ = 'device_status'
    status_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.device_id'), unique=True, nullable=False)
    is_on = db.Column(db.Boolean, default=False)
    current_temperature = db.Column(db.Numeric(4, 2))
    target_temperature = db.Column(db.Numeric(4, 2))
    mode = db.Column(db.Enum('cool', 'heat', 'dry', 'auto'))

# ------------------------------------------
# 類別名稱：PowerLog (電力紀錄)
# ------------------------------------------
class PowerLog(db.Model):
    __tablename__ = 'power_logs'
    log_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.device_id'), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    energy_consumed = db.Column(db.Numeric(8, 4))
    cost = db.Column(db.Numeric(8, 2))
    electricity_rate = db.Column(db.Numeric(6, 4), default=3.20)