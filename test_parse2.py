"""
详细测试批注解析
用法：python3 test_parse2.py <docx文件路径>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT

def debug_parse(file_path):
    doc = Document(file_path)
    
    print("=" * 60)
    print("详细批注解析调试")
    print("=" * 60)
    
    # 1. 检查文档结构
    print("\n[1] 文档段落结构:")
    for i, para in enumerate(doc.paragraphs[:10]):
        style = para.style.name if para.style else 'Normal'
        text = para.text[:50] + "..." if len(para.text) > 50 else para.text
        print(f"  段落{i}: [{style}] {text}")
    
    # 2. 尝试获取批注部分
    print("\n[2] 尝试获取批注:")
    try:
        print(f"  doc.part type: {type(doc.part)}")
        print(f"  doc.part has rels: {hasattr(doc.part, 'rels')}")
        
        if hasattr(doc.part, 'rels'):
            print(f"  rels count: {len(doc.part.rels)}")
            for rel in doc.part.rels.values():
                print(f"    reltype: {rel.reltype}")
                if 'comments' in str(rel.reltype).lower():
                    print(f"    -> 找到批注关系!")
                    comments_part = rel.target_part
                    print(f"    comments_part type: {type(comments_part)}")
                    if hasattr(comments_part, 'blob'):
                        print(f"    blob length: {len(comments_part.blob)}")
                    break
        
        # 尝试另一种方式
        print("\n[3] 尝试直接访问 comments.xml:")
        package = doc.part.package
        print(f"  package type: {type(package)}")
        
        # 列出所有 parts
        print("\n[4] 文档中的所有 parts:")
        for part_name in package.parts:
            print(f"    {part_name}")
            
    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 test_parse2.py <docx文件路径>")
        sys.exit(1)
    
    debug_parse(sys.argv[1])
