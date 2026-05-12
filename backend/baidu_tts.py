"""
伴读书童 - 百度 TTS 语音合成服务
支持 Web Speech API 降级到百度云端 TTS
"""

import os
import json
import time
import hashlib
import requests
from datetime import datetime

# 百度 TTS 配置（通过环境变量或直接填写）
BAIDU_TTS_APP_ID = os.environ.get('BAIDU_TTS_APP_ID', '')
BAIDU_TTS_API_KEY = os.environ.get('BAIDU_TTS_API_KEY', '')
BAIDU_TTS_SECRET_KEY = os.environ.get('BAIDU_TTS_SECRET_KEY', '')

# 百度 TTS API
BAIDU_TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
BAIDU_TTS_URL = 'https://tsn.baidu.com/text2audio'

# 音频文件保存目录
AUDIO_DIR = os.path.join(os.path.dirname(__file__), '..', 'audio_files')
os.makedirs(AUDIO_DIR, exist_ok=True)

# 缓存 access_token
_cached_token = ''
_token_expire_time = 0


def get_access_token():
    """获取百度 API access_token"""
    global _cached_token, _token_expire_time
    
    # 如果 token 还没过期，直接返回
    if _cached_token and time.time() < _token_expire_time:
        return _cached_token
    
    if not BAIDU_TTS_APP_ID or not BAIDU_TTS_API_KEY or not BAIDU_TTS_SECRET_KEY:
        print("警告：未配置百度 TTS 密钥")
        return None
    
    try:
        params = {
            'grant_type': 'client_credentials',
            'client_id': BAIDU_TTS_API_KEY,
            'client_secret': BAIDU_TTS_SECRET_KEY
        }
        response = requests.post(BAIDU_TOKEN_URL, params=params, timeout=10)
        result = response.json()
        
        if 'access_token' in result:
            _cached_token = result['access_token']
            _token_expire_time = time.time() + result.get('expires_in', 2592000) - 600
            print("百度 TTS token 获取成功")
            return _cached_token
        else:
            print(f"获取 token 失败: {result}")
            return None
    except Exception as e:
        print(f"获取 token 异常: {e}")
        return None


def text_to_speech(text, section_id=None, speed=5, pitch=5, volume=5, person=0):
    """
    调用百度 TTS 合成语音
    
    参数:
        text: 要合成的文本（最多1024字节）
        section_id: 小节ID（用于缓存文件名）
        speed: 语速 0-15，默认5
        pitch: 音调 0-15，默认5
        volume: 音量 0-15，默认5
        person: 发音人选择
            0: 普通女声（默认）
            1: 普通男声
            3: 情感合成-度逍遥
            4: 情感合成-度丫丫
            5: 情感合成-度小娇
            103: 情感合成-度米朵
            106: 情感合成-度小萌
            111: 情感合成-度小甜
    
    返回:
        audio_path: 音频文件路径，失败返回 None
    """
    token = get_access_token()
    if not token:
        return None
    
    # 百度 TTS 单次最多 1024 字节，需要分段
    # 先尝试直接合成
    try:
        params = {
            'tok': token,
            'tex': text,
            'per': person,
            'spd': speed,
            'pit': pitch,
            'vol': volume,
            'aue': 3,  # MP3 格式
            'cuid': 'bandushutong_app',
            'lan': 'zh',
            'ctp': 1
        }
        
        response = requests.post(BAIDU_TTS_URL, params=params, timeout=30)
        
        content_type = response.headers.get('Content-Type', '')
        
        if 'audio' in content_type:
            # 成功返回音频
            if section_id:
                filename = f'section_{section_id}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return f'audio_files/{filename}'
            else:
                # 临时文件
                filename = f'temp_{int(time.time())}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return f'audio_files/{filename}'
        else:
            # 返回了错误信息
            result = response.json()
            print(f"百度 TTS 错误: {result}")
            return None
            
    except Exception as e:
        print(f"百度 TTS 异常: {e}")
        return None


def text_to_speech_long(text, section_id=None, speed=5, pitch=5, volume=5, person=0):
    """
    合成长文本（自动分段合成）
    百度 TTS 单次最多 1024 字节（约 500 个中文字符）
    
    返回: 音频文件路径列表
    """
    # 按句号分段，每段不超过 500 字符
    segments = []
    current = ''
    for char in text:
        current += char
        if len(current.encode('utf-8')) >= 900 or char in '。！？\n':
            if current.strip():
                segments.append(current.strip())
            current = ''
    if current.strip():
        segments.append(current.strip())
    
    if not segments:
        return []
    
    # 合成每段
    audio_paths = []
    for i, seg in enumerate(segments):
        path = text_to_speech(seg, 
                              section_id=f'{section_id}_{i}' if section_id else None,
                              speed=speed, pitch=pitch, volume=volume, person=person)
        if path:
            audio_paths.append(path)
    
    return audio_paths


def is_configured():
    """检查百度 TTS 是否已配置"""
    return bool(BAIDU_TTS_APP_ID and BAIDU_TTS_API_KEY and BAIDU_TTS_SECRET_KEY)


if __name__ == '__main__':
    if is_configured():
        print("百度 TTS 已配置")
        result = text_to_speech("你好，这是一个测试。", section_id=999)
        print(f"测试结果: {result}")
    else:
        print("百度 TTS 未配置，请设置环境变量:")
        print("  BAIDU_TTS_APP_ID")
        print("  BAIDU_TTS_API_KEY")
        print("  BAIDU_TTS_SECRET_KEY")
