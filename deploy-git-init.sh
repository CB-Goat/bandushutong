#!/bin/bash
# 使用git init方式部署

cd /www/dk_project/wwwroot/lit.handy.xin

# 初始化git
git init

# 添加远程仓库
git remote add origin https://github.com/CB-Goat/bandushutong.git

# 拉取代码
git pull origin main

# 创建数据目录
mkdir -p data ssl

# 部署
./deploy.sh
