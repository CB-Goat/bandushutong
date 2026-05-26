#!/bin/bash
# 悦读小将服务器更新脚本
# 用法: ./update_server.sh

echo "=========================================="
echo "悦读小将服务器更新脚本"
echo "=========================================="

# 进入项目目录
cd /opt/bandushutong

# 拉取最新代码
echo "[1/3] 拉取最新代码..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "错误: git pull 失败"
    exit 1
fi

# 检查是否需要初始化数据库（仅当表不存在时）
echo "[2/3] 检查数据库..."
python3 -c "
import sqlite3
import os
db_path = 'backend/reading_companion.db'
if not os.path.exists(db_path):
    print('数据库不存在，需要初始化')
    exit(1)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='books'\")
if not cursor.fetchone():
    print('表不存在，需要初始化')
    exit(1)
conn.close()
print('数据库已存在，跳过初始化')
exit(0)
" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "初始化数据库..."
    python3 init_db_with_user.py 2>&1 | grep -E "(创建|插入|已存在|完成)" || true
else
    echo "数据库已就绪"
fi

# 重启服务
echo "[3/3] 重启服务..."
fuser -k 8080/tcp 2>/dev/null
sleep 2
PORT=8080 nohup python3 backend/main.py > backend.log 2>&1 &
sleep 3

# 显示启动日志（包含清理信息）
echo ""
echo "--- 服务启动日志 (最后30行) ---"
tail -30 backend.log 2>/dev/null || echo "(无日志)"
echo "--- 服务启动日志结束 ---"

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
