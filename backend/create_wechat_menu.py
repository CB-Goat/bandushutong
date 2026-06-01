# -*- coding: utf-8 -*-
"""
微信公众自定义菜单创建脚本
使用方法：python create_wechat_menu.py
"""

import requests
import json

# ===== 配置 =====
APP_ID = 'wx6032ec9465fc7483'
APP_SECRET = '你的AppSecret'  # 去微信开发者平台获取

# 菜单配置
MENU_CONFIG = {
    "button": [
        {
            "type": "click",
            "name": "开始阅读",
            "key": "start_reading"
        },
        {
            "type": "click",
            "name": "使用帮助",
            "key": "help"
        }
    ]
}


def get_access_token(app_id, app_secret):
    """获取公众号access_token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    resp = requests.get(url)
    data = resp.json()
    if 'access_token' in data:
        print(f"✅ 获取access_token成功")
        return data['access_token']
    else:
        print(f"❌ 获取access_token失败: {data}")
        return None


def create_menu(access_token, menu_config):
    """创建自定义菜单"""
    url = f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}"
    resp = requests.post(url, json=menu_config, headers={'Content-Type': 'application/json'})
    data = resp.json()
    if data.get('errcode') == 0:
        print(f"✅ 菜单创建成功！")
        print(f"   菜单内容：")
        for btn in menu_config['button']:
            print(f"   - {btn['name']} (类型: {btn['type']}, Key: {btn['key']})")
    else:
        print(f"❌ 菜单创建失败: {data}")
    return data


def delete_menu(access_token):
    """删除现有菜单（可选）"""
    url = f"https://api.weixin.qq.com/cgi-bin/menu/delete?access_token={access_token}"
    resp = requests.get(url)
    data = resp.json()
    if data.get('errcode') == 0:
        print(f"✅ 现有菜单已删除")
    else:
        print(f"   无需删除（可能没有菜单）")
    return data


if __name__ == '__main__':
    print("=" * 40)
    print("微信公众号自定义菜单创建工具")
    print("=" * 40)

    if APP_SECRET == '你的AppSecret':
        print("❌ 请先填写 APP_SECRET！")
        print("   获取方式：微信开发者平台 → 公众号 → 基础信息 → AppSecret")
        exit(1)

    # 1. 获取access_token
    print("\n[1/3] 获取access_token...")
    token = get_access_token(APP_ID, APP_SECRET)
    if not token:
        exit(1)

    # 2. 删除旧菜单
    print("\n[2/3] 清理旧菜单...")
    delete_menu(token)

    # 3. 创建新菜单
    print("\n[3/3] 创建新菜单...")
    create_menu(token, MENU_CONFIG)

    print("\n" + "=" * 40)
    print("完成！请在微信中关注公众号查看菜单。")
    print("=" * 40)
