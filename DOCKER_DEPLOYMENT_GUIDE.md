# axSpA智能诊断系统 - Docker部署指南

## 🎯 部署目标
- **服务器**: 39.103.223.83
- **系统**: CentOS 7.9
- **架构**: Docker容器化部署
- **域名**: spa.asdoctor.net

## 🐳 Docker化优势

### 1. **环境完全隔离**
- 使用Python 3.11官方镜像
- 所有依赖包版本固定
- 避免系统环境冲突

### 2. **简化部署流程**
- 一键部署整个系统
- 自动安装所有依赖
- 标准化部署流程

### 3. **易于维护**
- 容器化隔离
- 快速更新和回滚
- 标准化运维

## 📦 项目架构

```
axSpA系统 (Docker Compose)
├── axspa-app (Flask应用)
├── axspa-db (MySQL数据库)
└── nginx (反向代理)
```

## 🚀 部署步骤

### 第一步：本地准备

```bash
# 1. 确保在项目根目录
cd /Users/wenchienyueh/Desktop/code_0411

# 2. 给部署脚本执行权限
chmod +x docker-deploy.sh

# 3. 执行Docker部署脚本
./docker-deploy.sh
```

### 第二步：上传到服务器

```bash
# 在新的终端窗口中执行
scp -r ./docker_deploy_* root@39.103.223.83:/tmp/
# 输入密码: ascare@996
```

### 第三步：服务器部署

```bash
# 1. 登录服务器
ssh root@39.103.223.83
# 输入密码: ascare@996

# 2. 进入部署目录
cd /tmp/docker_deploy_*

# 3. 执行部署脚本
bash deploy_on_server.sh
```

## 🔧 服务管理

### 查看服务状态
```bash
cd /opt/axspa
docker-compose ps
```

### 查看服务日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f axspa-app
docker-compose logs -f axspa-db
docker-compose logs -f nginx
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart axspa-app
```

### 停止服务
```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 更新服务
```bash
# 拉取最新镜像
docker-compose pull

# 重新构建并启动
docker-compose up -d --build
```

## 🌐 访问地址

### 生产环境
- **主域名**: http://spa.asdoctor.net
- **IP访问**: http://39.103.223.83
- **直接端口**: http://39.103.223.83:5500

### 管理员账号
- **用户名**: admin
- **密码**: yhnmkl

## 🔍 故障排查

### 1. 服务无法启动
```bash
# 检查Docker状态
systemctl status docker

# 检查容器状态
docker ps -a

# 查看详细错误日志
docker-compose logs axspa-app
```

### 2. 数据库连接失败
```bash
# 检查数据库容器
docker exec -it axspa-db mysql -u root -p

# 检查网络连接
docker network ls
docker network inspect axspa_axspa-network
```

### 3. Nginx代理失败
```bash
# 检查Nginx配置
docker exec -it axspa-nginx nginx -t

# 检查Nginx日志
docker-compose logs nginx
```

### 4. 端口冲突
```bash
# 检查端口占用
netstat -tlnp | grep :80
netstat -tlnp | grep :5500
netstat -tlnp | grep :3306
```

## 📊 监控和维护

### 系统资源监控
```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

### 数据备份
```bash
# 备份数据库
docker exec axspa-db mysqldump -u root -p axspa > backup_$(date +%Y%m%d).sql

# 备份上传文件
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz evaluation/uploads/
```

### 日志管理
```bash
# 查看应用日志
tail -f evaluation/log/*.log

# 清理旧日志
find evaluation/log/ -name "*.log" -mtime +7 -delete
```

## 🔒 安全配置

### 1. 防火墙设置
```bash
# 开放必要端口
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
```

### 2. SSL证书配置
```bash
# 在nginx.conf中启用HTTPS
# 配置SSL证书路径
# 重启Nginx服务
```

### 3. 数据库安全
```bash
# 修改默认密码
# 限制数据库访问IP
# 定期备份数据
```

## 🎉 部署完成

部署成功后，你可以：
1. 通过Web界面访问系统
2. 上传MRI影像进行诊断
3. 查看诊断结果和报告
4. 管理用户和权限

## 📞 技术支持

如果遇到问题：
1. 检查Docker服务状态
2. 查看容器日志
3. 验证网络连接
4. 确认配置文件正确

Docker化部署大大简化了环境配置和部署流程，提高了系统的稳定性和可维护性！ 