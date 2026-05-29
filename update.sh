#!/bin/bash
# Reading Companion 更新脚本
# 用法: ./update.sh

set -e

echo "=== Reading Companion 更新脚本 ==="

# 拉取最新代码
if [ -d ".git" ]; then
    echo "拉取最新代码..."
    git pull origin main
else
    echo "错误: 不是git仓库，请手动更新代码"
    exit 1
fi

# 重新构建并重启容器
echo "重新构建并重启容器..."
docker-compose up -d --build

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查后端健康状态
echo "检查后端健康状态..."
if curl -sf http://localhost:5000/api/version > /dev/null 2>&1; then
    echo "✓ 后端服务正常"
else
    echo "✗ 后端服务异常，请检查日志"
    docker-compose logs backend
    exit 1
fi

echo ""
echo "=== 更新完成 ==="
