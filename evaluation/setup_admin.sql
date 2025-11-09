-- 添加is_admin字段到现有表（如果不存在）
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- 将wenqianyue01设置为管理员
UPDATE users SET is_admin = TRUE WHERE username = 'wenqianyue01';

-- 查看结果
SELECT id, username, is_admin FROM users; 