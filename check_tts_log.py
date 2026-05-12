"""
检查TTS生成日志和状态
用法：python3 check_tts_log.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db
from backend.baidu_tts import is_configured

print("=" * 50)
print("TTS 生成状态检查")
print("=" * 50)

# 1. 检查百度TTS配置
print("\n[1] 百度TTS配置:")
if is_configured():
    print("  ✅ 已配置")
else:
    print("  ❌ 未配置")
    print("  环境变量:")
    for key in ['BAIDU_TTS_APP_ID', 'BAIDU_TTS_API_KEY', 'BAIDU_TTS_SECRET_KEY']:
        val = os.environ.get(key, '')
        print(f"    {key}: {'已设置' if val else '未设置'}")

# 2. 检查书籍TTS状态
print("\n[2] 书籍TTS状态:")
conn = get_db()
cursor = conn.cursor()
cursor.execute('SELECT id, title, tts_status, tts_progress, total_sections FROM books ORDER BY id DESC LIMIT 5')
books = cursor.fetchall()
for b in books:
    print(f"  书籍 [{b['id']}] {b['title']}: {b['tts_status']} ({b['tts_progress']})")

# 3. 检查节的音频状态
print("\n[3] 最新书籍的节:")
if books:
    latest_book = books[0]['id']
    cursor.execute('SELECT id, section_number, audio_path, has_audio, audio_duration FROM sections WHERE book_id = ? ORDER BY id', (latest_book,))
    sections = cursor.fetchall()
    print(f"  书籍 {latest_book} 共有 {len(sections)} 个节:")
    for s in sections:
        status = "✅" if s['audio_path'] and s['has_audio'] else "❌"
        print(f"    节 {s['id']} (第{s['section_number']}节): {status} {s['audio_path'] or '无'} ({s['audio_duration'] or 0:.1f}s)")

conn.close()

# 4. 检查服务器日志
print("\n[4] 服务器日志 (最后20行):")
if os.path.exists('server.log'):
    with os.popen('tail -20 server.log') as f:
        print(f.read())
else:
    print("  无日志文件")

print("\n" + "=" * 50)
