# feature_temp_auto.py
# ==========================================
# 功能3：溫度判斷並自動開關電器
# 支援手動判斷與自動監控模式
# ==========================================

from flask import Blueprint, request, jsonify
from models import db, Device, DeviceStatus
from datetime import datetime, timedelta
import threading
import time

bp = Blueprint("auto", __name__, template_folder="templates")

TARGET_TEMP = 26.0                               # 設定溫度閾值
AUTO_MONITOR_ENABLED = False                     # 自動監控開關
MONITOR_INTERVAL = 1800                          # 監控間隔（秒），預設 30 分鐘
MONITOR_THREAD = None                            # 監控執行緒
SIMULATED_TEMP = None                             # 可由前端設定的模擬目前溫度（以 °C 為單位）

# ==========================================
# 核心邏輯：從資料庫讀取溫度並判斷
# ==========================================

def get_latest_temperature():
    """
    從環境資料表或模擬器取得最新溫度
    如果沒有 environment_logs 表，使用模擬器 API
    
    Returns:
        float or None: 目前室內溫度
    """
    # 如果前端有設定模擬溫度，先使用模擬溫度
    try:
        global SIMULATED_TEMP
        if SIMULATED_TEMP is not None:
            return float(SIMULATED_TEMP)
    except Exception as e:
        print(f"Error reading SIMULATED_TEMP: {e}")

    try:
        # 方法 1: 從 environment_logs 表讀取（如果有建立）
        from models import EnvironmentLog
        latest = EnvironmentLog.query.order_by(
            EnvironmentLog.log_datetime.desc()
        ).first()
        
        if latest and latest.indoor_temp:
            return float(latest.indoor_temp)
    except Exception as e:
        print(f"EnvironmentLog not available: {e}")
    
    # 方法 2: 使用模擬器產生即時溫度
    try:
        from feature_simulator import simulate_outdoor_temperature, simulate_indoor_temperature
        outdoor = simulate_outdoor_temperature(datetime.now().date(), datetime.now().hour)
        indoor = simulate_indoor_temperature(outdoor, ac_running=False)
        return indoor
    except Exception as e:
        print(f"Error getting temperature: {e}")
        return None

def get_air_conditioner_devices():
    """
    取得所有冷氣設備
    
    Returns:
        list: Device 物件列表
    """
    return Device.query.filter_by(
        device_type='air_conditioner',
        is_active=True
    ).all()

def control_device(device, turn_on):
    """
    控制設備開關
    
    Args:
        device: Device 物件
        turn_on: True 為開啟，False 為關閉
    
    Returns:
        bool: 是否成功
    """
    try:
        # 取得或建立設備狀態
        status = device.status
        if not status:
            status = DeviceStatus(device_id=device.device_id, is_on=turn_on)
            db.session.add(status)
        else:
            status.is_on = turn_on
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error controlling device {device.device_id}: {e}")
        return False

def auto_temperature_check():
    """
    自動溫度檢查邏輯
    讀取資料庫溫度，判斷是否需要開關冷氣
    
    Returns:
        dict: 檢查結果
    """
    # 1. 讀取目前溫度
    current_temp = get_latest_temperature()
    
    if current_temp is None:
        return {
            "ok": False,
            "msg": "Unable to get temperature from database",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # 2. 判斷是否需要開關
    should_turn_on = current_temp > TARGET_TEMP
    action = "turn_on" if should_turn_on else "turn_off"
    
    # 3. 取得所有冷氣設備
    devices = get_air_conditioner_devices()
    
    # 4. 控制設備
    controlled = []
    for device in devices:
        success = control_device(device, should_turn_on)
        controlled.append({
            "device_id": device.device_id,
            "device_name": device.device_name,
            "action": action,
            "success": success
        })
    
    return {
        "ok": True,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_temp": current_temp,
        "target_temp": TARGET_TEMP,
        "action": action,
        "reason": f"Temperature {current_temp}°C {'>' if should_turn_on else '≤'} {TARGET_TEMP}°C",
        "devices_controlled": controlled
    }

# ==========================================
# 背景監控執行緒
# ==========================================

def monitor_loop():
    """背景執行緒：每隔指定時間檢查一次溫度"""
    global AUTO_MONITOR_ENABLED
    
    print(f"🌡️ Auto temperature monitor started (interval: {MONITOR_INTERVAL}s)")
    
    while AUTO_MONITOR_ENABLED:
        try:
            result = auto_temperature_check()
            print(f"[{result.get('timestamp')}] Temp: {result.get('current_temp')}°C, Action: {result.get('action')}")
        except Exception as e:
            print(f"Error in monitor loop: {e}")
        
        # 等待下一次檢查
        time.sleep(MONITOR_INTERVAL)
    
    print("🌡️ Auto temperature monitor stopped")

# ==========================================
# API 端點
# ==========================================

@bp.route("/decide", methods=["GET", "POST"])
def decide_by_temp():
    """
    手動溫度判斷 API（保留給前端使用）
    
    GET/POST ?temp=28 或 {"temp": 28}
    """
    # GET 請求從 query string 取得參數，POST 從 JSON body 取得
    if request.method == "GET":
        t = request.args.get("temp", type=float)
    else:
        data = request.get_json(silent=True) or {}
        t = data.get("temp")
    
    if not isinstance(t, (int, float)):
        return jsonify({"ok": False, "msg": "temp required"}), 400
    
    if t > TARGET_TEMP:
        action = "turn_on"
    else:
        action = "turn_off"
    
    return jsonify({
        "ok": True,
        "action": action,
        "current_temp": t,
        "target": TARGET_TEMP
    })

@bp.route("/check", methods=["GET"])
def check_temperature():
    """
    從資料庫讀取溫度並判斷（立即執行一次）
    
    GET /auto/check
    
    Response:
    {
        "ok": true,
        "timestamp": "2025-11-30 15:30:00",
        "current_temp": 28.5,
        "target_temp": 26.0,
        "action": "turn_on",
        "devices_controlled": [...]
    }
    """
    result = auto_temperature_check()
    return jsonify(result)

@bp.route("/monitor/start", methods=["POST"])
def start_monitor():
    """
    啟動自動監控
    
    POST /auto/monitor/start
    Body (optional):
    {
        "interval": 180  # 監控間隔（秒）
    }
    """
    global AUTO_MONITOR_ENABLED, MONITOR_INTERVAL, MONITOR_THREAD
    
    if AUTO_MONITOR_ENABLED:
        return jsonify({
            "ok": False,
            "msg": "Monitor is already running"
        }), 400
    
    # 取得自訂間隔（如果有）
    data = request.get_json(silent=True) or {}
    custom_interval = data.get("interval")
    if custom_interval:
        MONITOR_INTERVAL = int(custom_interval)
    
    # 啟動監控
    AUTO_MONITOR_ENABLED = True
    MONITOR_THREAD = threading.Thread(target=monitor_loop, daemon=True)
    MONITOR_THREAD.start()
    
    return jsonify({
        "ok": True,
        "msg": "Auto monitor started",
        "interval": MONITOR_INTERVAL,
        "target_temp": TARGET_TEMP
    })

@bp.route("/monitor/stop", methods=["POST"])
def stop_monitor():
    """
    停止自動監控
    
    POST /auto/monitor/stop
    """
    global AUTO_MONITOR_ENABLED
    
    if not AUTO_MONITOR_ENABLED:
        return jsonify({
            "ok": False,
            "msg": "Monitor is not running"
        }), 400
    
    AUTO_MONITOR_ENABLED = False
    
    return jsonify({
        "ok": True,
        "msg": "Auto monitor stopped"
    })

@bp.route("/monitor/status", methods=["GET"])
def monitor_status():
    """
    查看監控狀態
    
    GET /auto/monitor/status
    """
    return jsonify({
        "ok": True,
        "enabled": AUTO_MONITOR_ENABLED,
        "interval": MONITOR_INTERVAL,
        "target_temp": TARGET_TEMP
    })

@bp.route("/config", methods=["GET", "POST"])
def config():
    """
    查看或修改設定
    
    GET /auto/config - 查看目前設定
    POST /auto/config - 修改設定
    Body: {"target_temp": 25.0, "interval": 300}
    """
    global TARGET_TEMP, MONITOR_INTERVAL
    
    if request.method == "GET":
        return jsonify({
            "ok": True,
            "target_temp": TARGET_TEMP,
            "monitor_interval": MONITOR_INTERVAL,
            "monitor_enabled": AUTO_MONITOR_ENABLED,
            "simulated_temp": SIMULATED_TEMP
        })
    
    # POST: 修改設定
    data = request.get_json(silent=True) or {}
    
    if "target_temp" in data:
        TARGET_TEMP = float(data["target_temp"])
    
    if "interval" in data:
        MONITOR_INTERVAL = int(data["interval"])
    
    # 接受模擬溫度設定（以 Celsius）
    if "simulated_temp" in data:
        try:
            SIMULATED_TEMP = float(data["simulated_temp"]) if data["simulated_temp"] is not None else None
        except Exception:
            SIMULATED_TEMP = None
    
    return jsonify({
        "ok": True,
        "msg": "Config updated",
        "target_temp": TARGET_TEMP,
        "monitor_interval": MONITOR_INTERVAL
    })
