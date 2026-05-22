#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键修复：创建用户/重置密码/清除设备/设为管理员
"""

import sys
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'reading_companion.db')

def fix(phone, password, role):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 确保表存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("错误: users 表不存在，数据库可能损坏")
        conn.close()
        return
    
    # 查找用户
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()
    
    if user:
        cursor.execute('UPDATE users SET password = ?, role = ?, device_id = NULL, device_info = NULL WHERE id = ?',
                       (password, role, user['id']))
        print(f"用户已更新: {phone}")
        print(f"  密码: {password}")
        print(f"  角色: {role}")
        print(f"  设备绑定: 已清除")
    else:
        cursor.execute('''INSERT INTO users (phone, password, role, created_at) VALUES (?, ?, ?, datetime('now'))''',
                       (phone, password, role))
        print(f"用户已创建: {phone}")
        print(f"  密码: {password}")
        print(f"  角色: {role}")
    
    conn.commit()
    
    # 显示所有用户
    print("\n当前所有用户:")
    cursor.execute('SELECT id, phone, role FROM users')
    for u in cursor.fetchall():
        print(f"  ID:{u['id']} 手机号:{u['phone']} 角色:{u['role']}")
    
    conn.close()

if __name__ == '__main__':
    phone = sys.argv[1] if len(sys.argv) > 1 else '18674827052'
    password = sys.argv[2] if len(sys.argv) > 2 else 'admin123'
    role = sys.argv[3] if len(sys.argv) > 3 else 'admin'
    fix(phone, password, role)
