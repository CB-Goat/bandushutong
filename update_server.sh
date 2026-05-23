#!/bin/bash
# 悦读小将服务器更新脚本
# 用法: ./update_server.sh

echo "=========================================="
echo "悦读小将服务器更新脚本"
echo "=========================================="

# 进入项目目录
cd /opt/bandushutong

# 拉取最新代码
echo "[1/4] 拉取最新代码..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "错误: git pull 失败"
    exit 1
fi

# 初始化数据库
echo "[2/4] 初始化数据库..."
python3 init_db_with_user.py

# 更新军衔数据
echo "[3/4] 更新军衔数据..."
python3 update_ranks.py

# 重启服务
echo "[4/4] 重启服务..."
fuser -k 8080/tcp 2>/dev/null
sleep 2
PORT=8080 nohup python3 backend/main.py > backend.log 2>&1 &
sleep 3

# 检查服务是否启动
echo ""
echo "检查服务状态..."
HEALTH_RESPONSE=$(curl -s http://localhost:8080/health 2>&1)
echo "Health API 返回: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | grep -q "version"; then
    VERSION=$(echo "$HEALTH_RESPONSE" | grep -o '"version": *"#[0-9]*"' | grep -o '#[0-9]*')
    echo ""
    echo "=========================================="
    echo "✅ 更新成功！"
    echo "当前版本: $VERSION"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "⚠️ 服务可能未完全启动，请稍后手动检查"
    echo "命令: curl http://localhost:8080/health"
    echo "=========================================="
fi
