# feature_device_control.py
# ==========================================
# 電器控制功能：
# - GET   /device/state   取得所有電器開關狀態
# - PATCH /device/toggle  遠端控制指定電器開關
# ==========================================

from flask import Blueprint, request, jsonify    # 匯入 Flask 模組：藍圖、請求、回傳 JSON

bp = Blueprint("device", __name__, template_folder="templates")  # 建立 Blueprint 物件

DEVICE_STATE = {
    "aircon": False,   # 冷氣
    "light": False,    # 照明燈
}  # 模擬電器狀態（True=開，False=關）

@bp.get("/state")
def get_state():
    """取得目前所有電器狀態"""
    # 把 DEVICE_STATE 包成 JSON 回傳給前端
    return jsonify({"ok": True, "state": DEVICE_STATE})

@bp.patch("/toggle")
def toggle_device():
    """切換指定電器的開關（遠端控制）"""
    # 從請求裡拿 JSON，拿不到就給一個空 dict
    data = request.get_json(silent=True) or {}

    # 要控制的電器名稱，如 "aircon"、"light"
    name = data.get("name")
    # 希望設定成什麼狀態：True(開) / False(關)
    on = data.get("on")

    # 檢查：電器名稱是否存在
    if name not in DEVICE_STATE:
        msg = f"Invalid device name: '{name}'. Available devices: {list(DEVICE_STATE.keys())}"
        return jsonify({"ok": False, "msg": msg}), 400

    # 檢查：'on' 的值是否為布林值
    if not isinstance(on, bool):
        return jsonify({"ok": False, "msg": "Value for 'on' must be a boolean (true/false)."}), 400

    # 更新記憶體中電器狀態
    DEVICE_STATE[name] = on

    # 回傳更新後的完整狀態，讓前端同步畫面
    return jsonify({"ok": True, "state": DEVICE_STATE})
