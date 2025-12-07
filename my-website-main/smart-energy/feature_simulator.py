# feature_simulator.py
# ==========================================
# 智慧家庭資料模擬器 (修正版：加入計費邏輯)
# 模擬電量、溫度，並自動計算台電累進電費
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
# 台電費率設定 (與 feature_daily_usage.py 同步)
# ==========================================
TAIPOWER_RATES = {
    "summer": [ # 夏月 (6-9月)
        (120, 1.63), (330, 2.38), (500, 3.52), (700, 4.80), (1000, 5.83), (float('inf'), 7.69)
    ],
    "non_summer": [ # 非夏月
        (120, 1.63), (330, 2.10), (500, 2.89), (700, 3.94), (1000, 4.74), (float('inf'), 6.03)
    ]
}

def calculate_bill(kwh, usage_date):
    """計算電費 (累進費率)"""
    if isinstance(usage_date, str):
        usage_date = datetime.strptime(usage_date, "%Y-%m-%d").date()
        
    is_summer = 6 <= usage_date.month <= 9
    rates = TAIPOWER_RATES["summer"] if is_summer else TAIPOWER_RATES["non_summer"]
    
    total_bill = 0
    remaining_kwh = kwh
    prev_tier = 0
    
    for tier_limit, rate in rates:
        if remaining_kwh <= 0: break
        tier_kwh = min(remaining_kwh, tier_limit - prev_tier)
        total_bill += tier_kwh * rate
        remaining_kwh -= tier_kwh
        prev_tier = tier_limit
        
    return total_bill

# ==========================================
# 設備行為設定檔
# ==========================================
DEVICE_PROFILES = {
    "air_conditioner": {
        "base_usage_hours": (4, 10),
        "peak_hours": [13, 14, 15, 19, 20, 21, 22],
        "active_probability": 0.7,
        "power_factor": (0.6, 0.95),
        "temperature_dependent": True,
        "seasonal_factor": {"spring": 0.3, "summer": 1.2, "autumn": 0.4, "winter": 0.8}
    },
    "light": {
        "base_usage_hours": (3, 8),
        "peak_hours": [6, 7, 18, 19, 20, 21, 22, 23],
        "active_probability": 0.95,
        "power_factor": (0.9, 1.0),
        "temperature_dependent": False,
        "seasonal_factor": {"spring": 1.0, "summer": 0.8, "autumn": 1.0, "winter": 1.3}
    }
}

# ==========================================
# 溫度模擬參數
# ==========================================
TEMPERATURE_CONFIG = {
    "base_temp": {
        1: 16, 2: 17, 3: 20, 4: 24, 5: 27, 6: 29,
        7: 31, 8: 31, 9: 29, 10: 26, 11: 22, 12: 18
    },
    "daily_amplitude": 6,
    "random_noise": 2,
    "indoor_lag": 0.7,
    "cooling_effect": 3
}

# ==========================================
# 核心模擬函式
# ==========================================

def get_season(month):
    if month in [3, 4, 5]: return "spring"
    elif month in [6, 7, 8, 9]: return "summer"
    elif month in [10, 11]: return "autumn"
    else: return "winter"

def simulate_outdoor_temperature(target_date, hour=12):
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    base_temp = TEMPERATURE_CONFIG["base_temp"][target_date.month]
    daily_variation = TEMPERATURE_CONFIG["daily_amplitude"] * math.sin((hour - 4) * math.pi / 12)
    noise = random.uniform(-TEMPERATURE_CONFIG["random_noise"], TEMPERATURE_CONFIG["random_noise"])
    return round(base_temp + daily_variation + noise, 1)

def simulate_indoor_temperature(outdoor_temp, ac_running=False):
    indoor = outdoor_temp * TEMPERATURE_CONFIG["indoor_lag"] + (26 * (1 - TEMPERATURE_CONFIG["indoor_lag"]))
    if ac_running: indoor -= TEMPERATURE_CONFIG["cooling_effect"]
    return round(indoor, 1)

def simulate_device_usage(device, target_date, outdoor_temp=None):
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    profile = DEVICE_PROFILES.get(device.device_type)
    if not profile: return None
    
    if random.random() > profile["active_probability"]: return None
    
    season = get_season(target_date.month)
    seasonal_mult = profile["seasonal_factor"][season]
    base_hours = random.uniform(*profile["base_usage_hours"]) * seasonal_mult
    
    if profile["temperature_dependent"] and outdoor_temp:
        if device.device_type == "air_conditioner":
            if outdoor_temp > 28: base_hours *= 1.5
            elif outdoor_temp > 25: base_hours *= 1.2
            elif outdoor_temp < 20: base_hours *= 0.5
    
    hours = min(base_hours, 24.0)
    power_factor = random.uniform(*profile["power_factor"])
    rated_power_kw = float(device.rated_power) if device.rated_power else 1.0
    actual_power_kw = rated_power_kw * power_factor
    power_watts = actual_power_kw * 1000
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
    """將模擬資料存入資料庫 (含電費計算)"""
    try:
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            
        # 1. 計算該設備本月截至目前的累積用電 (不含今日)
        month_start = target_date.replace(day=1)
        accumulated_kwh = db.session.query(func.sum(PowerLog.energy_consumed))\
            .filter(PowerLog.device_id == device_id)\
            .filter(PowerLog.log_date >= month_start)\
            .filter(PowerLog.log_date < target_date)\
            .scalar() or 0
        accumulated_kwh = float(accumulated_kwh)
        
        # 2. 計算電費 (邊際成本)
        bill_before = calculate_bill(accumulated_kwh, target_date)
        bill_after = calculate_bill(accumulated_kwh + kwh, target_date)
        cost = round(bill_after - bill_before, 2)
        rate = round(cost / kwh, 2) if kwh > 0 else 0
        
        # 3. 檢查或新增
        existing = PowerLog.query.filter_by(device_id=device_id, log_date=target_date).first()
        
        if existing:
            existing.power_watts = Decimal(str(power_watts))
            existing.hours = Decimal(str(hours))
            existing.energy_consumed = Decimal(str(kwh))
            existing.cost = Decimal(str(cost))
            existing.electricity_rate = Decimal(str(rate))
        else:
            new_log = PowerLog(
                device_id=device_id,
                power_watts=Decimal(str(power_watts)),
                hours=Decimal(str(hours)),
                log_date=target_date,
                energy_consumed=Decimal(str(kwh)),
                cost=Decimal(str(cost)),
                electricity_rate=Decimal(str(rate))
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
    data = request.get_json(silent=True) or {}
    target_date_str = data.get("date")
    if not target_date_str: return jsonify({"ok": False, "msg": "date required"}), 400
    
    try: target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError: return jsonify({"ok": False, "msg": "Invalid date format"}), 400
    
    save_to_db = data.get("save_to_db", False)
    if data.get("seed"): random.seed(data.get("seed"))
    
    outdoor_temp = simulate_outdoor_temperature(target_date)
    devices = Device.query.filter_by(is_active=True).all()
    
    results = []
    total_kwh = 0
    saved_count = 0
    
    for device in devices:
        usage = simulate_device_usage(device, target_date, outdoor_temp)
        if usage:
            if save_to_db:
                save_simulated_data(
                    usage["device_id"], target_date, 
                    usage["power_watts"], usage["hours"], usage["kwh"]
                )
                saved_count += 1
            
            # 因為現在只有在 save_to_db 時才真的算 cost，如果不存檔就只給預估值
            # 這裡簡單回傳，讓前端測試用
            results.append(usage)
            total_kwh += usage["kwh"]
            
    return jsonify({
        "ok": True,
        "date": target_date_str,
        "outdoor_temp": outdoor_temp,
        "devices": results,
        "total_kwh": round(total_kwh, 4),
        "saved_count": saved_count
    })

@bp.route("/range", methods=["POST"])
def simulate_range():
    data = request.get_json(silent=True) or {}
    start_str = data.get("start_date")
    end_str = data.get("end_date")
    if not start_str or not end_str: return jsonify({"ok": False}), 400
    
    try:
        current_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    except ValueError: return jsonify({"ok": False}), 400
    
    if data.get("seed"): random.seed(data.get("seed"))
    save_to_db = data.get("save_to_db", False)
    
    total_records = 0
    
    while current_date <= end_date:
        outdoor_temp = simulate_outdoor_temperature(current_date)
        devices = Device.query.filter_by(is_active=True).all()
        for device in devices:
            usage = simulate_device_usage(device, current_date, outdoor_temp)
            if usage and save_to_db:
                save_simulated_data(
                    usage["device_id"], current_date, 
                    usage["power_watts"], usage["hours"], usage["kwh"]
                )
                total_records += 1
        current_date += timedelta(days=1)
        
    return jsonify({"ok": True, "total_records": total_records})

@bp.route("/temperature", methods=["GET"])
def simulate_temperature():
    target_date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    hour = request.args.get("hour", 12, type=int)
    ac_running = request.args.get("ac_running", "false").lower() == "true"
    
    try: target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError: return jsonify({"ok": False}), 400
    
    outdoor = simulate_outdoor_temperature(target_date, hour)
    indoor = simulate_indoor_temperature(outdoor, ac_running)
    return jsonify({"ok": True, "outdoor_temp": outdoor, "indoor_temp": indoor})

@bp.route("/config", methods=["GET"])
def get_config():
    return jsonify({"ok": True, "device_profiles": DEVICE_PROFILES, "temperature_config": TEMPERATURE_CONFIG})

@bp.route("/stats", methods=["GET"])
def get_stats():
    count = PowerLog.query.count()
    return jsonify({"ok": True, "total_records": count})