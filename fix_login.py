#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接修复登录问题 - 重置密码或创建管理员账号
"""

import sys
import os
import sqlite3

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'reading_companion.db')

def fix_or_create_user(phone, new_password, role='admin'):
    """重置用户密码或创建新用户"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找用户
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()
    
    if not user:
        print(f"用户 {phone} 不存在，创建新用户...")
        # 创建新用户
        cursor.execute('''
            INSERT INTO users (phone, password, role, created_at) 
            VALUES (?, ?, ?, datetime('now'))
        ''', (phone, new_password, role))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        print(f"成功创建用户!")
        print(f"  手机号: {phone}")
        print(f"  密码: {new_password}")
        print(f"  角色: {role}")
        print(f"  ID: {user_id}")
        return True
    
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

def list_all_users():
    """列出所有用户"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, phone, role, device_id FROM users ORDER BY id')
    users = cursor.fetchall()
    conn.close()
    
    print("\n=== 所有用户 ===")
    for u in users:
        device = u['device_id'][:10] + '...' if u['device_id'] else 'None'
        print(f"  ID:{u['id']} 手机号:{u['phone']} 角色:{u['role']} 设备:{device}")
    print(f"共 {len(users)} 个用户\n")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # 无参数，列出所有用户
        list_all_users()
        print("用法:")
        print("  python3 fix_login.py              # 列出所有用户")
        print("  python3 fix_login.py <手机号> <密码> [admin|user]  # 重置或创建用户")
        sys.exit(0)
    
    if len(sys.argv) < 3:
        print("用法: python3 fix_login.py <手机号> <新密码> [admin|user]")
        print("示例: python3 fix_login.py 18674827052 admin123 admin")
        sys.exit(1)
    
    phone = sys.argv[1]
    password = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else 'admin'
    
    fix_or_create_user(phone, password, role)
