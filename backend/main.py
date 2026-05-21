# -*- coding: utf-8 -*-
"""
伴读书童 - 儿童课外阅读辅助工具
后端主入口
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import api_bp
from database import init_db

app = Flask(__name__, static_folder=None)
CORS(app)  # 允许跨域

# 前端文件目录
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

# 注册 API 蓝图
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    """提供前端首页"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# 初始化数据库
init_db()

if __name__ == '__main__':
    # 确保目录存在
    if not os.path.exists('books'):
        os.makedirs('books')
    if not os.path.exists('audio_files'):
        os.makedirs('audio_files')
    
    # 检查并生成固定音频文件
    try:
        from baidu_tts import is_configured, generate_fixed_audio_files
        if is_configured():
            print("[TTS] 检查固定音频文件...")
            generate_fixed_audio_files()
    except Exception as e:
        print(f"[TTS] 生成固定音频失败: {e}")
    
    # 从环境变量获取端口，默认5000
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 50)
    print("伴读书童后端服务启动")
    print("更新版本: #76")
    print("访问地址: http://localhost:%d" % port)
    print("API 地址: http://localhost:%d/api" % port)
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=False)
