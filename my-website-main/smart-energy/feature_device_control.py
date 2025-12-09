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
from sqlalchemy import exc as sa_exc, text

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
        try:
            is_on = d.status.is_on if d.status else False
        except sa_exc.OperationalError as oe:
            # 若資料庫缺少欄位 (例如 current_temperature 等)，記錄錯誤並使用預設值
            print(f"[get_all_device_states] DB operational error when loading status for device {d.device_id}: {oe}")
            is_on = False
        except Exception as e:
            print(f"[get_all_device_states] Unexpected error when loading status for device {d.device_id}: {e}")
            is_on = False
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
    # 支援傳入 device_id（較穩定）或 device_name（向後相容）
    device_id = data.get("device_id")
    name = data.get("name")
    on = data.get("on")

    # 驗證資料
    if not isinstance(on, bool) or (device_id is None and not name):
        return jsonify({"ok": False, "msg": "Invalid input: require 'on' (bool) and 'device_id' or 'name'"}), 400

    try:
        print(f"[toggle_device] payload: {data}")
        # 1. 根據 device_id 或 name 搜尋裝置（優先使用 id）
        if device_id is not None:
            try:
                device_id = int(device_id)
            except Exception:
                return jsonify({"ok": False, "msg": "Invalid device_id"}), 400
            target_device = Device.query.get(device_id)
        else:
            target_device = Device.query.filter_by(device_name=name).first()
        print(f"[toggle_device] target_device: {getattr(target_device, 'device_id', None)} / {getattr(target_device, 'device_name', None)}")
        if not target_device:
            key = f"id {device_id}" if device_id is not None else f"name '{name}'"
            return jsonify({"ok": False, "msg": f"Device {key} not found"}), 404
        
        # 2. 使用原生 SQL 安全地取得或建立狀態紀錄 (避免 ORM 在映射時因缺少欄位而失敗)
        status_table_issue = False
        created_new = False
        fresh_is_on = False
        try:
            # 直接查 is_on 欄位（若欄位存在於資料表）
            pre = db.session.execute(text("SELECT * FROM device_status WHERE device_id = :id"), {"id": target_device.device_id}).fetchall()
            print(f"[toggle_device] pre-update device_status rows: {pre}")
            sel = db.session.execute(
                text("SELECT is_on FROM device_status WHERE device_id = :id"),
                {"id": target_device.device_id}
            ).fetchone()
            if sel is None:
                # 無紀錄 -> 新增一筆
                db.session.execute(
                    text("INSERT INTO device_status (device_id, is_on) VALUES (:id, :on)"),
                    {"id": target_device.device_id, "on": bool(on)}
                )
                created_new = True
            else:
                # 更新現有紀錄
                db.session.execute(
                    text("UPDATE device_status SET is_on = :on WHERE device_id = :id"),
                    {"on": bool(on), "id": target_device.device_id}
                )

            db.session.commit()

            # 再次讀取最新值
            sel2 = db.session.execute(
                text("SELECT is_on FROM device_status WHERE device_id = :id"),
                {"id": target_device.device_id}
            ).fetchone()
            post = db.session.execute(text("SELECT * FROM device_status WHERE device_id = :id"), {"id": target_device.device_id}).fetchall()
            print(f"[toggle_device] post-update device_status rows: {post}")
            fresh_is_on = bool(sel2[0]) if sel2 is not None else False

        except sa_exc.OperationalError as oe:
            # 若直接 SQL 執行也發生 OperationalError，記錄並標示
            print(f"[toggle_device] OperationalError when touching device_status for device {target_device.device_id}: {oe}")
            db.session.rollback()
            status_table_issue = True
            fresh_is_on = False
        except Exception as e:
            print(f"[toggle_device] Unexpected error when touching device_status: {e}")
            db.session.rollback()
            return jsonify({"ok": False, "msg": str(e)}), 500

        # 3. 回傳最新狀態並增加被切換的裝置資訊
        states = _get_all_device_states()
        toggled_info = {"device_id": target_device.device_id, "device_name": target_device.device_name, "is_on": fresh_is_on, "created_new_status": created_new}
        if status_table_issue:
            toggled_info["status_table_issue"] = True
        print(f"[toggle_device] toggled: {toggled_info}")
        return jsonify({"ok": True, "state": states, "toggled": toggled_info})
        
    except Exception as e:
        db.session.rollback() # 發生錯誤時回滾，避免資料庫鎖死
        print(f"Error toggling device: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500

@bp.get("/list")
def get_device_list():
    """取得所有設備列表（含詳細資訊、狀態）"""
    try:
        # 查詢所有設備（包含已停用的）
        print("[device_list] fetching devices from DB...")
        devices = Device.query.all()
        print(f"[device_list] fetched {len(devices)} devices")
        status_load_error = False
        
        # 整理成詳細資訊列表
        device_list = []
        for d in devices:
            # 取得狀態資訊
            status_info = None
            try:
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
            except sa_exc.OperationalError as oe:
                # 發生資料庫操作錯誤（例如欄位不存在），回退為預設狀態但不要中斷整個清單
                print(f"[get_device_list] OperationalError when loading status for device {d.device_id}: {oe}")
                status_load_error = True
                status_info = {
                    "is_on": False,
                    "current_temperature": None,
                    "target_temperature": None,
                    "mode": None
                }
            except Exception as e:
                print(f"[get_device_list] Unexpected error when loading status for device {d.device_id}: {e}")
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
        
        resp = {"ok": True, "devices": device_list, "count": len(device_list)}
        if status_load_error:
            resp["status_load_error"] = True
            resp["status_load_msg"] = "Some device status fields could not be loaded (DB schema mismatch)."
        return jsonify(resp)
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"Error fetching device list: {e}\n{tb}")
        # 回傳詳細錯誤資訊以便前端偵錯（開發環境用）
        return jsonify({"ok": False, "msg": str(e), "trace": tb}), 500

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
        # 決定要分配的 device_id：使用最小可用的正整數（填補被刪除的 ID）
        try:
            existing = db.session.execute(text("SELECT device_id FROM devices ORDER BY device_id ASC")).fetchall()
            existing_ids = [r[0] for r in existing]
            next_id = 1
            for eid in existing_ids:
                if eid == next_id:
                    next_id += 1
                elif eid > next_id:
                    break
        except Exception as e:
            print(f"[add_device] warning computing next_id: {e}")
            # fallback to letting DB assign via autoincrement
            next_id = None

        # 建立新設備並指定 device_id（若成功計算到 next_id）
        if next_id:
            new_device = Device(
                device_id=next_id,
                user_id=user_id,
                device_name=device_name,
                device_type=device_type,
                model_number=data.get("model_number"),
                location=data.get("location"),
                rated_power=data.get("rated_power"),
                is_active=data.get("is_active", True)  # 預設為啟用
            )
        else:
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
        db.session.flush()  # 取得 device_id (無論是指定或 autoincrement)
        
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
        # 以純 SQL 方式處理，避免透過 ORM 觸發關聯讀取導致 schema mismatch
        row = db.session.execute(text("SELECT device_name FROM devices WHERE device_id = :id"), {"id": device_id}).fetchone()
        if not row:
            return jsonify({"ok": False, "msg": f"Device with ID {device_id} not found"}), 404
        device_name = row[0]

        # 刪除 device_status（如果存在）
        try:
            db.session.execute(text("DELETE FROM device_status WHERE device_id = :id"), {"id": device_id})
        except Exception as e:
            print(f"[remove_device] warning deleting device_status: {e}")

        # 刪除 power_logs（如果存在）
        try:
            db.session.execute(text("DELETE FROM power_logs WHERE device_id = :id"), {"id": device_id})
        except Exception as e:
            print(f"[remove_device] warning deleting power_logs: {e}")

        # 刪除 devices
        db.session.execute(text("DELETE FROM devices WHERE device_id = :id"), {"id": device_id})
        db.session.commit()

        return jsonify({"ok": True, "msg": f"Device '{device_name}' (ID: {device_id}) deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting device: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500
