# feature_daily_usage.py
# ==========================================
# 功能2：每日用電量與電費統計（真實數據版）
# 使用台電累進費率制度
# 使用資料庫儲存
# ==========================================
# API 端點：
# - GET  /usage/daily    取得每日用電量統計
#                       查詢參數: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)
#                       預設查詢最近 7 天
#                       回傳: 每日用電量、電費（加總/累進費率）、設備明細
#
# - GET  /usage/bill     計算總用電量與總電費（依月份分別計算）
#                       回傳總用電量、總電費（加總/累進費率）、各月份統計
#
# - POST /usage/add     新增一筆用電紀錄
#                       請求體: {
#                         "device_id": int (必填),
#                         "kwh": float (可選，直接提供度數),
#                         "power_watts": float (可選，功率瓦數),
#                         "hours": float (可選，使用時數),
#                         "day": str (可選，日期 YYYY-MM-DD，預設今天)
#                       }
#                       必須提供 kwh 或 hours 其中一個
#
# - GET  /usage/monthly/<year>/<month>  取得指定月份的用電統計
#                       回傳: 月總用電量、總電費、每日明細
#
# - GET  /usage/yearly/<year>           取得指定年份的用電統計
#                       回傳: 年總用電量、總電費、每月明細
#
# - GET  /usage/compare                 比較兩個時間段的用電統計
#                       查詢參數: period_type (day/month/year), date1, date2
#                       回傳: 兩個時間段的統計與比較結果
#
# - POST /usage/batch                   批次新增多筆用電記錄
#                       請求體: {"records": [...]} - 多筆記錄陣列
# ==========================================

from flask import Blueprint, jsonify, request
from models import db, PowerLog
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from decimal import Decimal

bp = Blueprint("usage", __name__, template_folder="templates")

# 台電住宅用電累進費率（元/度）
# 夏月（6-9月）與非夏月費率 - 2025年最新費率
TAIPOWER_RATES = {
    "summer": [
        (120, 1.78),      # 0-120度
        (330, 2.55),      # 121-330度
        (500, 3.80),      # 331-500度
        (700, 5.14),      # 501-700度
        (1000, 6.44),     # 701-1000度
        (float('inf'), 8.86)  # 1001度以上
    ],
    "non_summer": [
        (120, 1.78),      # 0-120度
        (330, 2.26),      # 121-330度
        (500, 3.13),      # 331-500度
        (700, 4.24),      # 501-700度
        (1000, 5.27),     # 701-1000度
        (float('inf'), 7.03)  # 1001度以上
    ]
}

def calculate_taiwan_bill(total_kwh, usage_date):
    """
    根據台電累進費率計算電費
    
    Args:
        total_kwh: 當月累積用電度數
        usage_date: 日期物件 (date 或 datetime)
    
    Returns:
        計算出的電費金額（元）
    """
    # 判斷夏月或非夏月（6-9月為夏月）
    if isinstance(usage_date, str):
        usage_date = datetime.strptime(usage_date, "%Y-%m-%d").date()
    
    is_summer = 6 <= usage_date.month <= 9
    rates = TAIPOWER_RATES["summer"] if is_summer else TAIPOWER_RATES["non_summer"]
    
    # 累進計算電費
    total_bill = 0
    remaining_kwh = total_kwh
    prev_tier = 0
    
    for tier_limit, rate in rates:
        if remaining_kwh <= 0:
            break
        
        # 計算這個級距要使用的度數
        tier_kwh = min(remaining_kwh, tier_limit - prev_tier)
        total_bill += tier_kwh * rate
        remaining_kwh -= tier_kwh
        prev_tier = tier_limit
    
    return round(total_bill, 2)


def get_monthly_total_kwh(target_date, include_target_date=False):
    """
    取得指定日期所屬月份的累積用電量（使用 SQLAlchemy 直接查詢）
    
    Args:
        target_date: 目標日期
        include_target_date: 是否包含目標日期當天的用電量
    
    Returns:
        當月累積用電量（度）
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    # 計算月份的開始日期
    month_start = date(target_date.year, target_date.month, 1)
    
    # 使用 SQLAlchemy 查詢
    query = db.session.query(func.sum(PowerLog.energy_consumed)).filter(
        PowerLog.log_date >= month_start
    )
    
    if include_target_date:
        query = query.filter(PowerLog.log_date <= target_date)
    else:
        query = query.filter(PowerLog.log_date < target_date)
    
    result = query.scalar()
    return float(result) if result else 0


def get_daily_total_kwh_db(target_date, exclude_device_id=None):
    """
    取得指定日期當天所有設備的總用電量（使用 SQLAlchemy 直接查詢）
    
    Args:
        target_date: 目標日期
        exclude_device_id: 排除特定設備ID
    
    Returns:
        當天總用電量（度）
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    query = db.session.query(func.sum(PowerLog.energy_consumed)).filter(
        PowerLog.log_date == target_date
    )
    
    if exclude_device_id is not None:
        query = query.filter(PowerLog.device_id != exclude_device_id)
    
    result = query.scalar()
    return float(result) if result else 0


# ==========================================
# Helper Functions for Database Queries
# ==========================================

def _to_float(value):
    """將 Decimal 或其他數值類型轉換為 float"""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _get_logs_in_date_range(start_date, end_date):
    """
    使用 SQLAlchemy 查詢指定日期範圍內的記錄
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
    
    Returns:
        PowerLog 記錄列表
    """
    return db.session.query(PowerLog).filter(
        PowerLog.log_date >= start_date,
        PowerLog.log_date <= end_date
    ).order_by(PowerLog.log_date, PowerLog.created_at).all()


def _aggregate_by_date(logs):
    """
    將記錄按日期分組並計算總和
    
    Args:
        logs: PowerLog 記錄列表
    
    Returns:
        dict: {date: {"kwh": total, "cost": total, "devices": [...]}}
    """
    result = {}
    for log in logs:
        day_key = str(log.log_date)
        if day_key not in result:
            result[day_key] = {
                "kwh": 0,
                "cost": 0,
                "devices": []
            }
        result[day_key]["kwh"] += _to_float(log.energy_consumed)
        result[day_key]["cost"] += _to_float(log.cost)
        result[day_key]["devices"].append({
            "device_id": log.device_id,
            "kwh": round(_to_float(log.energy_consumed), 4),
            "cost": round(_to_float(log.cost), 2)
        })
    
    # Round totals
    for day_key in result:
        result[day_key]["kwh"] = round(result[day_key]["kwh"], 4)
        result[day_key]["cost"] = round(result[day_key]["cost"], 2)
    
    return result


@bp.get("/daily")
def get_daily_usage():
    """
    取得每日用電量統計
    支援查詢參數：
    - start_date: 開始日期 (YYYY-MM-DD)，預設為 7 天前
    - end_date: 結束日期 (YYYY-MM-DD)，預設為今天
    
    回傳格式：
    {
        "2025-11-12": {
            "kwh": 16.7,
            "cost_sum": 53.44,
            "cost_progressive": 54.20,
            "devices": [...]
        },
        ...
    }
    """
    # 解析查詢參數
    end_date_str = request.args.get("end_date")
    start_date_str = request.args.get("start_date")
    
    # 預設為最近 7 天
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    else:
        end_date = date.today()
    
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    else:
        start_date = end_date - timedelta(days=6)
    
    # 使用 SQLAlchemy 查詢指定日期範圍的記錄
    logs = _get_logs_in_date_range(start_date, end_date)
    
    if not logs:
        return jsonify({})
    
    # 按日期分組
    daily_data = {}
    for log in logs:
        day_key = str(log.log_date)
        if day_key not in daily_data:
            daily_data[day_key] = {
                "logs": [],
                "kwh": 0,
                "cost_sum": 0
            }
        daily_data[day_key]["logs"].append(log)
        daily_data[day_key]["kwh"] += _to_float(log.energy_consumed)
        daily_data[day_key]["cost_sum"] += _to_float(log.cost)
    
    # 構建結果
    result = {}
    for day_str, data in daily_data.items():
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
        total_kwh = data["kwh"]
        cost_sum = data["cost_sum"]
        
        # 使用台電累進費率重新計算當天電費
        month_total_before = get_monthly_total_kwh(day, include_target_date=False)
        month_total_after = month_total_before + total_kwh
        
        bill_before = calculate_taiwan_bill(month_total_before, day)
        bill_after = calculate_taiwan_bill(month_total_after, day)
        cost_progressive = bill_after - bill_before
        
        # 各設備明細
        devices = []
        for log in data["logs"]:
            devices.append({
                "device_id": log.device_id,
                "kwh": round(_to_float(log.energy_consumed), 4),
                "cost": round(_to_float(log.cost), 2)
            })
        
        result[day_str] = {
            "kwh": round(total_kwh, 4),
            "cost_sum": round(cost_sum, 2),
            "cost_progressive": round(cost_progressive, 2),
            "devices": devices
        }
    
    return jsonify(result)


@bp.get("/bill")
def get_total_bill():
    """
    計算總用電量與總電費（依月份分別計算）
    使用 SQLAlchemy 直接查詢，提供兩種計算方式：
    1. cost_sum: 各設備電費加總
    2. cost_progressive: 用累進費率重新計算的月總電費
    """
    # 使用 SQLAlchemy 查詢所有記錄的總和
    total_result = db.session.query(
        func.sum(PowerLog.energy_consumed).label('total_kwh'),
        func.sum(PowerLog.cost).label('total_cost')
    ).first()
    
    if not total_result or total_result.total_kwh is None:
        return jsonify({"total_kwh": 0, "total_cost_sum": 0, "total_cost_progressive": 0, "months": []})
    
    total_kwh = _to_float(total_result.total_kwh)
    total_cost_sum = _to_float(total_result.total_cost)
    
    # 按月份統計
    monthly_result = db.session.query(
        extract('year', PowerLog.log_date).label('year'),
        extract('month', PowerLog.log_date).label('month'),
        func.sum(PowerLog.energy_consumed).label('kwh'),
        func.sum(PowerLog.cost).label('cost')
    ).group_by(
        extract('year', PowerLog.log_date),
        extract('month', PowerLog.log_date)
    ).order_by(
        extract('year', PowerLog.log_date),
        extract('month', PowerLog.log_date)
    ).all()
    
    monthly_stats = []
    total_cost_progressive = 0
    
    for row in monthly_result:
        year = int(row.year)
        month = int(row.month)
        month_kwh = _to_float(row.kwh)
        month_cost_sum = _to_float(row.cost)
        
        year_month = f"{year}-{month:02d}"
        sample_date = date(year, month, 1)
        is_summer = 6 <= month <= 9
        
        # 用累進費率重新計算該月總電費
        month_cost_progressive = calculate_taiwan_bill(month_kwh, sample_date)
        total_cost_progressive += month_cost_progressive
        
        monthly_stats.append({
            "month": year_month,
            "kwh": round(month_kwh, 2),
            "cost_sum": round(month_cost_sum, 2),
            "cost_progressive": round(month_cost_progressive, 2),
            "season": "夏月" if is_summer else "非夏月",
            "difference": round(month_cost_progressive - month_cost_sum, 2)
        })

    return jsonify({
        "total_kwh": round(total_kwh, 2),
        "total_cost_sum": round(total_cost_sum, 2),
        "total_cost_progressive": round(total_cost_progressive, 2),
        "months": monthly_stats,
        "billing_method": "台電累進費率",
        "explanation": {
            "cost_sum": "各設備電費加總（邊際費率）",
            "cost_progressive": "月累積用電量重新計算（實際台電帳單）"
        }
    })


@bp.post("/add")
def add_usage():
    """
    新增一筆用電紀錄（修正版：即時累進計算）
    正確考慮同一天稍早已新增的記錄，確保累進費率計算準確
    """
    data = request.get_json(silent=True) or {}

    device_id = data.get("device_id")
    kwh = data.get("kwh")
    power_watts = data.get("power_watts")  # 瓦數（可選，若不提供則從 devices 表讀取）
    hours = data.get("hours")  # 使用時間（小時）
    day_str = data.get("day", str(date.today()))  # 傳進來的日期字串

    if not device_id:
        return jsonify({"ok": False, "msg": "device_id 必填"}), 400

    # 檢查輸入：必須提供 kwh 或 hours
    if kwh is not None:
        # 方式1: 直接提供度數
        if not isinstance(kwh, (int, float)):
            return jsonify({"ok": False, "msg": "kwh 必須是數字"}), 400
        calculated_kwh = kwh
        calculation_method = "direct"
        power_info = None
        power_watts = None  # 直接提供 kWh 時不記錄瓦數
    elif hours is not None:
        # 方式2: 從使用時數計算（自動讀取設備額定功率）
        if not isinstance(hours, (int, float)):
            return jsonify({"ok": False, "msg": "hours 必須是數字"}), 400
        
        # 如果沒有提供 power_watts，從 devices 表讀取額定功率
        if power_watts is None:
            device_query = db.session.execute(
                db.text("SELECT rated_power FROM devices WHERE device_id = :device_id"),
                {"device_id": device_id}
            ).fetchone()
            
            if not device_query or device_query[0] is None:
                return jsonify({
                    "ok": False, 
                    "msg": f"設備 {device_id} 不存在或未設定額定功率"
                }), 400
            
            # rated_power 是 kW，轉換成瓦特
            rated_power_kw = float(device_query[0])
            power_watts = rated_power_kw * 1000
        else:
            # 如果有提供 power_watts，檢查是否為數字
            if not isinstance(power_watts, (int, float)):
                return jsonify({"ok": False, "msg": "power_watts 必須是數字"}), 400
        
        # 計算用電量: 瓦數 × 小時數 ÷ 1000 = 度數（kWh）
        calculated_kwh = round((power_watts * hours) / 1000, 4)
        calculation_method = "calculated"
        power_info = {
            "power_watts": power_watts,
            "hours": hours,
            "formula": f"{power_watts}W × {hours}h ÷ 1000 = {calculated_kwh} kWh"
        }
    else:
        return jsonify({
            "ok": False, 
            "msg": "請提供 kwh 或 hours（系統會自動讀取設備額定功率）"
        }), 400

    # 使用計算出的度數
    kwh = calculated_kwh

    # 轉成 date 物件
    current_date = datetime.strptime(day_str, "%Y-%m-%d").date() if isinstance(day_str, str) else day_str

    # ==========================================
    # 核心修正：計算「目前這筆資料」該落在哪個級距
    # ==========================================
    
    # 1. 取得「本月截至昨天」的累積用電 (Base A)
    #    (include_target_date=False 代表只算到 target_date 的前一天)
    base_month_kwh = get_monthly_total_kwh(current_date, include_target_date=False)

    # 2. 取得「今天稍早已經新增」的累積用電 (Base B)
    #    這一步非常重要！原本的程式漏了這段，導致同一天的資料彼此「互不認識」
    #    使用 SQLAlchemy 直接查詢資料庫
    base_today_kwh_result = db.session.query(
        func.sum(PowerLog.energy_consumed)
    ).filter(
        PowerLog.log_date == current_date
    ).scalar()
    base_today_kwh = _to_float(base_today_kwh_result) if base_today_kwh_result else 0

    # 3. 算出「計算本筆電費前的總累積度數」
    #    (本月總累積 = 昨以前 + 今天已存)
    current_cumulative_kwh = base_month_kwh + base_today_kwh

    # 4. 計算加入本筆後的「新累積度數」
    new_cumulative_kwh = current_cumulative_kwh + kwh

    # ==========================================
    # 開始算錢 (使用台電累進費率)
    # ==========================================
    
    # 算式：(加了這筆後的總電費) - (還沒加這筆前的總電費) = 這筆電的真實邊際成本
    bill_before = calculate_taiwan_bill(current_cumulative_kwh, current_date)
    bill_after = calculate_taiwan_bill(new_cumulative_kwh, current_date)
    
    real_cost = round(bill_after - bill_before, 2)
    
    # 計算平均費率 (四捨五入到小數點後2位，避免浮點數誤差)
    avg_rate = round(real_cost / kwh, 2) if kwh > 0 else 0

    # ==========================================
    # 存入資料庫
    # ==========================================
    try:
        new_log = PowerLog(
            device_id=device_id,
            power_watts=power_watts if calculation_method == "calculated" else None,
            hours=hours if calculation_method == "calculated" else None,
            log_date=current_date,
            energy_consumed=kwh,
            cost=real_cost,
            electricity_rate=avg_rate
        )
        db.session.add(new_log)
        db.session.commit()
        
        # 重新整理以取得自動產生的 log_id
        db.session.refresh(new_log)
        new_row = new_log.to_dict()
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "msg": f"儲存失敗: {str(e)}"}), 500

    response_data = {
        "ok": True, 
        "new_data": new_row,
        "debug_info": {
            "month_base_kwh": float(base_month_kwh),
            "today_base_kwh": float(base_today_kwh),
            "total_accumulated_before": float(current_cumulative_kwh),
            "total_accumulated_after": float(new_cumulative_kwh),
            "this_tier_rate": avg_rate,
            "calculation_method": calculation_method
        }
    }
    
    # 如果是從瓦數計算的，加入計算資訊
    if power_info:
        response_data["power_calculation"] = power_info
    
    return jsonify(response_data)


# ==========================================
# 新增 API 端點
# ==========================================

@bp.route("/monthly/<int:year>/<int:month>", methods=["GET"])
def get_monthly_summary(year, month):
    """
    取得指定月份的用電統計
    
    URL: GET /usage/monthly/<year>/<month>
    
    回傳：
    - total_kwh: 該月總用電量
    - total_cost: 該月總電費
    - daily_breakdown: 每日用電明細
    - days_with_data: 有資料的天數
    """
    try:
        # 計算該月的開始和結束日期
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # 查詢該月的每日統計
        daily_stats = db.session.query(
            PowerLog.log_date,
            func.sum(PowerLog.energy_consumed).label('kwh'),
            func.sum(PowerLog.cost).label('cost'),
            func.count(PowerLog.log_id).label('record_count')
        ).filter(
            PowerLog.log_date >= start_date,
            PowerLog.log_date <= end_date
        ).group_by(PowerLog.log_date).order_by(PowerLog.log_date).all()
        
        # 計算月總計
        total_kwh = sum(_to_float(row.kwh) for row in daily_stats)
        total_cost = sum(_to_float(row.cost) for row in daily_stats)
        
        # 建立每日明細
        daily_breakdown = [
            {
                "date": row.log_date.strftime("%Y-%m-%d"),
                "kwh": round(_to_float(row.kwh), 2),
                "cost": round(_to_float(row.cost), 2),
                "record_count": row.record_count
            }
            for row in daily_stats
        ]
        
        return jsonify({
            "ok": True,
            "year": year,
            "month": month,
            "total_kwh": round(total_kwh, 2),
            "total_cost": round(total_cost, 2),
            "days_with_data": len(daily_stats),
            "daily_breakdown": daily_breakdown
        })
        
    except Exception as e:
        return jsonify({"ok": False, "msg": f"查詢失敗: {str(e)}"}), 500


@bp.route("/yearly/<int:year>", methods=["GET"])
def get_yearly_summary(year):
    """
    取得指定年份的用電統計
    
    URL: GET /usage/yearly/<year>
    
    回傳：
    - total_kwh: 該年總用電量
    - total_cost: 該年總電費
    - monthly_breakdown: 每月用電明細
    - months_with_data: 有資料的月份數
    """
    try:
        # 查詢該年的每月統計
        monthly_stats = db.session.query(
            extract('month', PowerLog.log_date).label('month'),
            func.sum(PowerLog.energy_consumed).label('kwh'),
            func.sum(PowerLog.cost).label('cost'),
            func.count(PowerLog.log_id).label('record_count')
        ).filter(
            extract('year', PowerLog.log_date) == year
        ).group_by(
            extract('month', PowerLog.log_date)
        ).order_by(
            extract('month', PowerLog.log_date)
        ).all()
        
        # 計算年總計
        total_kwh = sum(_to_float(row.kwh) for row in monthly_stats)
        total_cost = sum(_to_float(row.cost) for row in monthly_stats)
        
        # 建立每月明細
        monthly_breakdown = [
            {
                "month": int(row.month),
                "kwh": round(_to_float(row.kwh), 2),
                "cost": round(_to_float(row.cost), 2),
                "record_count": row.record_count
            }
            for row in monthly_stats
        ]
        
        return jsonify({
            "ok": True,
            "year": year,
            "total_kwh": round(total_kwh, 2),
            "total_cost": round(total_cost, 2),
            "months_with_data": len(monthly_stats),
            "monthly_breakdown": monthly_breakdown
        })
        
    except Exception as e:
        return jsonify({"ok": False, "msg": f"查詢失敗: {str(e)}"}), 500


@bp.route("/compare", methods=["GET"])
def compare_periods():
    """
    比較兩個時間段的用電統計
    
    URL: GET /usage/compare?period_type=<type>&date1=<date1>&date2=<date2>
    
    參數：
    - period_type: 比較類型 ('day', 'month', 'year')
    - date1: 第一個時間點 (YYYY-MM-DD 或 YYYY-MM 或 YYYY)
    - date2: 第二個時間點 (YYYY-MM-DD 或 YYYY-MM 或 YYYY)
    
    回傳：
    - period1: 第一個時間段的統計資料
    - period2: 第二個時間段的統計資料
    - comparison: 比較結果 (差異與百分比變化)
    """
    try:
        period_type = request.args.get("period_type", "month")
        date1_str = request.args.get("date1")
        date2_str = request.args.get("date2")
        
        if not date1_str or not date2_str:
            return jsonify({"ok": False, "msg": "請提供 date1 和 date2 參數"}), 400
        
        def get_period_stats(date_str, period_type):
            """取得指定時間段的統計"""
            if period_type == "day":
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                filters = [PowerLog.log_date == target_date]
                label = date_str
            elif period_type == "month":
                parts = date_str.split("-")
                year, month = int(parts[0]), int(parts[1])
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
                filters = [PowerLog.log_date >= start_date, PowerLog.log_date <= end_date]
                label = f"{year}-{month:02d}"
            elif period_type == "year":
                year = int(date_str)
                filters = [extract('year', PowerLog.log_date) == year]
                label = str(year)
            else:
                raise ValueError(f"不支援的 period_type: {period_type}")
            
            result = db.session.query(
                func.sum(PowerLog.energy_consumed).label('kwh'),
                func.sum(PowerLog.cost).label('cost'),
                func.count(PowerLog.log_id).label('record_count')
            ).filter(*filters).first()
            
            return {
                "label": label,
                "kwh": round(_to_float(result.kwh), 2) if result.kwh else 0,
                "cost": round(_to_float(result.cost), 2) if result.cost else 0,
                "record_count": result.record_count if result.record_count else 0
            }
        
        period1 = get_period_stats(date1_str, period_type)
        period2 = get_period_stats(date2_str, period_type)
        
        # 計算比較結果
        kwh_diff = period2["kwh"] - period1["kwh"]
        cost_diff = period2["cost"] - period1["cost"]
        
        kwh_pct_change = round((kwh_diff / period1["kwh"]) * 100, 2) if period1["kwh"] > 0 else None
        cost_pct_change = round((cost_diff / period1["cost"]) * 100, 2) if period1["cost"] > 0 else None
        
        comparison = {
            "kwh_difference": round(kwh_diff, 2),
            "cost_difference": round(cost_diff, 2),
            "kwh_percent_change": kwh_pct_change,
            "cost_percent_change": cost_pct_change
        }
        
        return jsonify({
            "ok": True,
            "period_type": period_type,
            "period1": period1,
            "period2": period2,
            "comparison": comparison
        })
        
    except ValueError as ve:
        return jsonify({"ok": False, "msg": str(ve)}), 400
    except Exception as e:
        return jsonify({"ok": False, "msg": f"比較失敗: {str(e)}"}), 500


@bp.route("/batch", methods=["POST"])
def add_usage_batch():
    """
    批次新增多筆用電記錄（使用資料庫交易）
    
    URL: POST /usage/batch
    
    Request Body (JSON):
    {
        "records": [
            {
                "device_id": 1,
                "kwh": 5.5,            // 直接提供度數
                "date": "2025-01-15"   // 可選，預設為今天
            },
            {
                "device_id": 2,
                "watts": 1000,         // 或提供瓦數和時數讓系統計算
                "hours": 3
            }
        ]
    }
    
    回傳：
    - success_count: 成功筆數
    - failure_count: 失敗筆數
    - results: 每筆記錄的處理結果
    """
    from models import Device
    
    try:
        data = request.get_json()
        if not data or "records" not in data:
            return jsonify({"ok": False, "msg": "請提供 records 陣列"}), 400
        
        records = data["records"]
        if not isinstance(records, list) or len(records) == 0:
            return jsonify({"ok": False, "msg": "records 必須是非空陣列"}), 400
        
        results = []
        success_count = 0
        failure_count = 0
        
        # 使用 savepoint 來處理交易
        try:
            for idx, record in enumerate(records):
                try:
                    device_id = record.get("device_id")
                    if not device_id:
                        raise ValueError("缺少 device_id")
                    
                    # 解析日期
                    if "date" in record:
                        try:
                            log_date = datetime.strptime(record["date"], "%Y-%m-%d").date()
                        except ValueError:
                            raise ValueError(f"日期格式錯誤，應為 YYYY-MM-DD")
                    else:
                        log_date = date.today()
                    
                    # 計算用電量
                    if "kwh" in record:
                        kwh = float(record["kwh"])
                        calculation_method = "direct"
                        power_watts = None
                        hours = None
                    elif "watts" in record and "hours" in record:
                        power_watts = float(record["watts"])
                        hours = float(record["hours"])
                        kwh = round(power_watts * hours / 1000, 2)
                        calculation_method = "calculated"
                    elif "watts" in record or "hours" in record:
                        # 只有一個參數，嘗試從設備取得額定功率
                        device = Device.query.get(device_id)
                        if not device:
                            raise ValueError(f"找不到設備 ID: {device_id}")
                        if not device.rated_power:
                            raise ValueError(f"設備 {device.name} 沒有設定額定功率")
                        
                        power_watts = float(record.get("watts", device.rated_power))
                        hours = float(record.get("hours", 1))
                        kwh = round(power_watts * hours / 1000, 2)
                        calculation_method = "calculated"
                    else:
                        raise ValueError("請提供 kwh 或 (watts + hours)")
                    
                    if kwh <= 0:
                        raise ValueError("用電量必須大於 0")
                    
                    # 計算電費 (使用累進費率)
                    base_month_kwh = get_monthly_total_kwh(log_date, include_target_date=False)
                    base_today_kwh_result = db.session.query(
                        func.sum(PowerLog.energy_consumed)
                    ).filter(
                        PowerLog.log_date == log_date
                    ).scalar()
                    base_today_kwh = _to_float(base_today_kwh_result) if base_today_kwh_result else 0
                    
                    current_cumulative_kwh = base_month_kwh + base_today_kwh
                    new_cumulative_kwh = current_cumulative_kwh + kwh
                    
                    bill_before = calculate_taiwan_bill(current_cumulative_kwh, log_date)
                    bill_after = calculate_taiwan_bill(new_cumulative_kwh, log_date)
                    
                    real_cost = round(bill_after - bill_before, 2)
                    avg_rate = round(real_cost / kwh, 2) if kwh > 0 else 0
                    
                    # 建立記錄
                    new_log = PowerLog(
                        device_id=device_id,
                        power_watts=power_watts,
                        hours=hours,
                        log_date=log_date,
                        energy_consumed=kwh,
                        cost=real_cost,
                        electricity_rate=avg_rate
                    )
                    db.session.add(new_log)
                    db.session.flush()  # 取得 log_id 但不 commit
                    
                    results.append({
                        "index": idx,
                        "success": True,
                        "log_id": new_log.log_id,
                        "device_id": device_id,
                        "kwh": kwh,
                        "cost": real_cost,
                        "date": log_date.strftime("%Y-%m-%d")
                    })
                    success_count += 1
                    
                except Exception as record_error:
                    results.append({
                        "index": idx,
                        "success": False,
                        "error": str(record_error)
                    })
                    failure_count += 1
            
            # 如果有任何失敗，回滾所有變更
            if failure_count > 0:
                db.session.rollback()
                return jsonify({
                    "ok": False,
                    "msg": f"批次處理失敗，已回滾所有變更。成功: {success_count}, 失敗: {failure_count}",
                    "success_count": 0,
                    "failure_count": len(records),
                    "results": results
                }), 400
            
            # 全部成功才 commit
            db.session.commit()
            
            return jsonify({
                "ok": True,
                "msg": f"批次處理完成",
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "ok": False,
                "msg": f"批次處理發生錯誤: {str(e)}",
                "success_count": 0,
                "failure_count": len(records)
            }), 500
            
    except Exception as e:
        return jsonify({"ok": False, "msg": f"請求格式錯誤: {str(e)}"}), 400
