# 伴读书童 - Render 部署指南

## 准备工作

### 1. 注册 Render 账号
- 访问 https://render.com
- 使用 GitHub 账号登录

### 2. 创建 GitHub 仓库
```bash
# 在 reading-companion 目录下初始化 git
cd reading-companion
git init
git add .
git commit -m "Initial commit"

# 在 GitHub 创建新仓库，然后推送
git remote add origin https://github.com/你的用户名/伴读书童.git
git push -u origin main
```

## 部署步骤

### 步骤1：在 Render 创建 Web Service
1. 登录 Render 控制台
2. 点击 "New" → "Web Service"
3. 选择你的 GitHub 仓库

### 步骤2：配置服务
| 配置项 | 值 |
|--------|-----|
| Name | 伴读书童 (或任意名称) |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn backend.main:app --bind 0.0.0.0:$PORT --workers 2` |
| Plan | Free |

### 步骤3：高级设置（可选）
点击 "Advanced" 添加环境变量：
- `PYTHON_VERSION`: `3.11.0`
- `FLASK_ENV`: `production`

### 步骤4：部署
点击 "Create Web Service"，Render 会自动：
1. 拉取代码
2. 安装依赖
3. 启动服务

等待部署完成，获得外网地址：`https://你的服务名.onrender.com`

## 注意事项

### 免费版限制
- **休眠机制**：15分钟无访问会自动休眠，下次访问需等待10-30秒启动
- **带宽**：每月100GB
- **磁盘**：512MB

### 数据持久化
- MySQL 数据库会保存在磁盘上
- 但免费版磁盘非永久存储（重启可能丢失）
- **建议**：重要数据定期导出备份

### 自定义域名（可选）
1. 在 Render 控制台点击 "Settings"
2. 找到 "Custom Domains"
3. 添加你的域名并按照提示配置 DNS

## 部署后测试

```bash
# 测试健康检查
curl https://你的服务名.onrender.com/health

# 测试登录API
curl -X POST https://你的服务名.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800000000","auth_code":"888888"}'
```

## 故障排查

### 部署失败
1. 查看 Render 的 "Logs" 标签页
2. 检查 requirements.txt 是否有语法错误
3. 确认 main.py 中的路径正确

### 服务启动后无法访问
1. 检查端口是否正确使用 `$PORT` 环境变量
2. 查看日志确认服务是否成功启动
3. 确认数据库初始化成功

### 数据库问题
如果数据库丢失，需要重新初始化：
```bash
# 通过 Render Shell 执行
python -c "from backend.database import init_db; init_db()"
python -c "from backend.database import create_user; create_user('13800000000', '888888', 'admin')"
```
