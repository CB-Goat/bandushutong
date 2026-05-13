"""
检查服务器上的 text_parser.py 是否是最新版本
用法：python3 check_parser_version.py
"""
import os

# 检查关键代码是否存在于 text_parser.py 中
parser_path = 'backend/text_parser.py'
with open(parser_path, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('精确字符偏移', 'start_char_in_para'),
    ('commentRangeStart 作为 p 的直接子元素', "ctag == 'commentRangeStart'"),
    ('跳过 commentsExtended', "'commentsExtended' not in reltype"),
    ('精确提取原文', 'annotated_text = text[start_char_in_para:end_char_in_para]'),
]

print("=" * 50)
print("检查 text_parser.py 版本")
print("=" * 50)

all_ok = True
for name, pattern in checks:
    if pattern in content:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} - 缺失!")
        all_ok = False

if all_ok:
    print("\n✅ text_parser.py 是最新版本")
else:
    print("\n❌ text_parser.py 不是最新版本，需要 git pull")

# 检查数据库中是否有批注数据
print("\n" + "-" * 50)
print("检查数据库中的批注数据:")
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.database import get_db

conn = get_db()
cursor = conn.cursor()

# 检查 sections 中的 summary
cursor.execute('SELECT id, title, summary FROM sections ORDER BY id DESC LIMIT 5')
sections = cursor.fetchall()
print(f"\n最近5个节的小结:")
for s in sections:
    summary = s['summary'] or '(无)'
    print(f"  节 {s['id']} {s['title']}: {summary[:50]}")

# 检查 annotations 表
cursor.execute('SELECT COUNT(*) as cnt FROM annotations')
count = cursor.fetchone()['cnt']
print(f"\nannotations 表中共 {count} 条记录")

if count > 0:
    cursor.execute('SELECT * FROM annotations LIMIT 5')
    annos = cursor.fetchall()
    for a in annos:
        print(f"  批注: section={a['section_id']}, 原文=\"{a['original_text'][:30]}...\", 点评=\"{a['comment'][:30]}...\"")
else:
    print("  ❌ 没有批注数据！")

conn.close()
