"""
Word 结构优先解析器
专门处理 Word 文档，精确提取：
- 标题结构（Heading 1/2）
- 正文内容
- 批注（对标题的批注=小结，对正文的批注=点评）
- 批注引用的精确字符范围
"""
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree


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
        # 1. 提取文档元信息
        meta = self._extract_metadata()
        
        # 2. 构建段落结构
        para_data = self._extract_paragraph_data()
        
        # 3. 提取批注信息
        comments = self._extract_comments()
        
        # 4. 提取批注范围（注释引用位置）
        comment_ranges = self._extract_comment_ranges()
        
        # 5. 构建节结构
        sections = self._build_sections(para_data, comments, comment_ranges)
        
        return {
            'title': meta['title'],
            'author': meta['author'],
            'sections': sections
        }
    
    def _extract_metadata(self):
        """提取文档元信息"""
        core_props = self.doc.core_properties
        return {
            'title': core_props.title or '未命名',
            'author': core_props.author or '未知作者'
        }
    
    def _extract_paragraph_data(self):
        """
        提取每个段落的详细信息：
        - 索引（在 doc.paragraphs 中的位置）
        - 样式名
        - 文本内容
        - 字符位置（起始位置）
        """
        para_data = []
        char_offset = 0
        
        for idx, para in enumerate(self.paragraphs):
            text = para.text
            style_name = para.style.name if para.style else 'Normal'
            
            para_data.append({
                'index': idx,
                'style': style_name,
                'text': text,
                'char_start': char_offset,
                'char_end': char_offset + len(text)
            })
            
            char_offset += len(text) + 1  # +1 for paragraph break
        
        return para_data
    
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
                    
                    # 提取批注文本
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
        """
        提取批注引用范围（注释在文档中的位置）
        返回: {comment_id: {'start': (para_idx, char_offset), 'end': (para_idx, char_offset)}}
        """
        comment_ranges = {}
        
        for para_idx, para in enumerate(self.paragraphs):
            para_element = para._element
            
            # 计算段内字符偏移
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
                    # 累加文本长度
                    for t in child.findall('.//w:t', self.nsmap):
                        if t.text:
                            char_offset += len(t.text)
        
        return comment_ranges
    
    def _build_sections(self, para_data, comments, comment_ranges):
        """
        构建节结构：
        - Heading 2 = 节标题
        - 节标题后的 Normal 段落 = 节正文
        - 对节标题的批注 = 小结
        - 对正文的批注 = 点评
        """
        sections = []
        current_section = None
        
        for pd in para_data:
            style = pd['style']
            text = pd['text']
            para_idx = pd['index']
            
            if style == 'Heading 1':
                # 书籍标题，跳过
                continue
            
            elif style == 'Heading 2':
                # 保存上一个节
                if current_section:
                    sections.append(current_section)
                
                # 开始新节，记录标题段落索引
                current_section = {
                    'title': text.strip(),
                    'content': '',
                    'summary': None,
                    'annotations': [],
                    '_title_para': para_idx,  # 记录标题段落索引
                    '_content_start': 0
                }
                print(f"[Parser] 新节: {current_section['title']} (标题段落={para_idx})")
                
                # 检查标题段落是否有批注（这是小结）
                for cid, rng in comment_ranges.items():
                    if rng['start_para'] == para_idx:
                        if cid in comments:
                            comment = comments[cid]
                            current_section['summary'] = comment['text']
                            print(f"[Parser] 节 '{current_section['title']}' 小结: {comment['text'][:40]}...")
            
            elif current_section is not None:
                # 节内的正文段落
                if current_section['content']:
                    current_section['content'] += '\n' + text
                else:
                    current_section['content'] = text
                    # 记录内容在文档中的起始位置
                    current_section['_content_start'] = pd['char_start']
                
                # 检查该段落是否有批注
                for cid, rng in comment_ranges.items():
                    if rng['start_para'] == para_idx:
                        if cid in comments:
                            comment = comments[cid]
                            comment_text = comment['text']
                            original_text = self._get_original_text(rng, para_data)
                            
                            # 判断是小结还是点评
                            # 如果该节还没有小结，且批注附加在标题段落，则是小结
                            if not current_section['summary'] and para_idx == current_section['_title_para']:
                                current_section['summary'] = comment_text
                                print(f"[Parser] 节 '{current_section['title']}' 小结: {comment_text[:40]}...")
                            else:
                                # 作为点评
                                # 计算在节内容中的字符位置
                                content_start = current_section['_content_start']
                                para_start_in_content = pd['char_start'] - content_start
                                
                                abs_start = para_start_in_content + rng['start_char']
                                abs_end = para_start_in_content + rng['end_char']
                                
                                annotation = {
                                    'original_text': original_text,
                                    'comment': comment_text,
                                    'start_char': abs_start,
                                    'end_char': abs_end
                                }
                                current_section['annotations'].append(annotation)
                                print(f"[Parser] 节 '{current_section['title']}' 点评: \"{original_text[:30]}...\"")
        
        # 保存最后一个节
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _get_original_text(self, rng, para_data):
        """根据批注范围提取引用的原文"""
        if rng['start_para'] == rng['end_para']:
            # 同一段落内
            para_text = para_data[rng['start_para']]['text']
            return para_text[rng['start_char']:rng['end_char']]
        else:
            # 跨段落（暂不处理）
            return para_data[rng['start_para']]['text'][rng['start_char']:]


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
    print(f"节数: {len(result['sections'])}")
    print("=" * 60)
    
    for sec in result['sections'][:3]:
        print(f"\n节: {sec['title']}")
        print(f"  小结: {sec['summary'][:50] if sec['summary'] else '(无)'}...")
        print(f"  点评: {len(sec['annotations'])} 条")
        for a in sec['annotations']:
            print(f"    - \"{a['original_text'][:30]}...\"")
