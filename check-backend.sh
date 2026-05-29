#!/bin/bash
# 检查后端状态

cd /www/dk_project/wwwroot/lit.handy.xin

echo "=== 容器状态 ==="
docker-compose ps

echo ""
echo "=== 后端日志（最近50行）==="
docker-compose logs --tail=50 backend

echo ""
echo "=== 测试API ==="
sleep 2
curl -v http://127.0.0.1:5000/api/version 2>&1 | head -20
