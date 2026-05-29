#!/bin/bash
# 检查部署状态

echo "=== 检查部署状态 ==="

cd /www/dk_project/wwwroot/lit.handy.xin

echo ""
echo "1. 检查Docker容器状态："
docker-compose ps

echo ""
echo "2. 检查后端日志（最近20行）："
docker-compose logs --tail=20 backend

echo ""
echo "3. 测试后端API："
curl -s http://127.0.0.1:5000/api/version || echo "后端无响应"

echo ""
echo "4. 检查Nginx配置："
sudo nginx -t

echo ""
echo "5. 检查端口占用："
netstat -tlnp | grep -E ':(80|5000)'

echo ""
echo "=== 检查完成 ==="
