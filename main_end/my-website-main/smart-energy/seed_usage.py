from app import create_app
from models import db, Device, PowerLog
from feature_simulator import simulate_device_usage, save_simulated_data, simulate_outdoor_temperature
from datetime import date, timedelta
import random

app = create_app()

def generate_usage_data():
    with app.app_context():
        print("🚀 開始生成用電數據...")
        
        # 1. 設定日期範圍：從 11/1 生成到 12/31
        start_date = date(2025, 11, 1)
        end_date = date(2025, 12, 31)
        
        # 2. 取得所有設備
        devices = Device.query.filter_by(is_active=True).all()
        if not devices:
            print("❌ 找不到設備，請先執行 python init_data.py")
            return

        total_records = 0
        current_date = start_date
        
        # 3. 逐日生成
        while current_date <= end_date:
            # 模擬當天氣溫
            outdoor_temp = simulate_outdoor_temperature(current_date)
            
            for device in devices:
                # 呼叫模擬器邏輯計算當日用電
                usage = simulate_device_usage(device, current_date, outdoor_temp)
                
                if usage:
                    # 寫入資料庫
                    save_simulated_data(
                        usage["device_id"],
                        current_date,
                        usage["power_watts"],
                        usage["hours"],
                        usage["kwh"]
                    )
                    total_records += 1
            
            # 顯示進度
            if current_date.day == 1 or current_date.day == 15:
                print(f"   -> 已生成 {current_date} 的數據...")
                
            current_date += timedelta(days=1)

        print(f"\n✅ 數據生成完成！總共新增了 {total_records} 筆用電紀錄。")
        print("📅 範圍：2025-11-01 ~ 2025-12-31")

if __name__ == "__main__":
    generate_usage_data()