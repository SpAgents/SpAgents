# axSpA智能诊断系统 - Docker镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=evaluation/evaluation_online.py

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    nginx \
    default-mysql-client \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖 - 分步安装，torch使用官方源
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    pip install --no-cache-dir torch==2.0.1+cpu torchvision==0.15.2+cpu -f https://download.pytorch.org/whl/torch_stable.html && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p evaluation/uploads evaluation/log evaluation/static

# 设置权限
RUN chmod -R 755 /app

# 创建启动脚本
RUN echo '#!/bin/bash\n\
echo "🚀 启动 axSpA 智能诊断系统..."\n\
echo "📱 Web界面地址: http://localhost:5500"\n\
cd /app/evaluation\n\
python evaluation_online.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# 暴露端口
EXPOSE 5500

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5500/ || exit 1

# 启动命令
CMD ["/app/start.sh"] 