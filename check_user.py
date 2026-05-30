#!/usr/bin/env python3
# 检查用户数据

import sqlite3
import sys

DB_PATH = '/www/dk_project/wwwroot/lit.handy.xin/data/reading.db'

def check_user(phone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查询指定用户
    print(f"=== 查询用户 {phone} ===")
    cursor.execute("SELECT id, username, phone, wechat_openid, created_at FROM users WHERE phone=?", (phone,))
    user = cursor.fetchone()
    if user:
        print(f"ID: {user[0]}")
        print(f"用户名: {user[1]}")
        print(f"手机号: {user[2]}")
        print(f"微信OpenID: {user[3]}")
        print(f"创建时间: {user[4]}")
    else:
        print("用户不存在")

    # 查询所有用户
    print("\n=== 所有用户列表 ===")
    cursor.execute("SELECT id, username, phone, created_at FROM users LIMIT 20")
    for row in cursor.fetchall():
        print(f"ID:{row[0]} 用户名:{row[1]} 手机:{row[2]} 创建:{row[3]}")

    # 查看表结构
    print("\n=== users表结构 ===")
    cursor.execute("PRAGMA table_info(users)")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]})")

    conn.close()

if __name__ == '__main__':
    phone = sys.argv[1] if len(sys.argv) > 1 else '18674827052'
    check_user(phone)
