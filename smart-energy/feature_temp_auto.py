# feature_temp_auto.py
# ==========================================
# 功能3：溫度判斷並自動開關電器
# ==========================================

from flask import Blueprint, request, jsonify     # 匯入 Flask 相關模組

bp = Blueprint("auto", __name__, template_folder="templates")  # 建立 Blueprint

TARGET_TEMP = 26.0                               # 設定溫度閾值
STATE = {"aircon": False}                        # 模擬空調狀態

@bp.post("/decide")                              # 定義路由：根據溫度判斷
def decide_by_temp():
    data = request.get_json(silent=True) or {}   # 取得傳入 JSON
    t = data.get("temp")                         # 取得溫度
    if not isinstance(t, (int, float)):          # 檢查格式
        return jsonify({"ok": False, "msg": "temp required"}), 400
    if t > TARGET_TEMP:                          # 若高於閾值則開冷氣
        STATE["aircon"] = True
        action = "turn_on"
    else:                                        # 否則關閉冷氣
        STATE["aircon"] = False
        action = "turn_off"
    return jsonify({"ok": True, "action": action, "state": STATE, "target": TARGET_TEMP})  # 回傳結果
