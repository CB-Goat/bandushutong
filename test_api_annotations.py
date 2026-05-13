"""
测试 API 是否正确返回批注数据
用法：python3 test_api_annotations.py <book_id>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import get_db, get_sections_by_book, get_annotations_by_section

book_id = int(sys.argv[1]) if len(sys.argv) > 1 else 14

print("=" * 50)
print(f"测试书籍 {book_id} 的 API 响应")
print("=" * 50)

# 获取书籍的节
sections = get_sections_by_book(book_id)
print(f"\n共 {len(sections)} 个节")

for sec in sections:
    print(f"\n节 {sec['id']}: {sec['title']}")
    
    # 小结
    summary = sec.get('summary', '') or ''
    if summary:
        print(f"  小结: {summary[:60]}...")
    else:
        print(f"  小结: (无)")
    
    # 点评
    annotations = get_annotations_by_section(sec['id'])
    if annotations:
        print(f"  点评: {len(annotations)} 条")
        for a in annotations:
            print(f"    - 原文: \"{a['original_text'][:40]}...\"")
            print(f"      点评: \"{a['comment'][:40]}...\"")
    else:
        print(f"  点评: (无)")

print("\n" + "=" * 50)
