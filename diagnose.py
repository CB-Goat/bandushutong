"""
诊断修复脚本 - 在服务器上运行
用法：python3 diagnose.py
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("伴读书童 - 诊断修复")
print("=" * 50)

# 1. 检查前端播放器代码
print("\n[1] 检查前端播放器代码...")
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

if '_checkTTSStatus' in html:
    print("  ✅ 新播放器代码已替换")
else:
    print("  ❌ 旧播放器代码未替换！需要运行 python3 replace_player.py")

# 2. 检查数据库
print("\n[2] 检查数据库...")
from backend.database import get_db

conn = get_db()
cursor = conn.cursor()

# 检查 books 表是否有 tts_status 列
cursor.execute("PRAGMA table_info(books)")
cols = [row[1] for row in cursor.fetchall()]
if 'tts_status' in cols:
    print("  ✅ books.tts_status 列存在")
else:
    print("  ❌ books.tts_status 列不存在，正在添加...")
    cursor.execute('ALTER TABLE books ADD COLUMN tts_status TEXT DEFAULT "none"')
    cursor.execute('ALTER TABLE books ADD COLUMN tts_progress TEXT DEFAULT ""')
    conn.commit()
    print("  ✅ 已添加")

# 检查 sections 表是否有 audio_duration 列
cursor.execute("PRAGMA table_info(sections)")
cols = [row[1] for row in cursor.fetchall()]
if 'audio_duration' in cols:
    print("  ✅ sections.audio_duration 列存在")
else:
    print("  ❌ sections.audio_duration 列不存在，正在添加...")
    cursor.execute('ALTER TABLE sections ADD COLUMN audio_duration REAL DEFAULT 0')
    cursor.execute('ALTER TABLE sections ADD COLUMN char_timeline TEXT')
    conn.commit()
    print("  ✅ 已添加")

# 3. 检查音频文件和数据库状态
print("\n[3] 检查音频文件和数据库状态...")
audio_dir = 'audio_files'
if os.path.exists(audio_dir):
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    print(f"  音频文件目录有 {len(audio_files)} 个MP3文件")
else:
    audio_files = []
    print("  ❌ audio_files 目录不存在")

# 检查数据库中的 sections
cursor.execute('SELECT id, audio_path, has_audio, audio_duration FROM sections')
sections = cursor.fetchall()
has_audio_count = 0
no_audio_count = 0
for s in sections:
    if s['audio_path'] and s['has_audio']:
        has_audio_count += 1
    else:
        no_audio_count += 1

print(f"  数据库共 {len(sections)} 个节")
print(f"  有音频记录: {has_audio_count}")
print(f"  无音频记录: {no_audio_count}")

# 4. 修复：将已有的音频文件关联到数据库
print("\n[4] 修复音频文件关联...")
fixed = 0
for s in sections:
    sid = s['id']
    expected_file = f'section_{sid}.mp3'
    if expected_file in audio_files and not s['audio_path']:
        audio_path = f'audio_files/{expected_file}'
        cursor.execute(
            'UPDATE sections SET audio_path = ?, has_audio = 1 WHERE id = ?',
            (audio_path, sid)
        )
        fixed += 1
        print(f"  修复节 {sid}: {audio_path}")

conn.commit()

if fixed > 0:
    print(f"  ✅ 修复了 {fixed} 个节的音频关联")
else:
    print("  无需修复")

# 5. 检查百度TTS配置
print("\n[5] 检查百度TTS配置...")
tts_app_id = os.environ.get('BAIDU_TTS_APP_ID', '')
tts_api_key = os.environ.get('BAIDU_TTS_API_KEY', '')
tts_secret = os.environ.get('BAIDU_TTS_SECRET_KEY', '')
if tts_app_id and tts_api_key and tts_secret:
    print(f"  ✅ 百度TTS已配置 (AppID: {tts_app_id[:6]}...)")
else:
    print("  ❌ 百度TTS未配置！需要设置环境变量：")
    if not tts_app_id: print("    - BAIDU_TTS_APP_ID")
    if not tts_api_key: print("    - BAIDU_TTS_API_KEY")
    if not tts_secret: print("    - BAIDU_TTS_SECRET_KEY")

# 6. 检查 ffmpeg
print("\n[6] 检查 ffmpeg...")
ffmpeg_exists = os.system('which ffprobe > /dev/null 2>&1') == 0
if ffmpeg_exists:
    print("  ✅ ffprobe 已安装")
else:
    print("  ❌ ffprobe 未安装（音频时长将使用估算值）")

# 7. 检查书籍TTS状态
print("\n[7] 检查书籍TTS状态...")
cursor.execute('SELECT id, title, tts_status, tts_progress FROM books')
books = cursor.fetchall()
for b in books:
    status = b['tts_status'] or 'none'
    progress = b['tts_progress'] or ''
    print(f"  书籍 [{b['id']}] {b['title']}: {status} ({progress})")

conn.close()

print("\n" + "=" * 50)
print("诊断完成")
print("=" * 50)
