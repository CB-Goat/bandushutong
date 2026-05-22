"""
悦读小将 - TTS 语音生成服务
使用阿里云 TTS（国内服务，儿童音色好）
"""

import os
import requests
import json
from datetime import datetime

# 阿里云 TTS 配置（需要用户填写）
ALIBABA_TTS_APPKEY = os.environ.get('ALIBABA_TTS_APPKEY', '')
ALIBABA_TTS_TOKEN = os.environ.get('ALIBABA_TTS_TOKEN', '')

# TTS 服务 URL
TTS_URL = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"

# 音频文件保存目录
AUDIO_DIR = os.path.join(os.path.dirname(__file__), '..', 'audio_files')
os.makedirs(AUDIO_DIR, exist_ok=True)

def generate_audio(text, section_id, voice='xiaoyan'):
    """
    生成语音文件
    
    参数:
        text: 要合成的文本
        section_id: 小节ID（用于文件名）
        voice: 音色选择
            - xiaoyan: 小燕（标准女声）
            - xiaoyou: 小悠（儿童音）
            - xiaomei: 小美（温柔女声）
    
    返回:
        audio_path: 音频文件相对路径
    """
    
    # 如果没有配置阿里云，使用模拟模式
    if not ALIBABA_TTS_APPKEY or not ALIBABA_TTS_TOKEN:
        print("警告：未配置阿里云 TTS，使用模拟模式")
        return generate_mock_audio(text, section_id)
    
    # 构建请求
    headers = {
        'Content-Type': 'application/json',
        'X-NLS-Token': ALIBABA_TTS_TOKEN
    }
    
    payload = {
        'appkey': ALIBABA_TTS_APPKEY,
        'text': text,
        'format': 'mp3',
        'sample_rate': 16000,
        'voice': voice,
        'volume': 50,
        'speech_rate': 0,
        'pitch_rate': 0
    }
    
    try:
        response = requests.post(TTS_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            # 保存音频文件
            filename = f'section_{section_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3'
            filepath = os.path.join(AUDIO_DIR, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"音频生成成功: {filepath}")
            return f'audio_files/{filename}'
        else:
            print(f"TTS 请求失败: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        print(f"TTS 生成错误: {e}")
        return None

def generate_mock_audio(text, section_id):
    """
    模拟音频生成（用于开发测试）
    创建一个空文件占位
    """
    filename = f'section_{section_id}_mock.mp3'
    filepath = os.path.join(AUDIO_DIR, filename)
    
    # 创建一个小的 MP3 占位文件（静音）
    # 实际是一个最小的有效 MP3 文件头
    mp3_header = bytes([
        0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ])
    
    with open(filepath, 'wb') as f:
        f.write(mp3_header)
    
    print(f"模拟音频生成: {filepath}")
    return f'audio_files/{filename}'

def get_audio_duration(text):
    """
    估算音频时长（秒）
    按每分钟 200 字计算
    """
    char_count = len(text)
    duration = (char_count / 200) * 60
    return int(duration)

if __name__ == '__main__':
    # 测试
    test_text = "这是一个测试文本，用于生成语音。"
    result = generate_audio(test_text, 1)
    print(f"生成结果: {result}")
