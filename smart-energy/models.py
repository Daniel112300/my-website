# models.py
# ==========================================
# 資料庫模型定義檔案
# 定義所有資料表的 SQLAlchemy 模型
# ==========================================

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# 建立資料庫物件
db = SQLAlchemy()

# ==========================================
# Device 模型 (設備資料表)
# ==========================================
class Device(db.Model):
    __tablename__ = 'devices'
    
    device_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    model_number = db.Column(db.String(50))
    location = db.Column(db.String(100))
    rated_power = db.Column(db.DECIMAL(6, 2))  # 額定功率(kW)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    
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
# PowerLog 模型 (電力使用記錄表)
# ==========================================
class PowerLog(db.Model):
    __tablename__ = 'power_logs'
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Integer, nullable=False)
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
