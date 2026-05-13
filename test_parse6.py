"""
精确调试批注字符位置
用法：python3 test_parse6.py <docx文件路径>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from lxml import etree

def debug_precise(file_path):
    doc = Document(file_path)
    
    print("=" * 60)
    print("精确调试批注字符位置")
    print("=" * 60)
    
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    doc_xml = etree.fromstring(doc.part.blob)
    body = doc_xml.find('.//w:body', nsmap)
    
    # 获取所有段落文本
    paragraphs = []
    for para in body.findall('.//w:p', nsmap):
        texts = [t.text for t in para.findall('.//w:t', nsmap) if t.text]
        para_text = ''.join(texts)
        paragraphs.append(para_text)
    
    comment_ranges = {}
    
    # 遍历每个段落
    para_idx = 0
    for para in body.findall('.//w:p', nsmap):
        para_text = paragraphs[para_idx]
        
        # 详细遍历段落中的每个元素
        char_offset = 0
        for child in para:
            ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            if ctag == 'commentRangeStart':
                cid = child.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid:
                    comment_ranges[cid] = {
                        'start_para': para_idx,
                        'start_char': char_offset,
                        'end_para': para_idx,
                        'end_char': char_offset
                    }
                    print(f"\n段落[{para_idx}] commentRangeStart id={cid}, char_offset={char_offset}")
                    print(f"  段落文本: {para_text[:60]}...")
                    print(f"  从偏移{char_offset}开始: \"{para_text[char_offset:char_offset+40]}...\"")
            
            elif ctag == 'commentRangeEnd':
                cid = child.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid and cid in comment_ranges:
                    comment_ranges[cid]['end_para'] = para_idx
                    comment_ranges[cid]['end_char'] = char_offset
                    print(f"\n段落[{para_idx}] commentRangeEnd id={cid}, char_offset={char_offset}")
                    start = comment_ranges[cid]['start_char']
                    print(f"  引用范围: [{start}:{char_offset}]")
                    print(f"  引用文本: \"{para_text[start:char_offset]}\"")
            
            elif ctag == 'r':
                # 累加 run 中文本的长度
                for t in child.findall('.//w:t', nsmap):
                    if t.text:
                        char_offset += len(t.text)
        
        para_idx += 1
    
    print("\n" + "=" * 60)
    print("批注汇总:")
    print("=" * 60)
    
    # 获取批注文本
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
                    para_text = paragraphs[para_idx]
                    
                    print(f"\n批注 ID={cid}:")
                    print(f"  批注内容: {comment_text[:60]}...")
                    print(f"  段落[{para_idx}], 字符[{start_char}:{end_char}]")
                    print(f"  引用原文: \"{para_text[start_char:end_char]}\"")
            break

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 test_parse6.py <docx文件路径>")
        sys.exit(1)
    debug_precise(sys.argv[1])
