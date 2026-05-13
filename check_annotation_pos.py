"""
检查数据库中批注的字符位置
用法：python3 check_annotation_pos.py <section_id>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db, get_sections_by_book

section_id = int(sys.argv[1]) if len(sys.argv) > 1 else 353

conn = get_db()
cursor = conn.cursor()

# 获取节内容和批注
cursor.execute('SELECT id, title, content, summary FROM sections WHERE id = ?', (section_id,))
section = cursor.fetchone()

if not section:
    print(f"节 {section_id} 不存在")
    sys.exit(1)

content = section['content'] or ''
print(f"节 {section_id}: {section['title']}")
print(f"内容长度: {len(content)} 字符")
print(f"小结: {section['summary'][:50] if section['summary'] else '(无)'}...")

# 获取批注
cursor.execute('SELECT * FROM annotations WHERE section_id = ?', (section_id,))
annotations = cursor.fetchall()

print(f"\n批注数量: {len(annotations)}")
for a in annotations:
    start = a['start_char']
    end = a['end_char']
    print(f"\n批注 ID={a['id']}:")
    print(f"  start_char={start}, end_char={end}")
    print(f"  原文: \"{content[start:end]}\"")
    print(f"  点评: \"{a['comment'][:50]}...\"")
    
    # 显示前后文
    context_start = max(0, start - 20)
    context_end = min(len(content), end + 20)
    print(f"  上下文: \"...{content[context_start:context_end]}...\"")

conn.close()
