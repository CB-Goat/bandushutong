"""
修复数据库中音频路径为完整URL
用法：python3 fix_audio_path.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db

conn = get_db()
cursor = conn.cursor()

# 查询所有有音频路径的节
cursor.execute('SELECT id, audio_path FROM sections WHERE audio_path IS NOT NULL AND audio_path != ""')
sections = cursor.fetchall()

fixed = 0
for s in sections:
    sid = s['id']
    old_path = s['audio_path']
    
    # 如果是相对路径，修复为完整URL
    if old_path.startswith('audio_files/'):
        new_path = old_path.replace('audio_files/', '/api/audio/')
        cursor.execute('UPDATE sections SET audio_path = ? WHERE id = ?', (new_path, sid))
        fixed += 1
        print(f"修复节 {sid}: {old_path} -> {new_path}")

conn.commit()
conn.close()

print(f"\n共修复 {fixed} 个节的音频路径")
