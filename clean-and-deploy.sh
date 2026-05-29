#!/bin/bash
# 清理并部署

cd /www/dk_project/wwwroot/lit.handy.xin

# 删除所有文件（包括隐藏文件）
rm -rf .* * 2>/dev/null || true

# 拉取代码
git clone https://github.com/CB-Goat/bandushutong.git .

# 创建数据目录
mkdir -p data ssl

# 部署
./deploy.sh
