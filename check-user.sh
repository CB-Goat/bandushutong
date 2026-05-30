#!/bin/bash
# 检查用户数据

cd /www/dk_project/wwwroot/lit.handy.xin

echo "=== 检查用户 18674827052 ==="
docker exec -it reading-companion-backend sqlite3 /app/instance/reading.db "SELECT id, username, phone, wechat_openid, created_at FROM users WHERE phone='18674827052';"

echo ""
echo "=== 所有用户列表（前10个）==="
docker exec -it reading-companion-backend sqlite3 /app/instance/reading.db "SELECT id, username, phone, created_at FROM users LIMIT 10;"

echo ""
echo "=== 用户表结构 ==="
docker exec -it reading-companion-backend sqlite3 /app/instance/reading.db ".schema users"
