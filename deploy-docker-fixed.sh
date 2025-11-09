#!/bin/bash

# axSpA智能诊断系统 - 修复版Docker部署脚本
# 目标服务器：39.103.223.83

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务器配置
SERVER_IP="39.103.223.83"
SERVER_USER="root"
SERVER_PASSWORD="ascare@996"

echo -e "${BLUE}🚀 axSpA智能诊断系统 - 修复版Docker部署脚本${NC}"
echo "=============================================="
echo -e "${YELLOW}目标服务器: ${SERVER_IP}${NC}"
echo ""

# 检查本地项目
LOCAL_PROJECT_PATH="/Users/wenchienyueh/Desktop/code_0411"
if [ ! -d "$LOCAL_PROJECT_PATH" ]; then
    echo -e "${RED}❌ 本地项目路径不存在: $LOCAL_PROJECT_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 本地项目检查通过${NC}"

# 创建部署包
echo -e "${YELLOW}📦 创建部署包...${NC}"
DEPLOY_DIR="./docker_deploy_fixed_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_DIR"

# 复制项目文件
echo "复制项目文件..."
cp -r "$LOCAL_PROJECT_PATH/evaluation" "$DEPLOY_DIR/"
cp -r "$LOCAL_PROJECT_PATH/agent" "$DEPLOY_DIR/"
cp -r "$LOCAL_PROJECT_PATH/module" "$DEPLOY_DIR/"
cp -r "$LOCAL_PROJECT_PATH/config" "$DEPLOY_DIR/"
cp -r "$LOCAL_PROJECT_PATH/utils" "$DEPLOY_DIR/"

# 复制Docker配置文件
cp "$LOCAL_PROJECT_PATH/Dockerfile" "$DEPLOY_DIR/"
cp "$LOCAL_PROJECT_PATH/docker-compose.yml" "$DEPLOY_DIR/"
cp "$LOCAL_PROJECT_PATH/nginx.conf" "$DEPLOY_DIR/"
cp "$LOCAL_PROJECT_PATH/init_database.sql" "$DEPLOY_DIR/"
cp "$LOCAL_PROJECT_PATH/requirements.txt" "$DEPLOY_DIR/"

# 复制Docker安装脚本
cp "$LOCAL_PROJECT_PATH/install-docker-centos.sh" "$DEPLOY_DIR/"

# 创建修复版服务器端部署脚本
echo "创建修复版服务器端部署脚本..."
cat > "$DEPLOY_DIR/deploy_on_server_fixed.sh" << 'EOF'
#!/bin/bash

# 修复版服务器端Docker部署脚本
set -e

echo "🚀 开始修复版Docker部署axSpA诊断系统..."

# 1. 检查Docker环境
echo "📦 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo "Docker未安装，使用yum方式安装..."
    bash install-docker-centos.sh
else
    echo "Docker已安装，版本: $(docker --version)"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose未安装，正在安装..."
    # 尝试使用yum安装
    yum install -y docker-compose-plugin || {
        echo "yum安装失败，尝试手动安装..."
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    }
fi

# 2. 创建项目目录
echo "📁 创建项目目录..."
mkdir -p /opt/axspa
cd /opt/axspa

# 3. 复制项目文件
echo "📁 复制项目文件..."
cp -r /tmp/docker_deploy_fixed_*/* .

# 4. 创建数据目录
echo "📁 创建数据目录..."
mkdir -p evaluation/uploads evaluation/log evaluation/static

# 5. 设置权限
echo "🔐 设置权限..."
chmod -R 755 /opt/axspa
chown -R root:root /opt/axspa

# 6. 构建Docker镜像
echo "📦 构建Docker镜像..."
docker build -t axspa-system .

# 7. 启动服务
echo "🚀 启动Docker服务..."
docker-compose up -d

# 8. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 45

# 9. 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 10. 检查健康状态
echo "🏥 检查健康状态..."
for i in {1..5}; do
    if curl -f http://localhost/health 2>/dev/null; then
        echo "✅ 健康检查通过！"
        break
    else
        echo "⏳ 等待服务启动... ($i/5)"
        sleep 10
    fi
done

echo "✅ Docker部署完成！"
echo ""
echo "📱 访问地址:"
echo "   - HTTP: http://39.103.223.83"
echo "   - 直接访问: http://39.103.223.83:5500"
echo ""
echo "🔧 管理命令:"
echo "   - 查看状态: docker-compose ps"
echo "   - 查看日志: docker-compose logs -f"
echo "   - 停止服务: docker-compose down"
echo "   - 重启服务: docker-compose restart"
EOF

chmod +x "$DEPLOY_DIR/deploy_on_server_fixed.sh"

echo -e "${GREEN}✅ 修复版部署包创建完成: $DEPLOY_DIR${NC}"

# 上传到服务器
echo -e "${YELLOW}📤 上传文件到服务器...${NC}"
echo "请在新的终端窗口中执行以下命令："
echo ""
echo -e "${BLUE}scp -r $DEPLOY_DIR $SERVER_USER@$SERVER_IP:/tmp/${NC}"
echo ""
echo -e "${BLUE}ssh $SERVER_USER@$SERVER_IP${NC}"
echo ""
echo -e "${BLUE}cd /tmp/$(basename $DEPLOY_DIR)${NC}"
echo ""
echo -e "${BLUE}bash deploy_on_server_fixed.sh${NC}"
echo ""

echo -e "${GREEN}🎉 修复版Docker部署脚本准备完成！${NC}"
echo -e "${YELLOW}请按照上述步骤在服务器上执行部署命令。${NC}" 