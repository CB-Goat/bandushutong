#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接修复登录问题 - 重置密码并清除设备绑定
"""

import sys
import os
import sqlite3

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'reading_companion.db')

def fix_user(phone, new_password):
    """重置用户密码并清除设备绑定"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找用户
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()
    
    if not user:
        print(f"错误: 用户 {phone} 不存在")
        # 列出所有用户
        cursor.execute('SELECT id, phone, role FROM users')
        users = cursor.fetchall()
        print("\n现有用户:")
        for u in users:
            print(f"  ID:{u['id']} 手机号:{u['phone']} 角色:{u['role']}")
        conn.close()
        return False
    
    print(f"找到用户: ID={user['id']}, 手机号={user['phone']}, 角色={user['role']}")
    print(f"当前密码: {user['password']}")
    print(f"当前设备: {user['device_id']}")
    
    # 更新密码并清除设备绑定
    cursor.execute('UPDATE users SET password = ?, device_id = NULL, device_info = NULL WHERE id = ?', 
                   (new_password, user['id']))
    conn.commit()
    conn.close()
    
    print(f"\n成功!")
    print(f"  密码已重置为: {new_password}")
    print(f"  设备绑定已清除")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python3 fix_login.py <手机号> <新密码>")
        print("示例: python3 fix_login.py 18674827052 admin123")
        sys.exit(1)
    
    phone = sys.argv[1]
    password = sys.argv[2]
    
    fix_user(phone, password)
