# -*- coding: utf-8 -*-
"""
微信公众号自定义菜单创建脚本
使用方法：python create_wechat_menu.py
配置：在项目根目录 .env 文件中设置 WECHAT_APPID 和 WECHAT_APPSECRET
"""

import os
import sys
import json

# 添加后端目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# 加载 .env 文件
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())
        print(f"✅ 已加载 .env 文件: {env_path}")
    else:
        print(f"⚠️ 未找到 .env 文件: {env_path}")

load_env()

APP_ID = os.environ.get('WECHAT_APPID', '')
APP_SECRET = os.environ.get('WECHAT_APPSECRET', '')

# 菜单配置
MENU_CONFIG = {
    "button": [
        {
            "type": "click",
            "name": "欢迎语",
            "key": "welcome"
        },
        {
            "type": "click",
            "name": "悦读小将",
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
    import urllib.request
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        if 'access_token' in data:
            print(f"✅ 获取access_token成功")
            return data['access_token']
        else:
            print(f"❌ 获取access_token失败: {data}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def create_menu(access_token, menu_config):
    """创建自定义菜单"""
    import urllib.request
    url = f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}"
    data = json.dumps(menu_config, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        if result.get('errcode') == 0:
            print(f"✅ 菜单创建成功！")
            for btn in menu_config['button']:
                print(f"   - {btn['name']} (类型: {btn['type']}, Key: {btn['key']})")
        else:
            print(f"❌ 菜单创建失败: {result}")
        return result
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def delete_menu(access_token):
    """删除现有菜单"""
    import urllib.request
    url = f"https://api.weixin.qq.com/cgi-bin/menu/delete?access_token={access_token}"
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        if result.get('errcode') == 0:
            print(f"✅ 现有菜单已删除")
        else:
            print(f"   无需删除（可能没有菜单）")
    except:
        pass


if __name__ == '__main__':
    print("=" * 40)
    print("微信公众号自定义菜单创建工具")
    print("=" * 40)

    if not APP_ID or not APP_SECRET:
        print("❌ 请在 .env 文件中配置以下变量：")
        print("   WECHAT_APPID=你的AppID")
        print("   WECHAT_APPSECRET=你的AppSecret")
        print()
        print(f"   当前 APPID: {APP_ID or '(未设置)'}")
        print(f"   当前 APPSECRET: {APP_SECRET or '(未设置)'}")
        exit(1)

    print(f"\n   APPID: {APP_ID}")
    print(f"   APPSECRET: {APP_SECRET[:6]}{'*' * (len(APP_SECRET)-6)}")

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
