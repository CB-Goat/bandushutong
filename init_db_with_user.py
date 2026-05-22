#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化数据库并创建用户
"""

import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import init_db, create_user

# 初始化数据库（创建所有表）
init_db()
print("数据库表已创建")

# 创建系统用户
try:
    create_user('13800000000', '888888', role='admin')
    print("系统用户创建: 13800000000 / 888888")
except:
    print("系统用户已存在")

try:
    create_user('13900000000', '123456', role='user')
    print("普通用户创建: 13900000000 / 123456")
except:
    print("普通用户已存在")

try:
    create_user('18674827052', 'admin123', role='admin')
    print("管理员用户创建: 18674827052 / admin123")
except:
    print("管理员用户已存在")

print("\n数据库初始化完成！")
