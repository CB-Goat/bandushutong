#!/bin/bash
# 启动Nginx

echo "=== 启动Nginx ==="

# 检查Nginx配置
sudo /www/server/nginx/sbin/nginx -t

# 启动Nginx
sudo /www/server/nginx/sbin/nginx

# 检查状态
ps aux | grep nginx

echo "=== Nginx已启动 ==="
