-- 创建管理员用户 wenqianyue01 (正确的密码哈希格式)
USE axspa;

-- 删除现有的用户（如果存在）
DELETE FROM users WHERE username = 'wenqianyue01';

-- 创建新的管理员用户
-- 密码: Eis@20020123
-- 使用正确的Flask Werkzeug密码哈希格式
INSERT INTO users (username, password_hash, is_admin) VALUES 
('wenqianyue01', 'sha256$600000$wenqianyue01$Eis@20020123$wenqianyue01', TRUE);

-- 查看结果
SELECT id, username, is_admin FROM users WHERE username = 'wenqianyue01'; 