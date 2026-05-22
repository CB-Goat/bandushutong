#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置用户密码脚本
用法: python3 reset_password.py <手机号> <新密码>
"""

import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_user_by_phone, update_user_password

def reset_password(phone, new_password):
    """重置指定手机号的密码"""
    user = get_user_by_phone(phone)
    if not user:
        print(f"错误: 用户 {phone} 不存在")
        return False
    
    update_user_password(user['id'], new_password)
    print(f"成功: 用户 {phone} 的密码已重置为: {new_password}")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python3 reset_password.py <手机号> <新密码>")
        print("示例: python3 reset_password.py 18674827052 admin123")
        sys.exit(1)
    
    phone = sys.argv[1]
    password = sys.argv[2]
    
    reset_password(phone, password)
