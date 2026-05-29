#!/bin/bash
# 本地Python部署（不使用Docker）

set -e

echo "=== Reading Companion 本地部署 ==="

cd /www/dk_project/wwwroot/lit.handy.xin

# 创建虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 创建数据目录
mkdir -p data

# 初始化数据库
echo "初始化数据库..."
cd backend
python3 -c "from database import init_db; init_db()" || true
cd ..

# 启动后端（使用gunicorn）
echo "启动后端服务..."
nohup venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --access-logfile - --error-logfile - backend.main:app > backend.log 2>&1 &

# 配置Nginx
echo "配置Nginx..."
sudo tee /etc/nginx/conf.d/lit.handy.xin.conf << 'EOF'
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

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 测试并重载Nginx
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://lit.handy.xin"
echo ""
echo "管理命令:"
echo "  查看日志: tail -f /www/dk_project/wwwroot/lit.handy.xin/backend.log"
echo "  停止服务: pkill -f gunicorn"
echo "  重启服务: ./deploy-local.sh"
