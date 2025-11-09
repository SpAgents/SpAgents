-- 修复密码哈希格式问题
USE axspa;

-- 删除现有的用户
DELETE FROM users WHERE username IN ('admin', 'wenqianyue01');

-- 创建新的测试用户，使用简单的密码
INSERT INTO users (username, password_hash, is_admin) VALUES 
('admin', 'sha256$260000$admin$admin', TRUE),
('test', 'sha256$260000$test$test', TRUE);

-- 查看结果
SELECT id, username, is_admin FROM users; 