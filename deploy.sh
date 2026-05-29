#!/bin/bash
# Reading Companion 部署脚本
# 用法: ./deploy.sh

set -e

echo "=== Reading Companion 部署脚本 ==="

# 创建必要目录
mkdir -p data ssl

# 拉取最新代码（如果有git仓库）
if [ -d ".git" ]; then
    echo "拉取最新代码..."
    git pull origin main
fi

# 构建并启动Docker容器
echo "构建并启动Docker容器..."
docker-compose down 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查容器状态
echo "检查容器状态..."
docker-compose ps

# 检查后端健康状态
echo "检查后端健康状态..."
for i in {1..10}; do
    if curl -sf http://localhost:5000/api/version > /dev/null 2>&1; then
        echo "✓ 后端服务正常"
        break
    fi
    echo "等待后端启动... ($i/10)"
    sleep 3
done

# 检查nginx状态
echo "检查Nginx状态..."
if curl -sf http://localhost > /dev/null 2>&1; then
    echo "✓ Nginx服务正常"
else
    echo "✗ Nginx服务异常"
fi

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://你的服务器IP"
