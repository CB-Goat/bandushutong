#!/usr/bin/env python3
# 设置用户为管理员

import sqlite3
import sys

DB_PATH = '/www/dk_project/wwwroot/lit.handy.xin/data/reading.db'

def set_admin(phone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查询用户
    cursor.execute("SELECT id, username, role FROM users WHERE phone=?", (phone,))
    user = cursor.fetchone()

    if not user:
        print(f"用户 {phone} 不存在")
        conn.close()
        return

    print(f"当前用户: ID={user[0]}, 用户名={user[1]}, 角色={user[2]}")

    # 更新为admin
    cursor.execute("UPDATE users SET role='admin' WHERE phone=?", (phone,))
    conn.commit()

    print(f"✓ 用户 {phone} 已设置为管理员")

    conn.close()

if __name__ == '__main__':
    phone = sys.argv[1] if len(sys.argv) > 1 else '18674827052'
    set_admin(phone)
