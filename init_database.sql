-- axSpA诊断系统数据库初始化脚本
-- 数据库服务器：39.103.223.165:23306

-- 创建数据库
CREATE DATABASE IF NOT EXISTS axspa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE axspa;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建诊断记录表
CREATE TABLE IF NOT EXISTS diagnosis_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    file_id VARCHAR(100),
    diagnosis_result INT, -- 1: 可以诊断, 0: 未诊断, -1: 无法确定
    diagnosis_reason TEXT,
    treatment_suggestion TEXT,
    medical_info JSON,
    processing_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建管理员用户
INSERT INTO users (username, password_hash, is_admin) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK2', TRUE),
('wenqianyue01', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK2', TRUE);

-- 创建索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_diagnosis_records_user_id ON diagnosis_records(user_id);
CREATE INDEX idx_diagnosis_records_created_at ON diagnosis_records(created_at);

-- 显示创建的表
SHOW TABLES; 