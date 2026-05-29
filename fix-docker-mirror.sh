#!/bin/bash
# 配置阿里云Docker镜像加速

echo "=== 配置阿里云Docker镜像加速 ==="

# 创建Docker配置目录
sudo mkdir -p /etc/docker

# 配置镜像加速（使用阿里云镜像）
sudo tee /etc/docker/daemon.json <<-'EOF'
{
    "registry-mirrors": [
        "https://mirror.ccs.tencentyun.com",
        "https://hub-mirror.c.163.com",
        "https://docker.mirrors.ustc.edu.cn"
    ],
    "dns": ["223.5.5.5", "8.8.8.8"]
}
EOF

# 重启Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

echo "Docker镜像加速配置完成"
echo "请重新运行 ./deploy.sh"
