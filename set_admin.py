#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将用户升级为系统管理员
"""

import sys
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'reading_companion.db')

def set_admin(phone):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()
    
    if not user:
        print(f"错误: 用户 {phone} 不存在")
        cursor.execute('SELECT id, phone, role FROM users')
        for u in cursor.fetchall():
            print(f"  ID:{u['id']} 手机号:{u['phone']} 角色:{u['role']}")
        conn.close()
        return False
    
    print(f"找到用户: ID={user['id']}, 手机号={user['phone']}, 当前角色={user['role']}")
    
    cursor.execute('UPDATE users SET role = ? WHERE id = ?', ('admin', user['id']))
    conn.commit()
    conn.close()
    
    print(f"成功! 用户 {phone} 已升级为系统管理员")
    return True

if __name__ == '__main__':
    phone = sys.argv[1] if len(sys.argv) > 1 else '18674827052'
    set_admin(phone)
