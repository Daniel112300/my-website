-- device_status 資料匯出
-- 匯出時間: 2025-11-30

DELETE FROM device_status;

INSERT INTO device_status (status_id, device_id, is_on, current_temp, target_temp, fan_speed, mode, last_updated) VALUES
(1, 1, 1, 26.50, 25.00, 'medium', 'cool', '2025-11-14 04:19:32'),
(2, 2, 0, 28.10, 26.00, 'auto', 'cool', '2025-11-14 04:19:32');
