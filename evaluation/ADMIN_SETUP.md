# 管理员设置操作指南

## 🎯 目标
将用户 `wenqianyue01` 设置为管理员，并暂时禁止其他账号注册和登录。

## 📋 操作步骤

### 1. 更新数据库表结构
在MySQL中执行以下命令：

```sql
-- 连接到数据库
mysql -u root -p
USE axspa;

-- 添加管理员字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- 将wenqianyue01设置为管理员
UPDATE users SET is_admin = TRUE WHERE username = 'wenqianyue01';

-- 查看结果
SELECT id, username, is_admin FROM users;
```

### 2. 运行系统
```bash
cd /Users/wenchienyueh/Desktop/code_0411/evaluation
python evaluation_online.py
```

### 3. 访问系统
- 打开浏览器访问: `http://localhost:5500`
- 使用 `wenqianyue01` 账号登录
- 其他用户将无法登录，会显示"系统维护中"提示

## 🔧 功能说明

### 维护模式配置
在 `evaluation_online.py` 中：
```python
MAINTENANCE_MODE = True  # 设置为True时，只允许管理员登录
ADMIN_USERNAME = 'wenqianyue01'  # 管理员用户名
```

### 访问控制
- **登录限制**: 只有 `wenqianyue01` 可以登录
- **注册禁止**: 所有新用户注册被禁止
- **管理员面板**: 访问 `/admin` 查看所有用户

### 恢复正常模式
将 `MAINTENANCE_MODE = False` 即可恢复正常访问。

## 🎨 界面变化
- 登录页面显示维护提示
- 主页面右下角有"管理员面板"按钮
- 管理员可以查看所有用户列表

## 🔒 安全特性
- 密码仍然加密存储
- 管理员权限存储在数据库中
- 会话管理包含管理员状态 