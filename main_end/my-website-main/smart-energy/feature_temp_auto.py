# feature_temp_auto.py
# ==========================================
# 功能3：溫度判斷並自動開關電器 (重構版)
# 改用 Dictionary 管理全域狀態，避免 UnboundLocalError
# ==========================================

from flask import Blueprint, request, jsonify
from models import db, Device, DeviceStatus
from datetime import datetime
import threading
import time

bp = Blueprint("auto", __name__, template_folder="templates")

# ==========================================
# 系統全域狀態 (State Dictionary)
# 使用字典管理，避免 Python 函式內部的 global 變數賦值問題
# ==========================================
AUTO_STATE = {
    "target_temp": 26.0,        # 目標溫度
    "monitor_enabled": False,   # 監控是否開啟
    "monitor_interval": 1800,   # 監控間隔(秒)
    "simulated_temp": None      # 前端強制設定的模擬溫度 (None 代表不使用)
}

MONITOR_THREAD = None  # 執行緒物件仍需獨立存放

# ==========================================
# 核心邏輯
# ==========================================

def get_latest_temperature():
    """取得目前溫度 (優先順序: 手動模擬 > 資料庫 > 自動計算)"""
    
    # 1. 優先檢查是否有人為設定的模擬溫度
    if AUTO_STATE["simulated_temp"] is not None:
        return float(AUTO_STATE["simulated_temp"])

    # 2. 嘗試從 EnvironmentLog 讀取 (如果有這個表)
    try:
        from models import EnvironmentLog
        latest = EnvironmentLog.query.order_by(
            EnvironmentLog.log_datetime.desc()
        ).first()
        if latest and latest.indoor_temp:
            return float(latest.indoor_temp)
    except Exception:
        # 資料表可能不存在或沒資料，忽略錯誤
        pass
    
    # 3. 最後手段：使用模擬器算出當下溫度
    try:
        from feature_simulator import simulate_outdoor_temperature, simulate_indoor_temperature
        outdoor = simulate_outdoor_temperature(datetime.now().date(), datetime.now().hour)
        indoor = simulate_indoor_temperature(outdoor, ac_running=False)
        return indoor
    except Exception as e:
        print(f"Error generating temp: {e}")
        return 28.0 # 萬一都失敗的預設值

def control_air_conditioners(should_turn_on):
    """控制所有冷氣開關"""
    devices = Device.query.filter_by(device_type='air_conditioner', is_active=True).all()
    results = []
    
    target_action = "turn_on" if should_turn_on else "turn_off"
    
    for device in devices:
        try:
            # 取得或建立狀態記錄
            status = device.status
            if not status:
                status = DeviceStatus(device_id=device.device_id)
                db.session.add(status)
            
            # 只有當狀態真的需要改變時才寫入，減少 DB 操作
            if status.is_on != should_turn_on:
                status.is_on = should_turn_on
                status.target_temperature = AUTO_STATE["target_temp"]
                db.session.commit()
                success = True
            else:
                success = True # 狀態本來就正確
                
            results.append({
                "device_name": device.device_name,
                "action": target_action,
                "success": success
            })
        except Exception as e:
            db.session.rollback()
            results.append({
                "device_name": device.device_name,
                "action": target_action,
                "success": False,
                "error": str(e)
            })
    return results

def perform_check():
    """執行一次溫度檢查與控制"""
    current_temp = get_latest_temperature()
    target_temp = AUTO_STATE["target_temp"]
    
    # 判斷邏輯
    if current_temp > target_temp:
        action = "turn_on"
        should_on = True
        reason = f"目前 {current_temp}°C 高於目標 {target_temp}°C，開啟冷氣"
    else:
        action = "turn_off"
        should_on = False
        reason = f"目前 {current_temp}°C 低於/等於目標 {target_temp}°C，關閉冷氣"
    
    # 執行控制 (在 app_context 下)
    controlled_list = control_air_conditioners(should_on)
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_temp": current_temp,
        "target_temp": target_temp,
        "action": action,
        "reason": reason,
        "devices_controlled": controlled_list
    }

# ==========================================
# 背景執行緒
# ==========================================
def monitor_loop(app):
    """背景監控迴圈"""
    print(f"🌡️ 自動監控已啟動 (每 {AUTO_STATE['monitor_interval']} 秒)")
    
    with app.app_context():
        while AUTO_STATE["monitor_enabled"]:
            try:
                result = perform_check()
                print(f"[AutoMonitor] {result['timestamp']} - {result['reason']}")
            except Exception as e:
                print(f"[AutoMonitor] Error: {e}")
            
            # 休息等待下一次檢查
            # 切分成小睡片段，以便能即時響應停止指令
            for _ in range(AUTO_STATE["monitor_interval"]):
                if not AUTO_STATE["monitor_enabled"]:
                    break
                time.sleep(1)
                
    print("🌡️ 自動監控已停止")

# ==========================================
# API Routes
# ==========================================

@bp.route("/check", methods=["GET"])
def check_now():
    """立即檢查並執行控制"""
    return jsonify({"ok": True, **perform_check()})

@bp.route("/config", methods=["GET", "POST"])
def handle_config():
    """讀取或修改設定 (解決了 global 變數問題)"""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        
        if "target_temp" in data:
            AUTO_STATE["target_temp"] = float(data["target_temp"])
            
        if "interval" in data:
            AUTO_STATE["monitor_interval"] = int(data["interval"])
            
        if "simulated_temp" in data:
            val = data["simulated_temp"]
            # 允許設為 null (清除模擬)
            try:
                AUTO_STATE["simulated_temp"] = float(val) if val is not None and val != "" else None
            except ValueError:
                AUTO_STATE["simulated_temp"] = None
            
        return jsonify({"ok": True, "msg": "設定已更新", "config": AUTO_STATE})
    
    return jsonify({"ok": True, **AUTO_STATE})

@bp.route("/monitor/start", methods=["POST"])
def start_monitor():
    """啟動背景監控"""
    global MONITOR_THREAD
    
    if AUTO_STATE["monitor_enabled"]:
        return jsonify({"ok": False, "msg": "監控已經在執行中"}), 400
        
    data = request.get_json(silent=True) or {}
    if "interval" in data:
        AUTO_STATE["monitor_interval"] = int(data["interval"])
        
    AUTO_STATE["monitor_enabled"] = True
    
    # 傳入 app 物件以確保 thread 有 context
    from flask import current_app
    # 使用 _get_current_object() 獲取真實的 app 物件
    app_obj = current_app._get_current_object()
    
    MONITOR_THREAD = threading.Thread(target=monitor_loop, args=(app_obj,), daemon=True)
    MONITOR_THREAD.start()
    
    return jsonify({
        "ok": True, 
        "msg": "背景監控已啟動", 
        "interval": AUTO_STATE["monitor_interval"]
    })

@bp.route("/monitor/stop", methods=["POST"])
def stop_monitor():
    """停止背景監控"""
    if not AUTO_STATE["monitor_enabled"]:
        return jsonify({"ok": False, "msg": "監控並未執行"}), 400
        
    AUTO_STATE["monitor_enabled"] = False
    return jsonify({"ok": True, "msg": "背景監控停止訊號已發送"})

@bp.route("/monitor/status", methods=["GET"])
def get_status():
    """取得監控狀態"""
    return jsonify({
        "ok": True, 
        "enabled": AUTO_STATE["monitor_enabled"],
        "target_temp": AUTO_STATE["target_temp"],
        "interval": AUTO_STATE["monitor_interval"]
    })

# 保留舊接口相容性 (可選)
@bp.route("/decide", methods=["GET", "POST"])
def decide_temp():
    # 簡單回應，不影響系統狀態
    t = request.args.get("temp", type=float)
    if not t:
        data = request.get_json(silent=True) or {}
        t = data.get("temp")
    
    if t is None: return jsonify({"ok": False})
    
    action = "turn_on" if t > AUTO_STATE["target_temp"] else "turn_off"
    return jsonify({"ok": True, "action": action, "current_temp": t})