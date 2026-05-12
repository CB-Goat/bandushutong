"""
检查音频文件是否正确
用法：python3 check_audio.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db

print("=" * 50)
print("音频文件检查")
print("=" * 50)

# 1. 检查音频目录
audio_dir = 'audio_files'
if not os.path.exists(audio_dir):
    print(f"\n❌ 音频目录不存在: {audio_dir}")
else:
    files = os.listdir(audio_dir)
    mp3_files = [f for f in files if f.endswith('.mp3')]
    print(f"\n✅ 音频目录存在，共 {len(mp3_files)} 个MP3文件")
    
    # 检查文件大小
    empty_files = []
    for f in mp3_files[:10]:  # 只检查前10个
        path = os.path.join(audio_dir, f)
        size = os.path.getsize(path)
        if size < 1000:  # 小于1KB可能是空文件
            empty_files.append((f, size))
    
    if empty_files:
        print(f"\n⚠️ 发现 {len(empty_files)} 个可能损坏的文件（小于1KB）:")
        for f, size in empty_files:
            print(f"   - {f}: {size} bytes")

# 2. 检查数据库
print("\n" + "-" * 50)
conn = get_db()
cursor = conn.cursor()

cursor.execute('SELECT id, audio_path, has_audio, audio_duration FROM sections')
sections = cursor.fetchall()

print(f"\n数据库共有 {len(sections)} 个节")

# 检查每个节的音频
missing_files = []
wrong_path = []
for s in sections:
    sid = s['id']
    path = s['audio_path']
    has_audio = s['has_audio']
    duration = s['audio_duration']
    
    if not path:
        missing_files.append(sid)
        continue
    
    # 检查路径格式
    if path.startswith('/api/audio/'):
        # 转换为实际文件路径
        real_path = path.replace('/api/audio/', 'audio_files/')
    elif path.startswith('audio_files/'):
        real_path = path
        wrong_path.append(sid)
    else:
        real_path = path
    
    # 检查文件是否存在
    if not os.path.exists(real_path):
        missing_files.append(sid)
    else:
        size = os.path.getsize(real_path)
        print(f"  节 {sid}: {path} ({size} bytes, {duration:.1f}s)")

if missing_files:
    print(f"\n❌ {len(missing_files)} 个节缺少音频文件: {missing_files[:5]}...")

if wrong_path:
    print(f"\n⚠️ {len(wrong_path)} 个节使用旧路径格式，需要修复")
    for sid in wrong_path:
        cursor.execute("UPDATE sections SET audio_path = '/api/audio/section_' || id || '.mp3' WHERE id = ?", (sid,))
    conn.commit()
    print("   已自动修复路径")

conn.close()

print("\n" + "=" * 50)
print("检查完成")
print("=" * 50)
