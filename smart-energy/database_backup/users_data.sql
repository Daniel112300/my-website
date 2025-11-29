-- users 資料匯出
-- 匯出時間: 2025-11-30

DELETE FROM users;

INSERT INTO users (user_id, username, password_hash, email, role, created_at) VALUES
(1, 'xiaoming', '$2y$10$abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJK', 'xiaoming@example.com', 'user', '2025-11-14 04:19:32'),
(2, 'admin_user', '$2y$10$zyxwvutsrqponmlkjihgfedcba0987654321ZYXWVUTSRQP', 'admin@example.com', 'admin', '2025-11-14 04:19:32'),
(3, 'test_user', '$2y$10$testpasswordhash123456789', 'test@example.com', 'user', '2025-11-29 23:59:00'),
(4, 'power_test_user', '$2y$10$testpowerhash', 'powertest@example.com', 'user', '2025-11-30 01:11:54');
