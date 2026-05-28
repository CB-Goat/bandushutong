#!/bin/bash
# 版本号检查脚本 - 确保 main.py 中的版本号与最新 git 提交一致

# 获取 git 最新提交的版本号
GIT_VERSION=$(git log -1 --oneline | grep -oP '#\d+' | head -1)

# 获取 main.py 中的版本号
PY_VERSION=$(grep -oP "version': '#\K\d+" backend/main.py)

echo "Git 最新版本: $GIT_VERSION"
echo "main.py 版本: $PY_VERSION"

if [ "$GIT_VERSION" != "$PY_VERSION" ]; then
    echo "❌ 版本号不一致！"
    echo "请将 backend/main.py 中的版本号从 #$PY_VERSION 改为 #$GIT_VERSION"
    exit 1
else
    echo "✅ 版本号一致"
fi
