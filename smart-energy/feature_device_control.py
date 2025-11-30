# feature_device_control.py
# ==========================================
# 電器控制功能 (Database Version)：
# - GET   /device/state   從資料庫取得所有電器開關狀態
# - PATCH /device/toggle  更新資料庫中的電器開關狀態
# ==========================================

from flask import Blueprint, request, jsonify
from models import db, Device, DeviceStatus

# 建立 Blueprint 物件 (只要定義一次就好)
bp = Blueprint("device", __name__)

@bp.get("/state")
def get_state():
    """從資料庫取得所有電器狀態"""
    try:
        # 1. 查詢所有啟用中的裝置 (WHERE is_active = True)
        devices = Device.query.filter_by(is_active=True).all()
        
        # 2. 整理成前端需要的格式 { "設備名稱": True/False }
        states = {}
        for d in devices:
            # 透過 relationship 取得 status，如果沒資料預設為 False
            is_on = d.status.is_on if d.status else False
            states[d.device_name] = is_on
            
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
        return get_state()
        
    except Exception as e:
        db.session.rollback() # 發生錯誤時回滾，避免資料庫鎖死
        print(f"Error toggling device: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500