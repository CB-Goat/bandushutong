"""
获取批注的精确字符位置
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
    print("获取批注精确字符位置")
    print("=" * 60)
    
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    doc_xml = etree.fromstring(doc.part.blob)
    body = doc_xml.find('.//w:body', nsmap)
    
    # 解析所有段落，记录每个段落的文本和字符位置
    paragraphs = []
    for para in body.findall('.//w:p', nsmap):
        texts = []
        for t in para.findall('.//w:t', nsmap):
            if t.text:
                texts.append(t.text)
        para_text = ''.join(texts)
        paragraphs.append(para_text)
    
    print(f"\n共 {len(paragraphs)} 个段落")
    for i, p in enumerate(paragraphs[:10]):
        print(f"  [{i}]: {p[:60]}...")
    
    # 解析 commentRangeStart/End 的精确位置
    print("\n" + "-" * 60)
    print("批注精确位置:")
    
    comment_ranges = {}
    
    # 遍历所有段落，查找 commentRangeStart/End
    for para_idx, para in enumerate(body.findall('.//w:p', nsmap)):
        # 获取段落的完整文本用于计算偏移
        texts = []
        text_elements = []  # 记录每个 w:t 元素及其位置
        
        # 遍历段落中的所有 run
        char_offset = 0
        for run in para.findall('.//w:r', nsmap):
            # 检查是否有 commentRangeStart
            for start in run.findall('.//w:commentRangeStart', nsmap):
                cid = start.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid:
                    comment_ranges[cid] = {
                        'start_para': para_idx,
                        'start_char': char_offset,
                        'end_para': para_idx,
                        'end_char': char_offset
                    }
                    print(f"  RangeStart: ID={cid}, 段落={para_idx}, 字符={char_offset}")
            
            # 检查是否有 commentRangeEnd
            for end in run.findall('.//w:commentRangeEnd', nsmap):
                cid = end.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid and cid in comment_ranges:
                    comment_ranges[cid]['end_para'] = para_idx
                    comment_ranges[cid]['end_char'] = char_offset
                    print(f"  RangeEnd: ID={cid}, 段落={para_idx}, 字符={char_offset}")
            
            # 累加文本长度
            for t in run.findall('.//w:t', nsmap):
                if t.text:
                    char_offset += len(t.text)
    
    # 获取批注文本
    print("\n" + "-" * 60)
    print("批注关联结果:")
    
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
                    print(f"\n  批注 ID={cid}:")
                    print(f"    内容: {comment_text[:60]}...")
                    print(f"    范围: 段落[{rng['start_para']}]:{rng['start_char']} ~ 段落[{rng['end_para']}]:{rng['end_char']}")
                    
                    # 提取原文
                    if rng['start_para'] == rng['end_para']:
                        # 同一段落
                        original = paragraphs[rng['start_para']][rng['start_char']:rng['end_char']]
                    else:
                        # 跨段落
                        parts = []
                        parts.append(paragraphs[rng['start_para']][rng['start_char']:])
                        for pi in range(rng['start_para']+1, rng['end_para']):
                            parts.append(paragraphs[pi])
                        parts.append(paragraphs[rng['end_para']][:rng['end_char']])
                        original = '\n'.join(parts)
                    
                    print(f"    原文: {original[:60]}...")
            break

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 test_parse5.py <docx文件路径>")
        sys.exit(1)
    get_precise_comment_ranges(sys.argv[1])
