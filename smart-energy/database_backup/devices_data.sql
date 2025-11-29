-- devices 資料匯出
-- 匯出時間: 2025-11-30

DELETE FROM devices;

INSERT INTO devices (device_id, user_id, device_name, device_type, model_number, location, rated_power, is_active) VALUES
(1, 1, '客廳冷氣', 'air_conditioner', 'AC001-LIVING', '客廳', 3.50, 1),
(2, 1, '臥室冷氣', 'air_conditioner', 'AC002-BEDROOM', '主臥室', 2.80, 1),
(3, 1, '餐廳主燈', 'light', 'LIGHT004-DINING', '餐廳', 0.02, 1),
(4, 3, '測試冷氣', 'air_conditioner', 'TEST-AC-001', '測試房間', 3.50, 1),
(5, 4, '客廳LED燈', 'light', 'LED-001', '客廳', 0.02, 1),
(6, 4, '臥室冷氣', 'air_conditioner', 'AC-003', '臥室', 2.50, 1),
(7, 4, '書房檯燈', 'light', 'LAMP-001', '書房', 0.03, 1);
