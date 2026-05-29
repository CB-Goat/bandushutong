#!/bin/bash
# 修复Docker DNS问题

echo "=== 配置Docker全局DNS ==="

# 创建Docker配置目录
sudo mkdir -p /etc/docker

# 配置DNS
sudo tee /etc/docker/daemon.json <<-'EOF'
{
    "dns": ["223.5.5.5", "8.8.8.8"],
    "dns-opts": ["ndots:0"]
}
EOF

# 重启Docker
sudo systemctl restart docker

echo "Docker DNS配置完成"
echo "请重新运行 ./deploy.sh"
