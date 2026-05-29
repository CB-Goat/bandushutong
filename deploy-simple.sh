#!/bin/bash
# 简单部署脚本

cd /www/dk_project/wwwroot/lit.handy.xin

# 删除现有文件
echo "清理现有文件..."
rm -f 404.html index.html

# 拉取代码
echo "拉取代码..."
git clone https://github.com/CB-Goat/bandushutong.git .

# 创建数据目录
mkdir -p data ssl

# 部署
echo "部署..."
./deploy.sh
