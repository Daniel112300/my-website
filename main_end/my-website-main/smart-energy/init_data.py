from app import create_app
from models import db, User, Device, DeviceStatus
from datetime import datetime

# 建立 Flask App Context
app = create_app()

def seed_data():
    with app.app_context():
        print("🔄 正在連線資料庫...")
        
        # 1. 為了避免重複，我們先清空舊資料 (開發階段適用)
        # 注意：這會刪除所有現有資料！
        db.drop_all()
        db.create_all()
        print("✅ 資料表重置完成 (Tables Re-created)")

        # 2. 建立測試使用者
        user1 = User(
            username='xiaoming',
            email='xiaoming@example.com',
            role='user'
        )
        user1.set_password('123456') # 設定密碼

        admin = User(
            username='admin_user',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')

        db.session.add_all([user1, admin])
        db.session.commit()
        print("✅ 使用者建立完成")

        # 3. 建立測試設備 (記得要關聯 user_id)
        # User 1 (xiaoming) 的設備
        ac_living = Device(
            user_id=user1.user_id,
            device_name='客廳冷氣',
            device_type='air_conditioner',
            model_number='AC-2025-L',
            location='客廳',
            rated_power=3.5, # kW
            is_active=True
        )

        ac_bedroom = Device(
            user_id=user1.user_id,
            device_name='臥室冷氣',
            device_type='air_conditioner',
            model_number='AC-2025-B',
            location='主臥室',
            rated_power=2.8,
            is_active=True
        )

        light_living = Device(
            user_id=user1.user_id,
            device_name='客廳主燈',
            device_type='light',
            model_number='LED-100W',
            location='客廳',
            rated_power=0.1,
            is_active=True
        )

        db.session.add_all([ac_living, ac_bedroom, light_living])
        db.session.commit()
        print("✅ 設備建立完成")

        # 4. 建立設備初始狀態
        # 客廳冷氣：開啟，26度
        status1 = DeviceStatus(
            device_id=ac_living.device_id,
            is_on=True,
            current_temperature=28.5,
            target_temperature=26.0,
            mode='cool'
        )

        # 臥室冷氣：關閉
        status2 = DeviceStatus(
            device_id=ac_bedroom.device_id,
            is_on=False,
            current_temperature=27.0,
            target_temperature=26.0,
            mode='cool'
        )
        
        # 客廳燈：關閉 (如果沒有狀態紀錄，前端預設會顯示關閉，但為了完整性我們建一筆)
        status3 = DeviceStatus(
            device_id=light_living.device_id,
            is_on=False
        )

        db.session.add_all([status1, status2, status3])
        db.session.commit()
        print("✅ 設備狀態建立完成")
        
        print("\n🎉 初始化成功！現在你可以重新整理網頁了。")

if __name__ == "__main__":
    seed_data()