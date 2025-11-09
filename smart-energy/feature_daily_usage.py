# feature_daily_usage.py
# ==========================================
# 功能2：每日用電量與電費統計
# ==========================================

from flask import Blueprint, jsonify, request      # 匯入 Flask 相關模組
from datetime import date                          # 匯入日期模組

bp = Blueprint("usage", __name__, template_folder="templates")  # 建立 Blueprint

MOCK_USAGE = {                                    # 模擬資料：每日用電量
    "2025-11-01": 12.3,
    "2025-11-02": 10.1,
    "2025-11-03": 14.8,
}
RATE = 2.625                                      # 假設每度電費

@bp.get("/daily")                                # 路由：取得每日用電資料
def daily_kwh():
    return jsonify(MOCK_USAGE)                    # 回傳模擬資料

@bp.get("/bill")                                 # 路由：計算總電費
def calc_bill():
    total_kwh = sum(MOCK_USAGE.values())          # 計算總用電量
    bill = round(total_kwh * RATE, 2)             # 計算電費
    return jsonify({"total_kwh": total_kwh, "bill": bill, "rate": RATE})  # 回傳結果

@bp.post("/add")                                 # 路由：新增每日用電記錄
def add_usage():
    data = request.get_json(silent=True) or {}    # 取得傳入 JSON
    kwh = data.get("kwh")                         # 取得電量
    day = data.get("day", str(date.today()))      # 若未指定日期則預設今日
    if not isinstance(kwh, (int, float)):         # 檢查資料格式
        return jsonify({"ok": False, "msg": "kwh required"}), 400
    MOCK_USAGE[day] = float(kwh)                  # 儲存新資料
    return jsonify({"ok": True, "daily": MOCK_USAGE})  # 回傳更新後資料
