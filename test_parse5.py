"""
获取批注精确字符位置 v2
用法：python3 test_parse5.py <docx文件路径>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from lxml import etree

def get_precise_comment_ranges(file_path):
    doc = Document(file_path)
    
    print("=" * 60)
    print("获取批注精确字符位置 v2")
    print("=" * 60)
    
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    doc_xml = etree.fromstring(doc.part.blob)
    body = doc_xml.find('.//w:body', nsmap)
    
    # 先看看 commentRangeStart/End 到底在什么位置
    print("\n[调试] 搜索 commentRangeStart 在 body 中的位置:")
    for elem in body.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'commentRangeStart':
            cid = elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
            parent_tag = elem.getparent().tag.split('}')[-1] if '}' in elem.getparent().tag else elem.getparent().tag
            grandparent_tag = elem.getparent().getparent().tag.split('}')[-1] if '}' in elem.getparent().getparent().tag else elem.getparent().getparent().tag
            print(f"  commentRangeStart id={cid}, parent={parent_tag}, grandparent={grandparent_tag}")
            # 看看它在段落中的位置
            # 找到它所属的段落
            p = elem.getparent()
            while p is not None:
                ptag = p.tag.split('}')[-1] if '}' in p.tag else p.tag
                if ptag == 'p':
                    break
                p = p.getparent()
            if p is not None:
                # 计算在段落中的位置（在哪个 run 之前/之后）
                char_count = 0
                for child in p:
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if ctag == 'r':
                        for t in child.findall('.//w:t', nsmap):
                            if t.text:
                                char_count += len(t.text)
                    if child is elem:
                        print(f"    在段落内位置: 字符偏移={char_count}")
                        break
    
    print("\n[调试] 搜索 commentRangeEnd 在 body 中的位置:")
    for elem in body.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'commentRangeEnd':
            cid = elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
            parent_tag = elem.getparent().tag.split('}')[-1] if '}' in elem.getparent().tag else elem.getparent().tag
            grandparent_tag = elem.getparent().getparent().tag.split('}')[-1] if '}' in elem.getparent().getparent().tag else elem.getparent().getparent().tag
            print(f"  commentRangeEnd id={cid}, parent={parent_tag}, grandparent={grandparent_tag}")
            p = elem.getparent()
            while p is not None:
                ptag = p.tag.split('}')[-1] if '}' in p.tag else p.tag
                if ptag == 'p':
                    break
                p = p.getparent()
            if p is not None:
                char_count = 0
                for child in p:
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if ctag == 'r':
                        for t in child.findall('.//w:t', nsmap):
                            if t.text:
                                char_count += len(t.text)
                    if child is elem:
                        print(f"    在段落内位置: 字符偏移={char_count}")
                        break

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 test_parse5.py <docx文件路径>")
        sys.exit(1)
    get_precise_comment_ranges(sys.argv[1])
