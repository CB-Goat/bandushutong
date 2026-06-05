# 伴读书童 - Docker 部署指南

## 方案一：一键部署（推荐）

### 1. SSH 登录服务器
```bash
ssh root@您的服务器IP
```

### 2. 下载并执行部署脚本
```bash
curl -fsSL https://raw.githubusercontent.com/CB-Goat/bandushutong/main/deploy-docker.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh
```

### 3. 完成！
部署完成后会显示访问地址和测试账号。

---

## 方案二：手动部署

### 1. 安装 Docker 和 Docker Compose
```bash
# 安装 Docker
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 2. 克隆代码并启动
```bash
mkdir -p /opt/bandushutong
cd /opt/bandushutong
git clone https://github.com/CB-Goat/bandushutong.git .
docker-compose up -d --build
```

### 3. 初始化数据库
```bash
docker exec bandushutong python -c "
import sys
sys.path.insert(0, 'backend')
from database import init_db, create_user
init_db()
create_user('13800000000', '888888', 'admin')
create_user('13900000000', '123456', 'user')
"
```

---

## 访问地址

- **内网**: http://localhost:8080
- **外网**: http://您的服务器IP:8080

---

## 常用命令

| 命令 | 说明 |
|------|------|
| `docker logs -f bandushutong` | 查看实时日志 |
| `docker-compose down` | 停止服务 |
| `docker-compose up -d` | 启动服务 |
| `docker-compose restart` | 重启服务 |
| `docker exec -it bandushutong bash` | 进入容器 |

---

## 数据备份

数据库和上传的文件都在 `/opt/bandushutong` 目录：
- `books/` - 上传的书籍文件
- `audio_files/` - 生成的音频文件

备份命令：
```bash
cd /opt/bandushutong
tar czvf backup-$(date +%Y%m%d).tar.gz reading_companion.db books/ audio_files/
```

---

## 防火墙配置

如果无法访问，请开放 8080 端口：
```bash
# 开放 8080 端口
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

# 或使用 iptables
iptables -I INPUT -p tcp --dport 8080 -j ACCEPT
```

---

## 配置 Nginx 反向代理（可选）

如需使用域名和 HTTPS，配置 Nginx：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
