#!/bin/bash
# 伴读书童 - PythonAnywhere 一键部署脚本
# 在 PythonAnywhere 的 Bash Console 中执行

# ====== 修改这里：你的 PythonAnywhere 用户名 ======
USERNAME="你的用户名"
# =================================================

echo "=== 伴读书童 部署开始 ==="

# 1. 克隆代码
echo "[1/5] 克隆代码..."
cd /home/$USERNAME
if [ -d "bandushutong" ]; then
    cd bandushutong
    git pull
else
    git clone https://github.com/CB-Goat/bandushutong.git
    cd bandushutong
fi

# 2. 创建虚拟环境
echo "[2/5] 创建虚拟环境..."
virtualenv --python=python3.10 venv
source venv/bin/activate

# 3. 安装依赖
echo "[3/5] 安装依赖..."
pip install flask flask-cors python-docx lxml gunicorn

# 4. 初始化数据库和测试用户
echo "[4/5] 初始化数据库..."
cd /home/$USERNAME/bandushutong
python -c "
import sys
sys.path.insert(0, 'backend')
from database import init_db, create_user
init_db()
try:
    create_user('13800000000', '888888', 'admin')
    print('系统用户创建成功: 13800000000 / 888888')
except:
    print('系统用户已存在')
try:
    create_user('13900000000', '123456', 'user')
    print('普通用户创建成功: 13900000000 / 123456')
except:
    print('普通用户已存在')
"

# 5. 修改 wsgi.py 中的用户名
echo "[5/5] 更新 wsgi.py 配置..."
sed -i "s/你的用户名/$USERNAME/g" /home/$USERNAME/bandushutong/wsgi.py

echo ""
echo "=== 部署完成！==="
echo ""
echo "接下来请在 PythonAnywhere Web 面板配置："
echo "  1. 打开 Web 标签页"
echo "  2. 点击 'Add a new web app'"
echo "  3. 选择 Manual Configuration"
echo "  4. Python 版本选 3.10"
echo "  5. WSGI file 填: /home/$USERNAME/bandushutong/wsgi.py"
echo "  6. Virtualenv 填: /home/$USERNAME/bandushutong/venv"
echo "  7. 点击 Save，然后 Reload"
echo ""
echo "访问地址: https://$USERNAME.pythonanywhere.com"
