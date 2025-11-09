# MySQL数据库配置 - 支持本地和Docker双重部署
import os

# 从环境变量获取配置，支持本地和Docker环境
# 本地开发默认使用localhost，Docker部署使用环境变量
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')  # 本地默认localhost
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB = os.getenv('MYSQL_DB', 'axspa')