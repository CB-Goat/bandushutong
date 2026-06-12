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

@app.route('/index.html')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<page>.html')
def serve_page(page):
    """提供分页HTML文件"""
    allowed = {'catalog', 'reader', 'usercenter', 'admin'}
    if page in allowed:
        filepath = os.path.join(FRONTEND_DIR, page + '.html')
        if os.path.exists(filepath):
            return send_from_directory(FRONTEND_DIR, page + '.html')
    return jsonify({'error': 'Not found'}), 404

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

@app.route('/favicon.ico')
@app.route('/favicon.png')
def serve_favicon():
    """提供网站图标"""
    return send_from_directory(FRONTEND_DIR, 'favicon.png')

@app.route('/back.png')
def serve_back_icon():
    """提供返回按钮图标"""
    return send_from_directory(FRONTEND_DIR, 'back.png')

@app.route('/wechat_qrcode.png')
def serve_wechat_qrcode():
    """提供微信二维码图片"""
    return send_from_directory(FRONTEND_DIR, 'wechat_qrcode.png')

@app.route('/book_icons/<path:filename>')
def serve_book_icons(filename):
    """提供书籍图标，支持环境变量配置路径"""
    icons_path_env = os.environ.get('BOOK_ICONS_PATH')
    if icons_path_env and os.path.exists(icons_path_env):
        icons_dir = icons_path_env
    else:
        icons_dir = os.path.join(FRONTEND_DIR, 'book_icons')
    if os.path.exists(os.path.join(icons_dir, filename)):
        return send_from_directory(icons_dir, filename)
    default_icon = os.path.join(icons_dir, 'default.png')
    if os.path.exists(default_icon):
        return send_from_directory(icons_dir, 'default.png')
    return '', 200

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
os.makedirs('books', exist_ok=True)
os.makedirs('audio_files', exist_ok=True)

# 系统启动时检查并补齐固定音频文件（男声女声各4个，共8个）
# 幂等操作：已存在的文件不会重新生成
print("[TTS] 正在检查固定音频文件...", flush=True)
import sys; sys.stdout.flush()
try:
    from baidu_tts import ensure_fixed_audio_files
    result = ensure_fixed_audio_files()
    print(f"[TTS] 固定音频检查结果: {result}", flush=True)
except Exception as e:
    import traceback
    print(f"[TTS] 检查固定音频文件失败: {e}", flush=True)
    traceback.print_exc()

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
