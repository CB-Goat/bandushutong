#!/bin/bash
# 伴读书童 - CentOS 7.9 Docker 一键部署脚本（国内镜像版）

set -e

echo "=========================================="
echo "  伴读书童 Docker 部署脚本（国内镜像）"
echo "=========================================="

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 用户运行此脚本"
    exit 1
fi

# 1. 安装 Docker（使用阿里云镜像）
echo "[1/6] 安装 Docker..."
if ! command -v docker &> /dev/null; then
    # 卸载旧版本
    yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
    
    # 安装依赖
    yum install -y yum-utils device-mapper-persistent-data lvm2
    
    # 使用阿里云镜像源
    yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    
    # 安装 Docker
    yum install -y docker-ce docker-ce-cli containerd.io
    
    # 配置 Docker 使用国内镜像
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
    
    systemctl daemon-reload
    systemctl start docker
    systemctl enable docker
    echo "Docker 安装完成"
else
    echo "Docker 已安装"
fi

# 2. 安装 Docker Compose
echo "[2/6] 安装 Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    # 使用国内镜像下载
    curl -L "https://get.daocloud.io/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    echo "Docker Compose 安装完成"
else
    echo "Docker Compose 已安装"
fi

# 3. 创建项目目录
echo "[3/6] 创建项目目录..."
mkdir -p /opt/bandushutong
cd /opt/bandushutong

# 4. 克隆代码
echo "[4/6] 克隆代码..."
if [ -d ".git" ]; then
    git pull
else
    git clone https://github.com/CB-Goat/bandushutong.git .
fi

# 5. 创建数据目录
echo "[5/6] 创建数据目录..."
mkdir -p data books audio_files

# 6. 启动服务
echo "[6/6] 启动 Docker 服务..."
docker-compose down 2>/dev/null || true

# 使用国内镜像构建
docker-compose up -d --build

# 等待服务启动
sleep 5

# 初始化数据库和测试用户
docker exec bandushutong python -c "
import sys
sys.path.insert(0, 'backend')
from database import init_db, create_user
try:
    init_db()
    create_user('13800000000', '888888', 'admin')
    print('系统用户创建: 13800000000 / 888888')
except:
    print('系统用户已存在')
try:
    create_user('13900000000', '123456', 'user')
    print('普通用户创建: 13900000000 / 123456')
except:
    print('普通用户已存在')
"

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - 内网: http://localhost:8080"
echo "  - 外网: http://$(curl -s ifconfig.me):8080"
echo ""
echo "测试账号:"
echo "  - 系统用户: 13800000000 / 888888"
echo "  - 普通用户: 13900000000 / 123456"
echo ""
echo "常用命令:"
echo "  - 查看日志: docker logs -f bandushutong"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo "=========================================="
