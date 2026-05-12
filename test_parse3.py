"""
检查批注XML的实际结构
用法：python3 test_parse3.py <docx文件路径>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document

def debug_comments(file_path):
    doc = Document(file_path)
    
    print("=" * 60)
    print("检查批注XML结构")
    print("=" * 60)
    
    # 找到批注部分
    comments_part = None
    for rel in doc.part.rels.values():
        if 'comments' in str(rel.reltype).lower():
            comments_part = rel.target_part
            print(f"\n批注关系类型: {rel.reltype}")
            break
    
    if not comments_part:
        print("未找到批注部分")
        return
    
    # 打印原始XML内容
    print(f"\n批注XML内容 (前3000字符):")
    xml_content = comments_part.blob.decode('utf-8', errors='ignore')
    print(xml_content[:3000])
    
    # 尝试用 lxml 解析
    print("\n" + "-" * 60)
    print("尝试解析XML:")
    from lxml import etree
    
    try:
        root = etree.fromstring(comments_part.blob)
        
        # 打印根元素
        print(f"根元素: {root.tag}")
        
        # 定义所有可能的命名空间
        nsmap = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
            'w15': 'http://schemas.microsoft.com/office/word/2012/wordml',
        }
        
        # 查找所有可能的批注元素
        for ns_name, ns_uri in nsmap.items():
            elems = root.findall(f'.//{ns_name}:comment', {ns_name: ns_uri})
            if elems:
                print(f"\n使用命名空间 {ns_name} ({ns_uri}) 找到 {len(elems)} 个批注")
                for i, elem in enumerate(elems[:2]):
                    print(f"  批注{i+1} ID: {elem.get('id')}")
                    # 提取文本
                    texts = elem.xpath('.//text()', namespaces={ns_name: ns_uri})
                    text = ''.join(texts).strip()[:100]
                    print(f"    内容: {text}...")
        
        # 如果没有找到，打印所有元素标签
        print("\n文档中所有元素标签:")
        all_tags = set()
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            all_tags.add(tag)
        for tag in sorted(all_tags)[:20]:
            print(f"  - {tag}")
            
    except Exception as e:
        print(f"解析错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 test_parse3.py <docx文件路径>")
        sys.exit(1)
    
    debug_comments(sys.argv[1])
