# feature_device_control.py
# ==========================================
# 功能1：電器開關狀態與遠端控制
# ==========================================

from flask import Blueprint, request, jsonify    # 匯入 Flask 模組：藍圖、請求、回傳 JSON

bp = Blueprint("device", __name__, template_folder="templates")  # 建立 Blueprint 物件

DEVICE_STATE = {"aircon": False, "light": False}  # 模擬電器狀態（True=開，False=關）

@bp.get("/state")                                # 定義路由：取得電器狀態
def get_state():
    return jsonify(DEVICE_STATE)                 # 回傳 JSON 格式的狀態資料

@bp.post("/toggle")                              # 定義路由：切換電器狀態
def toggle_device():
    data = request.get_json(silent=True) or {}   # 從請求中取得 JSON 資料
    name = data.get("name")                      # 取得電器名稱
    on = data.get("on")                          # 取得是否開啟
    if name not in DEVICE_STATE or type(on) is not bool:  # 檢查資料格式
        return jsonify({"ok": False, "msg": "bad payload"}), 400  # 錯誤回應
    DEVICE_STATE[name] = on                      # 更新狀態
    return jsonify({"ok": True, "state": DEVICE_STATE})  # 回傳更新後結果
