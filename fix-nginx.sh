#!/bin/bash
# 修复Nginx配置

echo "=== 修复Nginx配置 ==="

# 创建Nginx配置文件
cat > /tmp/lit.handy.xin.conf << 'EOF'
server {
    listen 80;
    server_name lit.handy.xin;

    root /www/dk_project/wwwroot/lit.handy.xin/frontend;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
        client_max_body_size 50M;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 复制到Nginx配置目录
sudo cp /tmp/lit.handy.xin.conf /www/server/panel/vhost/nginx/lit.handy.xin.conf

# 测试配置
sudo nginx -t

# 重载Nginx
sudo systemctl reload nginx

echo "=== Nginx配置完成 ==="
