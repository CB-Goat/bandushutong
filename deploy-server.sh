#!/bin/bash
# 服务器部署脚本 - 适用于非空目录

set -e

echo "=== Reading Companion 服务器部署 ==="

# 检查是否在正确目录
if [ ! -d "/www/dk_project/wwwroot/lit.handy.xin" ]; then
    echo "错误: 目录 /www/dk_project/wwwroot/lit.handy.xin 不存在"
    exit 1
fi

cd /www/dk_project/wwwroot/lit.handy.xin

# 如果目录非空，先备份再清空
if [ "$(ls -A)" ]; then
    echo "目录非空，备份现有文件..."
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    mv * "$BACKUP_DIR/" 2>/dev/null || true
    mv .* "$BACKUP_DIR/" 2>/dev/null || true
    echo "已备份到: $BACKUP_DIR"
fi

# 拉取代码
echo "拉取代码..."
git clone https://github.com/CB-Goat/bandushutong.git .

# 创建数据目录
mkdir -p data ssl

# 构建并启动
echo "构建并启动Docker容器..."
docker-compose down 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# 等待启动
echo "等待服务启动..."
sleep 10

# 检查状态
echo "=== 部署完成 ==="
docker-compose ps

echo ""
echo "访问地址: http://$(hostname -I | awk '{print $1}')"
