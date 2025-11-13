-- ============================================
-- 智慧家電控制系統資料庫
-- 建立日期: 2025-11-14
-- 功能: 管理家電設備、狀態監控、電費記錄
-- ============================================

DROP DATABASE IF EXISTS `smart_home_db`;
CREATE DATABASE `smart_home_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `smart_home_db`;

-- ============================================
-- 資料表 1: users (使用者資料表)
-- 用途: 儲存系統使用者資訊
-- ============================================
CREATE TABLE `users` (
  `user_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '使用者ID',
  `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '使用者名稱',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密碼雜湊值',
  `email` VARCHAR(100) UNIQUE COMMENT '電子郵件',
  `role` ENUM('admin', 'user') DEFAULT 'user' COMMENT '使用者角色',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='使用者資料表';

-- ============================================
-- 資料表 2: devices (設備資料表)
-- 用途: 儲存所有智慧家電設備資訊
-- ============================================
CREATE TABLE `devices` (
  `device_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '設備ID',
  `user_id` INT NOT NULL COMMENT '擁有者ID',
  `device_name` VARCHAR(100) NOT NULL COMMENT '設備名稱',
  `device_type` ENUM('air_conditioner', 'light') NOT NULL COMMENT '設備類型',
  `model_number` VARCHAR(50) COMMENT '型號',
  `location` VARCHAR(100) COMMENT '安裝位置',
  `rated_power` DECIMAL(6,2) COMMENT '額定功率(kW)',
  `is_active` BOOLEAN DEFAULT TRUE COMMENT '設備是否啟用',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
  FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE,
  INDEX idx_user_device (`user_id`, `device_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='設備資料表';

-- ============================================
-- 資料表 3: device_status (設備即時狀態表)
-- 用途: 記錄設備當前狀態(溫度、開關等)
-- ============================================
CREATE TABLE `device_status` (
  `status_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '狀態ID',
  `device_id` INT NOT NULL COMMENT '設備ID',
  `is_on` BOOLEAN DEFAULT FALSE COMMENT '開關狀態',
  `current_temperature` DECIMAL(4,2) COMMENT '當前室內溫度(°C)',
  `target_temperature` DECIMAL(4,2) COMMENT '目標溫度(°C)',
  `mode` ENUM('cool', 'heat', 'dry', 'auto') COMMENT '運轉模式',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '狀態更新時間',
  FOREIGN KEY (`device_id`) REFERENCES `devices`(`device_id`) ON DELETE CASCADE,
  UNIQUE KEY uk_device_status (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='設備即時狀態表';

-- ============================================
-- 資料表 4: power_logs (電力使用記錄表)
-- 用途: 記錄每日用電量及電費
-- ============================================
CREATE TABLE `power_logs` (
  `log_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '記錄ID',
  `device_id` INT NOT NULL COMMENT '設備ID',
  `log_date` DATE NOT NULL COMMENT '記錄日期',
  `energy_consumed` DECIMAL(8,4) COMMENT '用電量(kWh)',
  `cost` DECIMAL(8,2) COMMENT '電費(元)',
  `electricity_rate` DECIMAL(6,4) DEFAULT 3.20 COMMENT '電價(元/kWh)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  FOREIGN KEY (`device_id`) REFERENCES `devices`(`device_id`) ON DELETE CASCADE,
  UNIQUE KEY uk_device_date (`device_id`, `log_date`),
  INDEX idx_log_date (`log_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='電力使用記錄表';

-- ============================================
-- 插入測試資料
-- ============================================

-- 1. 插入使用者資料
INSERT INTO `users` (`username`, `password_hash`, `email`, `role`) VALUES
('xiaoming', '$2y$10$abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJK', 'xiaoming@example.com', 'user'),
('admin_user', '$2y$10$zyxwvutsrqponmlkjihgfedcba0987654321ZYXWVUTSRQP', 'admin@example.com', 'admin');

-- 2. 插入設備資料
INSERT INTO `devices` (`user_id`, `device_name`, `device_type`, `model_number`, `location`, `rated_power`, `is_active`) VALUES
(1, '客廳冷氣', 'air_conditioner', 'AC001-LIVING', '客廳', 3.50, TRUE),
(1, '臥室冷氣', 'air_conditioner', 'AC002-BEDROOM', '主臥室', 2.80, TRUE),
(1, '餐廳主燈', 'light', 'LIGHT004-DINING', '餐廳', 0.02, TRUE);

-- 3. 插入設備即時狀態
INSERT INTO `device_status` (`device_id`, `is_on`, `current_temperature`, `target_temperature`, `mode`) VALUES
(1, TRUE, 26.50, 25.00, 'cool'),
(2, FALSE, 28.10, 26.00, 'cool');

-- 4. 插入電力使用記錄 (最近3天)
INSERT INTO `power_logs` (`device_id`, `log_date`, `energy_consumed`, `cost`, `electricity_rate`) VALUES
-- 2025-11-12 的記錄
(1, '2025-11-12', 10.2000, 32.64, 3.20),
(2, '2025-11-12', 6.5000, 20.80, 3.20),
-- 2025-11-13 的記錄
(1, '2025-11-13', 12.5000, 40.00, 3.20),
(2, '2025-11-13', 7.8000, 24.96, 3.20),
-- 2025-11-14 的記錄 (今日)
(1, '2025-11-14', 5.1000, 16.32, 3.20),
(2, '2025-11-14', 1.5000, 4.80, 3.20);

-- ============================================
-- 實用查詢範例
-- ============================================

-- 查詢 1: 查看所有冷氣的即時狀態
-- SELECT 
--     d.device_name AS '設備名稱',
--     d.location AS '位置',
--     ds.is_on AS '開關狀態',
--     ds.current_temperature AS '室內溫度(°C)',
--     ds.target_temperature AS '目標溫度(°C)',
--     ds.mode AS '模式'
-- FROM devices d
-- JOIN device_status ds ON d.device_id = ds.device_id
-- WHERE d.device_type = 'air_conditioner';

-- 查詢 2: 計算今日總電費
-- SELECT 
--     SUM(cost) AS '今日總電費(元)',
--     SUM(energy_consumed) AS '今日總用電量(kWh)'
-- FROM power_logs
-- WHERE log_date = CURDATE();

-- 查詢 3: 查看各設備今日用電排行
-- SELECT 
--     d.device_name AS '設備名稱',
--     pl.energy_consumed AS '用電量(kWh)',
--     pl.cost AS '電費(元)'
-- FROM power_logs pl
-- JOIN devices d ON pl.device_id = d.device_id
-- WHERE pl.log_date = CURDATE()
-- ORDER BY pl.cost DESC;

-- 查詢 4: 查看最近7天的電費趨勢
-- SELECT 
--     log_date AS '日期',
--     SUM(cost) AS '總電費(元)',
--     SUM(energy_consumed) AS '總用電量(kWh)'
-- FROM power_logs
-- WHERE log_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
-- GROUP BY log_date
-- ORDER BY log_date DESC;

-- ============================================
-- 資料庫建立完成
-- ============================================
