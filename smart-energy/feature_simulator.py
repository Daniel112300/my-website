# feature_simulator.py
# ==========================================
# 智慧家庭資料模擬器
# 模擬電量、溫度、設備使用行為
# ==========================================

from flask import Blueprint, jsonify, request
from models import db, Device, PowerLog
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func
import random
import math

bp = Blueprint("simulator", __name__)

# ==========================================
# 設備行為設定檔
# ==========================================
DEVICE_PROFILES = {
    "air_conditioner": {
        "base_usage_hours": (4, 10),  # 每日基礎使用時數範圍
        "peak_hours": [13, 14, 15, 19, 20, 21, 22],  # 尖峰使用時段
        "active_probability": 0.7,  # 該日有使用的機率
        "power_factor": (0.6, 0.95),  # 實際功率因數範圍（rated_power的倍數）
        "temperature_dependent": True,  # 是否受溫度影響
        "seasonal_factor": {  # 季節因子
            "spring": 0.3,  # 春季（3-5月）使用率較低
            "summer": 1.2,  # 夏季（6-9月）使用率高
            "autumn": 0.4,  # 秋季（10-11月）
            "winter": 0.8   # 冬季（12-2月）
        }
    },
    "light": {
        "base_usage_hours": (3, 8),
        "peak_hours": [6, 7, 18, 19, 20, 21, 22, 23],
        "active_probability": 0.95,  # 燈具幾乎每天使用
        "power_factor": (0.9, 1.0),  # 燈具功率較穩定
        "temperature_dependent": False,
        "seasonal_factor": {
            "spring": 1.0,
            "summer": 0.8,  # 夏季日照長，用燈較少
            "autumn": 1.0,
            "winter": 1.3   # 冬季日照短，用燈較多
        }
    }
}

# ==========================================
# 溫度模擬參數
# ==========================================
TEMPERATURE_CONFIG = {
    "base_temp": {  # 基礎溫度（月平均）
        1: 16, 2: 17, 3: 20, 4: 24, 5: 27, 6: 29,
        7: 31, 8: 31, 9: 29, 10: 26, 11: 22, 12: 18
    },
    "daily_amplitude": 6,  # 日夜溫差振幅
    "random_noise": 2,  # 隨機雜訊範圍
    "indoor_lag": 0.7,  # 室內溫度延遲因子（0-1）
    "cooling_effect": 3  # 冷氣降溫效果（度）
}

# ==========================================
# 核心模擬函式
# ==========================================

def get_season(month):
    """根據月份取得季節"""
    if month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8, 9]:
        return "summer"
    elif month in [10, 11]:
        return "autumn"
    else:
        return "winter"

def simulate_outdoor_temperature(target_date, hour=12):
    """
    模擬室外溫度
    
    Args:
        target_date: 目標日期
        hour: 時刻（0-23）
    
    Returns:
        模擬的室外溫度（攝氏）
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    # 取得該月份的基礎溫度
    base_temp = TEMPERATURE_CONFIG["base_temp"][target_date.month]
    
    # 日內溫度波動（正弦曲線：14:00 最熱，凌晨 4:00 最冷）
    daily_variation = TEMPERATURE_CONFIG["daily_amplitude"] * math.sin(
        (hour - 4) * math.pi / 12
    )
    
    # 加入隨機雜訊
    noise = random.uniform(
        -TEMPERATURE_CONFIG["random_noise"],
        TEMPERATURE_CONFIG["random_noise"]
    )
    
    temp = base_temp + daily_variation + noise
    return round(temp, 1)

def simulate_indoor_temperature(outdoor_temp, ac_running=False):
    """
    模擬室內溫度
    
    Args:
        outdoor_temp: 室外溫度
        ac_running: 冷氣是否運轉
    
    Returns:
        室內溫度
    """
    # 室內溫度會比室外溫度有延遲效應
    indoor = outdoor_temp * TEMPERATURE_CONFIG["indoor_lag"] + \
             (26 * (1 - TEMPERATURE_CONFIG["indoor_lag"]))
    
    # 如果冷氣開啟，降溫效果
    if ac_running:
        indoor -= TEMPERATURE_CONFIG["cooling_effect"]
    
    return round(indoor, 1)

def simulate_device_usage(device, target_date, outdoor_temp=None):
    """
    模擬單一設備在指定日期的用電量
    
    Args:
        device: Device 模型實例
        target_date: 目標日期
        outdoor_temp: 室外溫度（可選）
    
    Returns:
        dict: {
            "device_id": int,
            "device_name": str,
            "power_watts": float,
            "hours": float,
            "kwh": float,
            "simulated": True
        }
        如果該設備當日不使用，返回 None
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    # 取得設備類型的行為設定檔
    profile = DEVICE_PROFILES.get(device.device_type)
    if not profile:
        return None
    
    # 判斷該日是否使用（依機率）
    if random.random() > profile["active_probability"]:
        return None
    
    # 計算季節因子
    season = get_season(target_date.month)
    seasonal_mult = profile["seasonal_factor"][season]
    
    # 基礎使用時數
    base_hours = random.uniform(*profile["base_usage_hours"]) * seasonal_mult
    
    # 如果設備受溫度影響
    if profile["temperature_dependent"] and outdoor_temp:
        if device.device_type == "air_conditioner":
            # 溫度越高，冷氣使用時間越長
            if outdoor_temp > 28:
                base_hours *= 1.5
            elif outdoor_temp > 25:
                base_hours *= 1.2
            elif outdoor_temp < 20:
                base_hours *= 0.5
    
    # 限制最大使用時數為 24 小時
    hours = min(base_hours, 24.0)
    
    # 計算功率（加入功率因數變化）
    power_factor = random.uniform(*profile["power_factor"])
    rated_power_kw = float(device.rated_power) if device.rated_power else 1.0
    actual_power_kw = rated_power_kw * power_factor
    power_watts = actual_power_kw * 1000
    
    # 計算耗電量
    kwh = actual_power_kw * hours
    
    return {
        "device_id": device.device_id,
        "device_name": device.device_name,
        "power_watts": round(power_watts, 2),
        "hours": round(hours, 2),
        "kwh": round(kwh, 4),
        "simulated": True
    }

def save_simulated_data(device_id, target_date, power_watts, hours, kwh):
    """
    將模擬資料存入資料庫
    
    Args:
        device_id: 設備 ID
        target_date: 日期
        power_watts: 功率（瓦）
        hours: 使用時數
        kwh: 耗電量（度）
    
    Returns:
        bool: 是否成功儲存
    """
    try:
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        
        # 檢查是否已存在該日記錄
        existing = PowerLog.query.filter_by(
            device_id=device_id,
            log_date=target_date
        ).first()
        
        if existing:
            # 更新現有記錄
            existing.power_watts = Decimal(str(power_watts))
            existing.hours = Decimal(str(hours))
            existing.energy_consumed = Decimal(str(kwh))
            # 成本會在 API 層級計算
        else:
            # 建立新記錄
            new_log = PowerLog(
                device_id=device_id,
                power_watts=Decimal(str(power_watts)),
                hours=Decimal(str(hours)),
                log_date=target_date,
                energy_consumed=Decimal(str(kwh))
            )
            db.session.add(new_log)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error saving simulated data: {e}")
        return False

# ==========================================
# API 端點
# ==========================================

@bp.route("/daily", methods=["POST"])
def simulate_daily():
    """
    模擬單日所有設備的用電量
    
    Request Body:
    {
        "date": "2025-12-01",  # 必填
        "save_to_db": true,    # 是否存入資料庫，預設 false
        "seed": 12345          # 隨機種子，用於可重現性（可選）
    }
    
    Response:
    {
        "ok": true,
        "date": "2025-12-01",
        "outdoor_temp": 25.3,
        "devices": [
            {
                "device_id": 1,
                "device_name": "客廳冷氣",
                "power_watts": 3200.5,
                "hours": 6.5,
                "kwh": 20.8,
                "simulated": true
            },
            ...
        ],
        "total_kwh": 45.6,
        "saved": true/false
    }
    """
    data = request.get_json(silent=True) or {}
    
    # 驗證必填參數
    target_date_str = data.get("date")
    if not target_date_str:
        return jsonify({"ok": False, "msg": "date is required (format: YYYY-MM-DD)"}), 400
    
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "msg": "Invalid date format, use YYYY-MM-DD"}), 400
    
    # 設定隨機種子（如果提供）
    seed = data.get("seed")
    if seed is not None:
        random.seed(seed)
    
    # 是否存入資料庫
    save_to_db = data.get("save_to_db", False)
    
    # 模擬室外溫度（使用中午 12 點作為代表）
    outdoor_temp = simulate_outdoor_temperature(target_date, hour=12)
    
    # 取得所有啟用的設備
    devices = Device.query.filter_by(is_active=True).all()
    
    results = []
    total_kwh = 0
    saved_count = 0
    
    for device in devices:
        usage = simulate_device_usage(device, target_date, outdoor_temp)
        
        if usage:  # 如果該設備當日有使用
            results.append(usage)
            total_kwh += usage["kwh"]
            
            # 存入資料庫
            if save_to_db:
                success = save_simulated_data(
                    usage["device_id"],
                    target_date,
                    usage["power_watts"],
                    usage["hours"],
                    usage["kwh"]
                )
                if success:
                    saved_count += 1
    
    return jsonify({
        "ok": True,
        "date": target_date_str,
        "outdoor_temp": outdoor_temp,
        "devices": results,
        "total_kwh": round(total_kwh, 4),
        "device_count": len(results),
        "saved": save_to_db,
        "saved_count": saved_count if save_to_db else 0
    })

@bp.route("/range", methods=["POST"])
def simulate_range():
    """
    模擬一段時間的用電量
    
    Request Body:
    {
        "start_date": "2025-12-01",  # 必填
        "end_date": "2025-12-07",    # 必填
        "save_to_db": true,          # 是否存入資料庫
        "seed": 12345                # 隨機種子（可選）
    }
    
    Response:
    {
        "ok": true,
        "start_date": "2025-12-01",
        "end_date": "2025-12-07",
        "days_simulated": 7,
        "total_records": 35,
        "total_kwh": 320.5,
        "saved": true
    }
    """
    data = request.get_json(silent=True) or {}
    
    # 驗證參數
    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date")
    
    if not start_date_str or not end_date_str:
        return jsonify({"ok": False, "msg": "start_date and end_date are required"}), 400
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "msg": "Invalid date format, use YYYY-MM-DD"}), 400
    
    if start_date > end_date:
        return jsonify({"ok": False, "msg": "start_date must be before end_date"}), 400
    
    # 設定隨機種子
    seed = data.get("seed")
    if seed is not None:
        random.seed(seed)
    
    save_to_db = data.get("save_to_db", False)
    
    # 逐日模擬
    current_date = start_date
    total_records = 0
    total_kwh = 0
    days_count = 0
    
    while current_date <= end_date:
        # 模擬當日溫度
        outdoor_temp = simulate_outdoor_temperature(current_date)
        
        # 取得所有啟用設備
        devices = Device.query.filter_by(is_active=True).all()
        
        for device in devices:
            usage = simulate_device_usage(device, current_date, outdoor_temp)
            
            if usage:
                total_records += 1
                total_kwh += usage["kwh"]
                
                if save_to_db:
                    save_simulated_data(
                        usage["device_id"],
                        current_date,
                        usage["power_watts"],
                        usage["hours"],
                        usage["kwh"]
                    )
        
        days_count += 1
        current_date += timedelta(days=1)
    
    return jsonify({
        "ok": True,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "days_simulated": days_count,
        "total_records": total_records,
        "total_kwh": round(total_kwh, 4),
        "saved": save_to_db
    })

@bp.route("/temperature", methods=["GET"])
def simulate_temperature():
    """
    模擬指定日期和時刻的溫度
    
    Query Parameters:
        date: 日期 (YYYY-MM-DD)，預設今天
        hour: 時刻 (0-23)，預設 12
        ac_running: 冷氣是否運轉 (true/false)，預設 false
    
    Response:
    {
        "ok": true,
        "date": "2025-12-01",
        "hour": 14,
        "outdoor_temp": 26.5,
        "indoor_temp": 23.2,
        "ac_running": false
    }
    """
    target_date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    hour = request.args.get("hour", 12, type=int)
    ac_running = request.args.get("ac_running", "false").lower() == "true"
    
    if not (0 <= hour <= 23):
        return jsonify({"ok": False, "msg": "hour must be between 0 and 23"}), 400
    
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "msg": "Invalid date format"}), 400
    
    outdoor_temp = simulate_outdoor_temperature(target_date, hour)
    indoor_temp = simulate_indoor_temperature(outdoor_temp, ac_running)
    
    return jsonify({
        "ok": True,
        "date": target_date_str,
        "hour": hour,
        "outdoor_temp": outdoor_temp,
        "indoor_temp": indoor_temp,
        "ac_running": ac_running
    })

@bp.route("/config", methods=["GET"])
def get_config():
    """
    取得目前的模擬器設定
    
    Response:
    {
        "ok": true,
        "device_profiles": {...},
        "temperature_config": {...}
    }
    """
    return jsonify({
        "ok": True,
        "device_profiles": DEVICE_PROFILES,
        "temperature_config": TEMPERATURE_CONFIG
    })

@bp.route("/stats", methods=["GET"])
def get_stats():
    """
    取得資料庫中模擬資料的統計
    
    Response:
    {
        "ok": true,
        "total_records": 991,
        "date_range": {
            "start": "2025-01-01",
            "end": "2025-11-30"
        },
        "devices": [...]
    }
    """
    try:
        # 總記錄數
        total_records = PowerLog.query.count()
        
        # 日期範圍
        min_date = db.session.query(func.min(PowerLog.log_date)).scalar()
        max_date = db.session.query(func.max(PowerLog.log_date)).scalar()
        
        # 各設備記錄數
        device_stats = db.session.query(
            Device.device_name,
            func.count(PowerLog.log_id).label("record_count"),
            func.sum(PowerLog.energy_consumed).label("total_kwh")
        ).join(PowerLog).group_by(Device.device_id, Device.device_name).all()
        
        devices = [
            {
                "device_name": d[0],
                "record_count": d[1],
                "total_kwh": float(d[2]) if d[2] else 0
            }
            for d in device_stats
        ]
        
        return jsonify({
            "ok": True,
            "total_records": total_records,
            "date_range": {
                "start": min_date.strftime("%Y-%m-%d") if min_date else None,
                "end": max_date.strftime("%Y-%m-%d") if max_date else None
            },
            "devices": devices
        })
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
