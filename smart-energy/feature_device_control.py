# feature_device_control.py
# ==========================================
# 電器控制功能 (Database Version)：
# - GET   /device/state   從資料庫取得所有電器開關狀態
# - PATCH /device/toggle  更新資料庫中的電器開關狀態
# - GET   /device/list    取得所有設備列表（含詳細資訊、狀態）
# - POST  /device/add     新增設備
# - DELETE /device/remove/<device_id>  刪除設備
# ==========================================

from flask import Blueprint, request, jsonify
from models import db, Device, DeviceStatus

# 建立 Blueprint 物件 (只要定義一次就好)
bp = Blueprint("device", __name__)

def _get_all_device_states():
    """輔助函數：從資料庫取得所有電器狀態（內部使用）"""
    # 1. 查詢所有啟用中的裝置 (WHERE is_active = True)
    devices = Device.query.filter_by(is_active=True).all()
    
    # 2. 整理成前端需要的格式 { "設備名稱": True/False }
    states = {}
    for d in devices:
        # 透過 relationship 取得 status，如果沒資料預設為 False
        is_on = d.status.is_on if d.status else False
        states[d.device_name] = is_on
    
    return states

@bp.get("/state")
def get_state():
    """從資料庫取得所有電器狀態"""
    try:
        states = _get_all_device_states()
        return jsonify({"ok": True, "state": states})
        
    except Exception as e:
        print(f"Error fetching state: {e}")
        return jsonify({"ok": False, "msg": "Database error"}), 500

@bp.patch("/toggle")
def toggle_device():
    """更新資料庫中的電器開關狀態"""
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    on = data.get("on")

    # 驗證資料
    if not name or not isinstance(on, bool):
        return jsonify({"ok": False, "msg": "Invalid input"}), 400

    try:
        # 1. 搜尋該裝置
        target_device = Device.query.filter_by(device_name=name).first()
        
        if not target_device:
            return jsonify({"ok": False, "msg": f"Device '{name}' not found"}), 404
        
        # 2. 取得或建立狀態紀錄
        status_record = target_device.status
        
        if not status_record:
            # 如果資料庫裡這台裝置還沒有狀態紀錄，幫它新增一筆
            status_record = DeviceStatus(device_id=target_device.device_id, is_on=on)
            db.session.add(status_record)
        else:
            # 如果有紀錄，直接更新
            status_record.is_on = on
            
        # 3. 提交變更 (Commit)
        db.session.commit()
        
        # 4. 回傳最新狀態
        states = _get_all_device_states()
        return jsonify({"ok": True, "state": states})
        
    except Exception as e:
        db.session.rollback() # 發生錯誤時回滾，避免資料庫鎖死
        print(f"Error toggling device: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500

@bp.get("/list")
def get_device_list():
    """取得所有設備列表（含詳細資訊、狀態）"""
    try:
        # 查詢所有設備（包含已停用的）
        devices = Device.query.all()
        
        # 整理成詳細資訊列表
        device_list = []
        for d in devices:
            # 取得狀態資訊
            status_info = None
            if d.status:
                status_info = {
                    "is_on": d.status.is_on,
                    "current_temperature": float(d.status.current_temperature) if d.status.current_temperature else None,
                    "target_temperature": float(d.status.target_temperature) if d.status.target_temperature else None,
                    "mode": d.status.mode
                }
            else:
                # 如果沒有狀態記錄，使用預設值
                status_info = {
                    "is_on": False,
                    "current_temperature": None,
                    "target_temperature": None,
                    "mode": None
                }
            
            device_info = {
                "device_id": d.device_id,
                "device_name": d.device_name,
                "device_type": d.device_type,
                "model_number": d.model_number,
                "location": d.location,
                "rated_power": float(d.rated_power) if d.rated_power else None,
                "is_active": d.is_active,
                "user_id": d.user_id,
                "status": status_info
            }
            device_list.append(device_info)
        
        return jsonify({"ok": True, "devices": device_list, "count": len(device_list)})
        
    except Exception as e:
        print(f"Error fetching device list: {e}")
        return jsonify({"ok": False, "msg": "Database error"}), 500

@bp.post("/add")
def add_device():
    """新增設備"""
    data = request.get_json(silent=True) or {}
    
    # 必填欄位驗證
    device_name = data.get("device_name")
    device_type = data.get("device_type")
    user_id = data.get("user_id")
    
    if not device_name or not device_type or not user_id:
        return jsonify({
            "ok": False, 
            "msg": "Missing required fields: device_name, device_type, user_id"
        }), 400
    
    # 驗證 device_type 是否為有效值
    if device_type not in ['air_conditioner', 'light']:
        return jsonify({
            "ok": False,
            "msg": "Invalid device_type. Must be 'air_conditioner' or 'light'"
        }), 400
    
    # 檢查設備名稱是否已存在
    existing_device = Device.query.filter_by(device_name=device_name).first()
    if existing_device:
        return jsonify({
            "ok": False,
            "msg": f"Device with name '{device_name}' already exists"
        }), 409
    
    try:
        # 建立新設備
        new_device = Device(
            user_id=user_id,
            device_name=device_name,
            device_type=device_type,
            model_number=data.get("model_number"),
            location=data.get("location"),
            rated_power=data.get("rated_power"),
            is_active=data.get("is_active", True)  # 預設為啟用
        )
        
        db.session.add(new_device)
        db.session.flush()  # 取得 device_id
        
        # 可選：如果提供了初始狀態，建立狀態記錄
        if data.get("create_status", False):
            initial_status = DeviceStatus(
                device_id=new_device.device_id,
                is_on=data.get("initial_is_on", False),
                current_temperature=data.get("initial_current_temperature"),
                target_temperature=data.get("initial_target_temperature"),
                mode=data.get("initial_mode")
            )
            db.session.add(initial_status)
        
        db.session.commit()
        
        # 回傳新建立的設備資訊
        device_info = {
            "device_id": new_device.device_id,
            "device_name": new_device.device_name,
            "device_type": new_device.device_type,
            "model_number": new_device.model_number,
            "location": new_device.location,
            "rated_power": float(new_device.rated_power) if new_device.rated_power else None,
            "is_active": new_device.is_active,
            "user_id": new_device.user_id
        }
        
        return jsonify({"ok": True, "msg": "Device added successfully", "device": device_info}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding device: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500

@bp.delete("/remove/<int:device_id>")
def remove_device(device_id):
    """刪除設備"""
    try:
        # 查找設備
        target_device = Device.query.get(device_id)
        
        if not target_device:
            return jsonify({"ok": False, "msg": f"Device with ID {device_id} not found"}), 404
        
        # 保存設備名稱用於回應
        device_name = target_device.device_name
        
        # 先手動刪除相關的狀態記錄，避免 SQLAlchemy 嘗試將 device_id 設為 NULL
        if target_device.status:
            db.session.delete(target_device.status)
        
        # 刪除設備（由於外鍵約束設置為 ON DELETE CASCADE，
        # 相關的 power_logs 會自動刪除）
        db.session.delete(target_device)
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "msg": f"Device '{device_name}' (ID: {device_id}) deleted successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting device: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500