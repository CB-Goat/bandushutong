"""
测试书籍解析，检查批注是否正确提取
用法：python3 test_parse.py <docx文件路径>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.text_parser import parse_file

if len(sys.argv) < 2:
    print("用法: python3 test_parse.py <docx文件路径>")
    sys.exit(1)

file_path = sys.argv[1]
if not os.path.exists(file_path):
    print(f"文件不存在: {file_path}")
    sys.exit(1)

print("=" * 60)
print("测试书籍解析")
print("=" * 60)

result = parse_file(file_path)

print(f"\n书名: {result['title']}")
print(f"作者: {result['author']}")
print(f"章数: {len(result['chapters'])}")
print(f"节数: {len(result['sections'])}")

print("\n" + "-" * 60)
print("各节的小结和点评:")
print("-" * 60)

for sec in result['sections']:
    print(f"\n第{sec['section_number']}节: {sec['title']}")
    print(f"  内容长度: {len(sec['content'])} 字")
    
    summary = sec.get('summary', '')
    if summary:
        print(f"  小结: {summary[:100]}...")
    else:
        print(f"  小结: (无)")
    
    annotations = sec.get('annotations', [])
    if annotations:
        print(f"  点评数量: {len(annotations)}")
        for idx, anno in enumerate(annotations[:3]):  # 只显示前3个
            print(f"    点评{idx+1}: {anno['comment'][:50]}...")
            print(f"      原文: {anno['original_text'][:30]}...")
    else:
        print(f"  点评: (无)")

print("\n" + "=" * 60)
