# axSpA智能诊断系统 - 部署操作总结报告

## 📋 项目概述

### 项目名称
axSpA（中轴型脊柱关节炎）智能诊断系统

### 项目性质
这是一个**复杂的医疗AI多智能体诊断系统**，不是简单的Web应用

### 技术架构
- **多智能体系统**：PlannerAgent、DataAgent、ToolAgent、DoctorAgent
- **大语言模型集成**：DeepSeek、Qwen等LLM
- **深度学习模型**：EdemaSystem医学影像分析
- **Web服务**：Flask框架 + 用户认证系统

## 🎯 部署目标

### 目标服务器
- **IP地址**：39.103.223.83
- **内网IP**：172.16.0.213
- **操作系统**：CentOS 7.9
- **登录账号**：root
- **登录密码**：ascare@996

### 数据库服务器
- **IP地址**：39.103.223.165
- **端口**：23306
- **数据库**：MySQL
- **用户名**：root
- **密码**：J!ZazKTCeH5@

## 🚀 部署操作记录

### 第一阶段：项目分析和准备

#### 1.1 项目结构分析
```
axSpA系统架构：
├── agent/           # 智能体模块
│   ├── planner_agent.py
│   ├── data_agent.py
│   ├── tool_agent.py
│   └── doctor_agent.py
├── evaluation/      # Web服务主程序
│   ├── evaluation_online.py  # 主服务文件
│   ├── static/      # 静态文件
│   └── uploads/     # 文件上传目录
├── module/          # 深度学习模块
│   ├── edema_system.py
│   └── deepseek_llm.py
├── config/          # 配置文件
└── utils/           # 工具函数
```

#### 1.2 技术依赖分析
**Python版本要求**：
- 项目需要：Python 3.8+
- 服务器当前：Python 3.6.8
- **关键依赖包**：
  - Flask==2.3.3（需要Python 3.8+）
  - numpy==1.24.3（需要Python 3.8+）
  - pandas==2.0.3（需要Python 3.8+）
  - PyMySQL==1.1.0
  - pydicom==2.4.3
  - SimpleITK==2.2.1

### 第二阶段：传统部署尝试

#### 2.1 初始部署尝试
```bash
# 登录服务器
ssh root@39.103.223.83

# 创建项目目录
mkdir -p /var/www/axspa

# 复制项目文件
cp -r /tmp/deploy_package_*/* /var/www/axspa/

# 创建Python虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖（失败）
pip install -r requirements.txt
```

#### 2.2 遇到的问题
1. **Python版本兼容性**：
   ```
   ERROR: Could not find a version that satisfies the requirement Flask==2.3.3
   ERROR: No matching distribution found for Flask==2.3.3
   ```

2. **依赖包版本冲突**：
   ```
   ERROR: Could not find a version that satisfies the requirement pandas==2.0.3
   ```

#### 2.3 解决方案尝试
尝试使用兼容Python 3.6的版本：
```bash
# 创建兼容版本requirements
cat > requirements_fixed.txt << 'EOF'
Flask==2.0.3
Flask-CORS==3.0.10
PyMySQL==1.0.2
Werkzeug==2.0.3
numpy==1.19.5
pandas==1.1.5
Pillow==8.4.0
pydicom==2.3.1
requests==2.28.2
EOF
```

### 第三阶段：Docker化部署方案

#### 3.1 Docker配置文件创建

**Dockerfile**：
```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    nginx \
    mysql-client \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .
RUN mkdir -p evaluation/uploads evaluation/log evaluation/static

EXPOSE 5500
CMD ["python", "evaluation/evaluation_online.py"]
```

**docker-compose.yml**：
```yaml
version: '3.8'
services:
  axspa-app:
    build: .
    ports:
      - "5500:5500"
    environment:
      - MYSQL_HOST=axspa-db
      - MYSQL_PORT=3306
      - MYSQL_USER=root
      - MYSQL_PASSWORD=axspa@2024
      - MYSQL_DB=axspa
    volumes:
      - ./evaluation/uploads:/app/evaluation/uploads
      - ./evaluation/log:/app/evaluation/log
    depends_on:
      - axspa-db

  axspa-db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=axspa@2024
      - MYSQL_DATABASE=axspa
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init_database.sql:/docker-entrypoint-initdb.d/init_database.sql

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - axspa-app

volumes:
  mysql_data:
```

#### 3.2 部署脚本创建
创建了多个版本的部署脚本：
- `deploy_to_aliyun.sh` - 初始部署脚本
- `server-docker-deploy.sh` - Docker部署脚本
- `deploy_on_server_fixed.sh` - 修复版部署脚本

### 第四阶段：服务器环境问题

#### 4.1 网络连接问题
```bash
# 错误信息
curl: (35) TCP connection reset by peer
```

**问题原因**：服务器无法连接到Docker官方安装脚本

#### 4.2 yum源配置问题
```bash
# 错误信息
Could not retrieve mirrorlist http://mirrorlist.centos.org?arch=x86_64&release=7&repo=sclo-rh 
error was 14: curl#6 - "Could not resolve host: mirrorlist.centos.org; Unknown error"
```

**问题原因**：CentOS官方镜像源无法访问

#### 4.3 解决方案实施
```bash
# 修复yum源
curl -o /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-7.repo
yum clean all
yum makecache

# 安装Docker
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io
systemctl start docker
systemctl enable docker
```

## 🔧 技术问题总结

### 1. 环境兼容性问题
- **根本原因**：服务器Python 3.6.8版本过旧
- **影响范围**：无法安装现代AI库和Web框架
- **解决方案**：Docker化部署，使用Python 3.11官方镜像

### 2. 网络连接问题
- **问题**：服务器网络配置限制对外连接
- **影响**：无法下载Docker安装脚本和依赖包
- **解决方案**：使用yum方式安装，配置阿里云镜像源

### 3. 系统权限问题
- **问题**：某些目录需要root权限
- **解决方案**：使用sudo权限执行部署脚本

## 📊 部署进度状态

### ✅ 已完成
- [x] 项目结构分析
- [x] 技术依赖分析
- [x] Docker配置文件创建
- [x] 部署脚本编写
- [x] 文件上传到服务器
- [x] yum源修复
- [x] Docker安装

### ⚠️ 进行中
- [ ] Docker镜像构建
- [ ] 服务启动
- [ ] 健康检查
- [ ] 系统测试

### ❌ 未完成
- [ ] 数据库初始化
- [ ] Nginx配置
- [ ] 防火墙配置
- [ ] SSL证书配置

## 🎯 关键发现和建议

### 1. 项目复杂度评估
这是一个**极其复杂的医疗AI系统**，包含：
- 多智能体协同工作
- 大语言模型集成
- 深度学习医学影像分析
- 实时诊断反馈系统

### 2. 环境要求
**最低要求**：
- Python 3.8+（推荐Python 3.11）
- 16GB+ 内存（用于AI模型推理）
- 稳定的网络连接（用于LLM API调用）
- 专业的运维支持

### 3. 部署策略建议
**推荐方案**：Docker化部署
- 环境完全隔离
- 版本固定，避免冲突
- 易于维护和更新
- 标准化部署流程

## 🚨 当前问题

### 服务器502错误
- **现象**：服务器无法登录
- **可能原因**：
  1. 部署过程中修改了系统配置
  2. 服务冲突导致系统不稳定
  3. 网络配置问题
  4. 资源占用过高

### 需要工程师协助
1. **检查服务器状态**：确认服务器是否正常运行
2. **查看系统日志**：分析502错误的具体原因
3. **恢复系统**：如果系统出现问题，需要恢复
4. **环境升级**：建议升级Python到3.11版本
5. **网络配置**：检查网络连接和防火墙设置

## 📞 联系信息

### 项目负责人
- **项目**：axSpA智能诊断系统
- **性质**：医疗AI多智能体系统
- **重要性**：涉及患者诊断，需要高稳定性

### 技术规格
- **Python版本**：需要3.8+（推荐3.11）
- **内存要求**：16GB+
- **存储要求**：50GB+
- **网络要求**：稳定的外网连接

## 📋 下一步行动计划

### 立即行动
1. **联系工程师**：报告服务器502错误
2. **提供技术文档**：本总结报告
3. **说明项目重要性**：医疗AI系统，需要专业环境

### 长期计划
1. **环境升级**：升级Python到3.11
2. **Docker化部署**：完成容器化部署
3. **监控配置**：设置系统监控和告警
4. **备份策略**：建立数据备份机制

---

**报告生成时间**：2025年7月31日  
**报告状态**：紧急 - 需要工程师立即协助  
**项目优先级**：高 - 医疗AI诊断系统 