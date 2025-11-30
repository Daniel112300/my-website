# models.py
# ==========================================
# 資料庫模型定義檔案
# 定義所有資料表的 SQLAlchemy 模型
# ==========================================

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# 建立資料庫物件
db = SQLAlchemy()

# ==========================================
# User 模型 (使用者資料表)
# ==========================================
class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True)
    role = db.Column(db.Enum('admin', 'user'), default='user')
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    # 關聯：一個使用者有多個裝置
    devices = db.relationship('Device', backref='owner', lazy=True)
    
    def set_password(self, password: str):
        """設定密碼 (使用 scrypt 加密)"""
        self.password_hash = generate_password_hash(password, method="scrypt")
    
    def check_password(self, password: str):
        """檢查密碼"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.user_id}: {self.username}>'

# ==========================================
# Device 模型 (設備資料表)
# ==========================================
class Device(db.Model):
    __tablename__ = 'devices'
    
    device_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.Enum('air_conditioner', 'light'), nullable=False)
    model_number = db.Column(db.String(50))
    location = db.Column(db.String(100))
    rated_power = db.Column(db.DECIMAL(6, 2))  # 額定功率(kW)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    
    # 關聯
    status = db.relationship('DeviceStatus', backref='device', uselist=False, lazy=True)
    logs = db.relationship('PowerLog', backref='device', lazy=True)
    
    def to_dict(self):
        """將模型轉換為字典格式"""
        return {
            'device_id': self.device_id,
            'user_id': self.user_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'model_number': self.model_number,
            'location': self.location,
            'rated_power': float(self.rated_power) if self.rated_power else None,
            'rated_power_watts': float(self.rated_power) * 1000 if self.rated_power else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<Device {self.device_id}: {self.device_name}>'

# ==========================================
# DeviceStatus 模型 (設備狀態表)
# ==========================================
class DeviceStatus(db.Model):
    __tablename__ = 'device_status'
    
    status_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.device_id'), unique=True, nullable=False)
    is_on = db.Column(db.Boolean, default=False)
    current_temperature = db.Column(db.DECIMAL(4, 2))
    target_temperature = db.Column(db.DECIMAL(4, 2))
    mode = db.Column(db.Enum('cool', 'heat', 'dry', 'auto'))
    
    def to_dict(self):
        """將模型轉換為字典格式"""
        return {
            'status_id': self.status_id,
            'device_id': self.device_id,
            'is_on': self.is_on,
            'current_temperature': float(self.current_temperature) if self.current_temperature else None,
            'target_temperature': float(self.target_temperature) if self.target_temperature else None,
            'mode': self.mode
        }
    
    def __repr__(self):
        return f'<DeviceStatus {self.status_id}: Device {self.device_id}>'

# ==========================================
# PowerLog 模型 (電力使用記錄表)
# ==========================================
class PowerLog(db.Model):
    __tablename__ = 'power_logs'
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.device_id'), nullable=False)
    power_watts = db.Column(db.DECIMAL(8, 2))  # 功率(瓦)
    hours = db.Column(db.DECIMAL(6, 2))  # 使用時數
    log_date = db.Column(db.Date, nullable=False)
    energy_consumed = db.Column(db.DECIMAL(8, 4))
    cost = db.Column(db.DECIMAL(8, 2))
    electricity_rate = db.Column(db.DECIMAL(6, 4), default=3.20)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    # 建立複合唯一索引
    __table_args__ = (
        db.UniqueConstraint('device_id', 'log_date', name='uk_device_date'),
        db.Index('idx_log_date', 'log_date'),
        db.Index('idx_device_date', 'device_id', 'log_date'),
        {'mysql_engine': 'InnoDB', 
         'mysql_charset': 'utf8mb4', 
         'mysql_collate': 'utf8mb4_unicode_ci',
         'comment': '電力使用記錄表'}
    )
    
    def to_dict(self):
        """將模型轉換為字典格式"""
        return {
            'log_id': self.log_id,
            'device_id': self.device_id,
            'power_watts': float(self.power_watts) if self.power_watts else None,
            'hours': float(self.hours) if self.hours else None,
            'log_date': self.log_date.strftime('%Y-%m-%d') if self.log_date else None,
            'energy_consumed': float(self.energy_consumed) if self.energy_consumed else 0,
            'cost': float(self.cost) if self.cost else 0,
            'electricity_rate': float(self.electricity_rate) if self.electricity_rate else 0,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
    
    def __repr__(self):
        return f'<PowerLog {self.log_id}: Device {self.device_id} on {self.log_date}>'

# ==========================================
# EnvironmentLog 模型 (環境資料記錄表)
# ==========================================
class EnvironmentLog(db.Model):
    __tablename__ = 'environment_logs'
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    log_datetime = db.Column(db.TIMESTAMP, nullable=False, index=True)
    outdoor_temp = db.Column(db.DECIMAL(4, 2))  # 室外溫度（攝氏）
    indoor_temp = db.Column(db.DECIMAL(4, 2))   # 室內溫度（攝氏）
    humidity = db.Column(db.DECIMAL(5, 2))      # 濕度（%）
    source_type = db.Column(db.Enum('real', 'simulated'), default='simulated')
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    # 建立索引
    __table_args__ = (
        db.Index('idx_log_datetime', 'log_datetime'),
        {'mysql_engine': 'InnoDB', 
         'mysql_charset': 'utf8mb4', 
         'mysql_collate': 'utf8mb4_unicode_ci',
         'comment': '環境資料記錄表'}
    )
    
    def to_dict(self):
        """將模型轉換為字典格式"""
        return {
            'log_id': self.log_id,
            'log_datetime': self.log_datetime.strftime('%Y-%m-%d %H:%M:%S') if self.log_datetime else None,
            'outdoor_temp': float(self.outdoor_temp) if self.outdoor_temp else None,
            'indoor_temp': float(self.indoor_temp) if self.indoor_temp else None,
            'humidity': float(self.humidity) if self.humidity else None,
            'source_type': self.source_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
    
    def __repr__(self):
        return f'<EnvironmentLog {self.log_id}: {self.log_datetime}>'
