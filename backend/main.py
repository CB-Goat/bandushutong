# -*- coding: utf-8 -*-
"""
悦读小将 - 儿童课外阅读辅助工具
后端主入口
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import api_bp
from database import init_db, cleanup_duplicate_progress

app = Flask(__name__, static_folder=None)
CORS(app)  # 允许跨域

# 前端文件目录
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

# 当前版本号 - 每次修改后手动更新
CURRENT_VERSION = '#328'

# 注册 API 蓝图
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/api/health')
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'version': CURRENT_VERSION})

@app.route('/')
def index():
    """提供前端首页"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/ranks/<path:filename>')
def serve_ranks(filename):
    """提供军衔肩章图片和头像"""
    ranks_dir = os.path.join(FRONTEND_DIR, 'ranks')
    return send_from_directory(ranks_dir, filename)

@app.route('/medals/<path:filename>')
def serve_medals(filename):
    """提供军功勋章图片"""
    medals_dir = os.path.join(FRONTEND_DIR, 'medals')
    return send_from_directory(medals_dir, filename)

@app.route('/favicon.png')
def serve_favicon():
    """提供网站图标"""
    return send_from_directory(FRONTEND_DIR, 'favicon.png')

@app.route('/book_icons/<path:filename>')
def serve_book_icons(filename):
    """提供书籍图标，不存在时返回默认图标"""
    icons_dir = os.path.join(FRONTEND_DIR, 'book_icons')
    icon_path = os.path.join(icons_dir, filename)
    if os.path.exists(icon_path):
        return send_from_directory(icons_dir, filename)
    else:
        # 返回默认书籍图标
        default_icon = os.path.join(FRONTEND_DIR, 'favicon.png')
        if os.path.exists(default_icon):
            return send_from_directory(FRONTEND_DIR, 'favicon.png')
        else:
            return '', 404

@app.route('/bookmark-icon.png')
def serve_bookmark_icon():
    """提供书签图标"""
    return send_from_directory(FRONTEND_DIR, 'bookmark-icon.png')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': CURRENT_VERSION})

# 初始化数据库
init_db()
cleanup_duplicate_progress()

# 确保目录存在
if not os.path.exists('books'):
    os.makedirs('books')
if not os.path.exists('audio_files'):
    os.makedirs('audio_files')

# 检查并生成固定音频文件（gunicorn启动时也需要执行）
# 生成男声女声各一套
try:
    from baidu_tts import is_configured, generate_fixed_audio_files_by_voice
    if is_configured():
        print("[TTS] 检查固定音频文件...")
        generate_fixed_audio_files_by_voice('male')
        generate_fixed_audio_files_by_voice('female')
except Exception as e:
    print(f"[TTS] 生成固定音频失败: {e}")

if __name__ == '__main__':
    # 从环境变量获取端口，默认5000
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 50)
    print("悦读小将后端服务启动")
    print("更新版本:", CURRENT_VERSION)
    print("访问地址: http://localhost:%d" % port)
    print("API 地址: http://localhost:%d/api" % port)
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=False)
