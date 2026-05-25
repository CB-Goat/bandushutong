"""
Word 结构优先解析器
专门处理 Word 文档，精确提取：
- 书名（Heading 1）
- 作者、国籍、版本（书名后的 Normal 段落）
- 章（Heading 2）
- 节（Heading 3）
- 批注（对标题的批注=小结，对正文的批注=点评）
"""
from docx import Document
from lxml import etree
import re


class WordStructureParser:
    """Word 文档结构解析器"""
    
    # Word 命名空间
    W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    
    def __init__(self, file_path):
        self.doc = Document(file_path)
        self.paragraphs = list(self.doc.paragraphs)
        self.nsmap = {'w': self.W_NS}
        
    def parse(self):
        """解析整个文档"""
        # 1. 提取元信息
        meta = self._extract_metadata()
        
        # 2. 提取批注信息
        comments = self._extract_comments()
        comment_ranges = self._extract_comment_ranges()
        
        # 3. 构建章节结构
        chapters, sections = self._build_structure(comments, comment_ranges)
        
        return {
            'title': meta['title'],
            'author': meta['author'],
            'author_nationality': meta['nationality'],
            'version': meta['version'],
            'chapters': chapters,
            'sections': sections
        }
    
    def _extract_metadata(self):
        """
        提取文档元信息：
        - 书名：Heading 1
        - 作者/国籍：书名后的第一个 Normal 段落
        - 版本：书名后的第二个 Normal 段落
        """
        meta = {
            'title': '未命名',
            'author': '',
            'nationality': '',
            'version': ''
        }
        
        # 查找第一个 Heading 1 作为书名
        for para in self.paragraphs:
            style = para.style.name if para.style else 'Normal'
            if style == 'Heading 1':
                meta['title'] = para.text.strip()
                break
        
        # 查找书名后的段落作为作者/版本
        found_title = False
        normal_count = 0
        for para in self.paragraphs:
            style = para.style.name if para.style else 'Normal'
            text = para.text.strip()
            
            if style == 'Heading 1':
                found_title = True
                continue
            
            if not found_title:
                continue
            
            # 支持自定义样式 [作者] 和 [版本]
            if style == '[作者]' or style == '作者':
                # 只取第一个 [作者] 段落
                if meta.get('author'):
                    continue
                if '「' in text and '」' in text:
                    parts = text.split('「')
                    meta['author'] = parts[0].strip()
                    meta['nationality'] = parts[1].split('」')[0].strip()
                elif '[' in text and ']' in text:
                    parts = text.split('[')
                    meta['author'] = parts[0].strip()
                    meta['nationality'] = parts[1].split(']')[0].strip()
                elif '（' in text and '）' in text:
                    parts = text.split('（')
                    meta['author'] = parts[0].strip()
                    meta['nationality'] = parts[1].split('）')[0].strip()
                else:
                    # 如果作者行没有格式，尝试从文本中解析
                    meta['author'] = text
                    # 尝试匹配 高尔基「苏联」 格式
                    import re
                    match = re.search(r'(.+?)「(.+?)」', text)
                    if match:
                        meta['author'] = match.group(1).strip()
                        meta['nationality'] = match.group(2).strip()
                    match = re.search(r'(.+?)\[(.+?)\]', text)
                    if match:
                        meta['author'] = match.group(1).strip()
                        meta['nationality'] = match.group(2).strip()
                    match = re.search(r'(.+?)（(.+?)）', text)
                    if match:
                        meta['author'] = match.group(1).strip()
                        meta['nationality'] = match.group(2).strip()
                continue
            
            if style == '[版本]' or style == '版本':
                # 只取第一个 [版本] 段落
                if meta.get('version'):
                    continue
                meta['version'] = text
                continue
            
            # 处理 Normal 样式作为备用（仅当未通过 [作者]/[版本] 样式获取时）
            if style == 'Normal' and text:
                normal_count += 1
                if normal_count == 1 and not meta.get('author'):
                    # 第一行：作者「国籍」
                    if '「' in text and '」' in text:
                        parts = text.split('「')
                        meta['author'] = parts[0].strip()
                        meta['nationality'] = parts[1].split('」')[0].strip()
                    elif '[' in text and ']' in text:
                        parts = text.split('[')
                        meta['author'] = parts[0].strip()
                        meta['nationality'] = parts[1].split(']')[0].strip()
                    elif '（' in text and '）' in text:
                        parts = text.split('（')
                        meta['author'] = parts[0].strip()
                        meta['nationality'] = parts[1].split('）')[0].strip()
                    else:
                        meta['author'] = text
                elif normal_count == 2 and not meta.get('version'):
                    # 第二行：版本
                    meta['version'] = text
                    break
        
        return meta
    
    def _extract_comments(self):
        """提取所有批注内容"""
        comments = {}
        
        for rel in self.doc.part.rels.values():
            reltype = str(rel.reltype)
            if reltype.endswith('/comments') and 'commentsExtended' not in reltype:
                comments_part = rel.target_part
                root = etree.fromstring(comments_part.blob)
                
                for comment in root.findall('.//w:comment', self.nsmap):
                    cid = comment.get(f'{{{self.W_NS}}}id')
                    author = comment.get(f'{{{self.W_NS}}}author', '')
                    
                    texts = []
                    for p in comment.findall('.//w:p', self.nsmap):
                        for t in p.findall('.//w:t', self.nsmap):
                            if t.text:
                                texts.append(t.text)
                    text = ''.join(texts).strip()
                    
                    comments[cid] = {
                        'id': cid,
                        'author': author,
                        'text': text
                    }
        
        return comments
    
    def _extract_comment_ranges(self):
        """提取批注引用范围"""
        comment_ranges = {}
        
        for para_idx, para in enumerate(self.paragraphs):
            para_element = para._element
            char_offset = 0
            
            for child in para_element:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                
                if tag == 'commentRangeStart':
                    cid = child.get(f'{{{self.W_NS}}}id')
                    if cid and cid not in comment_ranges:
                        comment_ranges[cid] = {
                            'start_para': para_idx,
                            'start_char': char_offset,
                            'end_para': para_idx,
                            'end_char': char_offset
                        }
                
                elif tag == 'commentRangeEnd':
                    cid = child.get(f'{{{self.W_NS}}}id')
                    if cid and cid in comment_ranges:
                        comment_ranges[cid]['end_para'] = para_idx
                        comment_ranges[cid]['end_char'] = char_offset
                
                elif tag == 'r':
                    # 计算该 run 中的所有字符（包括文本和TAB等特殊字符）
                    for elem in child.iter():
                        elem_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        if elem_tag == 't' and elem.text:
                            char_offset += len(elem.text)
                        elif elem_tag == 'tab':
                            # TAB 字符也算一个字符
                            char_offset += 1
        
        return comment_ranges
    
    def _extract_number(self, text):
        """从标题文本中提取序号，如 '第一章' -> 1, '1. 标题' -> 1, '第3节' -> 3, '第一篇' -> 1"""
        # 匹配 "第X章"、"第X节"、"第X回"、"第X篇" 等中文序号
        match = re.search(r'第\s*(\d+)\s*[章节回篇]', text)
        if match:
            return int(match.group(1))
        # 匹配 "1."、"1、"、"1 " 开头的数字序号
        match = re.match(r'^\s*(\d+)\s*[.．、\s]', text)
        if match:
            return int(match.group(1))
        # 匹配纯数字开头
        match = re.match(r'^\s*(\d+)\s*', text)
        if match:
            return int(match.group(1))
        return None

    def _build_structure(self, comments, comment_ranges):
        """
        构建章节结构：
        - Heading 2 = 章
        - Heading 3 = 节（阅读单元）
        - 如果只有 Heading 2 没有 Heading 3，则 Heading 2 作为节
        - 序号从 Word 标题文本中解析，解析失败时使用自增序号
        """
        chapters = []
        sections = []
        chapter_number = 0
        section_number = 0
        current_chapter_title = None
        
        # 先检查是否有 Heading 3
        has_h3 = self._has_heading3()
        print(f"[Parser] 文档是否有 Heading 3: {has_h3}")
        
        for para_idx, para in enumerate(self.paragraphs):
            style = para.style.name if para.style else 'Normal'
            text = para.text.strip()
            
            if not text:
                continue
            
            if style == 'Heading 1':
                # 书名，跳过
                continue
            
            elif style == 'Heading 2':
                # 从标题中提取序号，失败则自增
                extracted_num = self._extract_number(text)
                if extracted_num:
                    chapter_number = extracted_num
                else:
                    chapter_number += 1
                
                if has_h3:
                    # 有 Heading 3 时，Heading 2 是章
                    current_chapter_title = text
                    chapters.append({
                        'chapter_number': chapter_number,
                        'title': text
                    })
                    print(f"[Parser] 章 {chapter_number}: {text}")
                else:
                    # 没有 Heading 3 时，Heading 2 是节
                    section = self._create_section(
                        section_number=chapter_number,
                        chapter_number=None,
                        title=text,
                        para_idx=para_idx,
                        comments=comments,
                        comment_ranges=comment_ranges
                    )
                    sections.append(section)
            
            elif style == 'Heading 3':
                # 节标题，从标题中提取序号
                extracted_num = self._extract_number(text)
                if extracted_num:
                    section_number = extracted_num
                else:
                    section_number += 1
                
                section = self._create_section(
                    section_number=section_number,
                    chapter_number=chapter_number if has_h3 else None,
                    title=text,
                    para_idx=para_idx,
                    comments=comments,
                    comment_ranges=comment_ranges
                )
                sections.append(section)
        
        return chapters, sections
    
    def _has_heading3(self):
        """检查文档是否有 Heading 3 样式"""
        for para in self.paragraphs:
            style = para.style.name if para.style else 'Normal'
            if style == 'Heading 3':
                return True
        return False
    
    def _create_section(self, section_number, chapter_number, title, para_idx, comments, comment_ranges):
        """创建一个节"""
        section = {
            'section_number': section_number,
            'chapter_number': chapter_number,
            'title': title,
            'content': '',
            'summary': None,
            'annotations': []
        }
        
        print(f"[Parser] 节 {section_number}: {title}")
        
        # 检查节标题是否有批注（小结）
        for cid, rng in comment_ranges.items():
            if rng['start_para'] == para_idx and cid in comments:
                section['summary'] = comments[cid]['text']
                print(f"[Parser]   小结: {section['summary'][:40]}...")
        
        # 收集后续正文段落（不过滤空段落，与前端一致）
        content_start = None
        for i in range(para_idx + 1, len(self.paragraphs)):
            para = self.paragraphs[i]
            style = para.style.name if para.style else 'Normal'
            text = para.text or ''  # 空段落也保留
            
            if style in ['Heading 1', 'Heading 2', 'Heading 3']:
                break
            
            if section['content']:
                section['content'] += '\n' + text
            else:
                section['content'] = text
                content_start = i
        
        # 收集正文批注（点评）
        if content_start is not None:
            content_char_offset = 0
            for i in range(content_start, len(self.paragraphs)):
                para = self.paragraphs[i]
                style = para.style.name if para.style else 'Normal'
                
                if style in ['Heading 1', 'Heading 2', 'Heading 3']:
                    break
                
                # 使用与 _extract_comment_ranges 一致的字符计算方式
                para_char_count = self._count_para_chars(para)
                
                for cid, rng in comment_ranges.items():
                    if rng['start_para'] == i and cid in comments:
                        original_text = self._get_original_text(rng)
                        abs_start = content_char_offset + rng['start_char']
                        abs_end = content_char_offset + rng['end_char']
                        
                        annotation = {
                            'original_text': original_text,
                            'comment': comments[cid]['text'],
                            'start_char': abs_start,
                            'end_char': abs_end
                        }
                        section['annotations'].append(annotation)
                        print(f"[Parser]   点评: \"{original_text[:30]}...\" (pos:{abs_start}-{abs_end})")
                
                content_char_offset += para_char_count
        
        return section
    
    def _count_para_chars(self, para):
        """计算段落中的字符数（与 _extract_comment_ranges 中的计算方式一致）"""
        char_count = 0
        para_element = para._element
        for child in para_element:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'r':
                for elem in child.iter():
                    elem_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if elem_tag == 't' and elem.text:
                        char_count += len(elem.text)
                    elif elem_tag == 'tab':
                        char_count += 1
        return char_count
    
    def _get_original_text(self, rng):
        """根据批注范围提取引用的原文"""
        if rng['start_para'] == rng['end_para']:
            para_text = self.paragraphs[rng['start_para']].text
            return para_text[rng['start_char']:rng['end_char']]
        else:
            para_text = self.paragraphs[rng['start_para']].text
            return para_text[rng['start_char']:]


def parse_file(file_path):
    """解析 Word 文件的入口函数"""
    parser = WordStructureParser(file_path)
    return parser.parse()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 word_parser.py <docx文件路径>")
        sys.exit(1)
    
    result = parse_file(sys.argv[1])
    
    print("=" * 60)
    print(f"书名: {result['title']}")
    print(f"作者: {result['author']}")
    print(f"国籍: {result['author_nationality']}")
    print(f"版本: {result['version']}")
    print(f"章数: {len(result['chapters'])}")
    print(f"节数: {len(result['sections'])}")
    print("=" * 60)
    
    for ch in result['chapters'][:3]:
        print(f"\n章 {ch['chapter_number']}: {ch['title']}")
        ch_sections = [s for s in result['sections'] if s.get('chapter_number') == ch['chapter_number']]
        for sec in ch_sections:
            print(f"  节 {sec['section_number']}: {sec['title']}")
            if sec['summary']:
                print(f"    小结: {sec['summary'][:30]}...")
    
    if not result['chapters']:
        print("\n无章结构，直接显示节:")
        for sec in result['sections'][:3]:
            print(f"\n节 {sec['section_number']}: {sec['title']}")
            if sec['summary']:
                print(f"  小结: {sec['summary'][:30]}...")
            print(f"  点评: {len(sec['annotations'])} 条")
