"""
调试批注解析过程
用法：python3 test_parse_debug.py <docx文件路径>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from lxml import etree

def debug_parse(file_path):
    doc = Document(file_path)
    
    print("=" * 60)
    print("调试批注解析")
    print("=" * 60)
    
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    doc_xml = etree.fromstring(doc.part.blob)
    body = doc_xml.find('.//w:body', nsmap)
    
    # 获取所有段落文本和批注范围
    paragraphs = []
    comment_ranges = {}
    
    para_idx = 0
    for para in body.findall('.//w:p', nsmap):
        # 提取段落文本
        texts = []
        char_offset = 0
        for child in para:
            ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            if ctag == 'commentRangeStart':
                cid = child.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid:
                    comment_ranges[cid] = {
                        'start_para': para_idx,
                        'start_char': char_offset
                    }
            
            elif ctag == 'commentRangeEnd':
                cid = child.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid and cid in comment_ranges:
                    comment_ranges[cid]['end_para'] = para_idx
                    comment_ranges[cid]['end_char'] = char_offset
            
            elif ctag == 'r':
                for t in child.findall('.//w:t', nsmap):
                    if t.text:
                        texts.append(t.text)
                        char_offset += len(t.text)
        
        para_text = ''.join(texts)
        paragraphs.append(para_text)
        para_idx += 1
    
    # 打印所有段落（带索引）
    print("\n[段落列表]:")
    for i, p in enumerate(paragraphs):
        print(f"  [{i}]: {p[:60]}...")
    
    # 获取批注文本
    print("\n[批注解析]:")
    for rel in doc.part.rels.values():
        reltype = str(rel.reltype)
        if reltype.endswith('/comments') and 'commentsExtended' not in reltype:
            comments_part = rel.target_part
            root = etree.fromstring(comments_part.blob)
            for comment in root.findall('.//w:comment', nsmap):
                cid = comment.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                texts = []
                for p in comment.findall('.//w:p', nsmap):
                    t = [x.text for x in p.findall('.//w:t', nsmap) if x.text]
                    texts.append(''.join(t))
                comment_text = '\n'.join(texts).strip()
                
                if cid in comment_ranges:
                    rng = comment_ranges[cid]
                    para_idx = rng['start_para']
                    start_char = rng['start_char']
                    end_char = rng['end_char']
                    
                    print(f"\n  批注 ID={cid}:")
                    print(f"    段落={para_idx}, 字符范围=[{start_char}:{end_char}]")
                    print(f"    段落文本: \"{paragraphs[para_idx][:80]}...\"")
                    print(f"    引用原文: \"{paragraphs[para_idx][start_char:end_char]}\"")
                    print(f"    批注内容: \"{comment_text[:50]}...\"")
            break
    
    # 模拟 content 构建过程
    print("\n[模拟 content 构建]:")
    content = ""
    for i, p in enumerate(paragraphs):
        para_start = len(content)
        if content:
            para_start += 1  # '\n'
            content += '\n' + p
        else:
            content = p
        print(f"  段落[{i}]: content_start={para_start}, text_len={len(p)}")
        if i == 7:  # 第7段（母亲跪在他身边...）
            print(f"    内容: \"{p}\"")
            print(f"    在content中的位置: [{para_start}:{para_start+len(p)}]")
            print(f"    content[para_start:para_start+10] = \"{content[para_start:para_start+10]}\"")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 test_parse_debug.py <docx文件路径>")
        sys.exit(1)
    debug_parse(sys.argv[1])
