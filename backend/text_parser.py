"""
伴读书童 - 文本解析模块
将 TXT / DOCX 文件解析为章节和小节

Word 文件结构约定：
  - Heading 1: 书名（第一个）
  - Normal: 作者「国籍」（第二个段落）
  - Normal: 版本信息（第三个段落）
  - Heading 1: 章标题（后续出现的，可选）
  - Heading 2: 节标题（第X节 节名）
  - Normal: 节正文内容
"""

import re
import os


def parse_file(file_path):
    """
    根据文件扩展名自动选择解析方式
    支持 .txt 和 .docx 格式

    返回字典：
    {
        'title': 书名,
        'author': 作者,
        'author_nationality': 国籍,
        'version': 版本,
        'chapters': [{'chapter_number': 1, 'title': '...', 'sections': [...]}],
        'sections': [{'section_number': 1, 'title': '...', 'content': '...', 'chapter_number': None}]
    }
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.docx':
        return parse_docx_file(file_path)
    else:
        return parse_txt_file(file_path)


def parse_docx_file(file_path):
    """
    解析 Word (.docx) 文件

    结构约定：
    - 第1个 Heading 1 = 书名
    - 第2个段落(Normal) = 作者「国籍」
    - 第3个段落(Normal) = 版本
    - 后续 Heading 1 = 章标题（可选）
    - Heading 2 = 节标题
    - Normal = 节正文
    """
    from docx import Document

    doc = Document(file_path)

    # 收集所有段落（带样式信息）
    all_paras = []
    for para in doc.paragraphs:
        text = para.text.strip()
        style = para.style.name if para.style else 'Normal'
        all_paras.append({'text': text, 'style': style})

    # 收集批注（comments）
    # Word批注结构：对某一节标题的批注 = 小结；对节正文的批注 = 点评
    comments = []
    try:
        # 尝试多种方式获取批注
        comments_part = None
        
        # 方式1: 通过 rels 查找 comments 或 commentsExtended
        for rel in doc.part.rels.values():
            reltype = str(rel.reltype).lower()
            if 'comments' in reltype:
                comments_part = rel.target_part
                print(f"[Parser] 找到批注部分: {rel.reltype}")
                break
        
        if comments_part:
            from lxml import etree
            nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            root = etree.fromstring(comments_part.blob)
            
            # 尝试多种批注标签
            comment_elems = root.findall('.//w:comment', nsmap)
            if not comment_elems:
                # 尝试 commentsExtended 格式
                comment_elems = root.findall('.//w15:comment', {'w15': 'http://schemas.microsoft.com/office/word/2012/wordml'})
            
            for comment in comment_elems:
                comment_id = comment.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if not comment_id:
                    comment_id = comment.get('{http://schemas.microsoft.com/office/word/2012/wordml}id')
                author = comment.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}author', '')
                if not author:
                    author = comment.get('{http://schemas.microsoft.com/office/word/2012/wordml}author', '')
                comment_texts = []
                for p in comment.findall('.//w:p', nsmap):
                    texts = [t.text for t in p.findall('.//w:t', nsmap) if t.text]
                    comment_texts.append(''.join(texts))
                comments.append({
                    'id': comment_id,
                    'author': author,
                    'text': '\n'.join(comment_texts).strip()
                })
            print(f"[Parser] 解析到 {len(comments)} 条批注")
    except Exception as e:
        print(f"[Parser] 批注解析警告: {e}")
        import traceback
        traceback.print_exc()

    # 构建段落索引 -> 批注映射
    # 通过遍历 document.xml 中的 commentRangeStart/commentRangeEnd 来关联段落和批注
    para_comments = {}  # paragraph_index -> [comment]
    try:
        from lxml import etree
        nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        doc_xml = etree.fromstring(doc.part.blob)
        body = doc_xml.find('.//w:body', nsmap)
        all_elements = body.iter()
        para_idx = 0
        comment_ranges = {}  # comment_id -> {'start_para': idx, 'end_para': idx, 'text': ''}
        for elem in all_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'p':
                para_idx += 1
            elif tag == 'commentRangeStart':
                cid = elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid and cid not in comment_ranges:
                    comment_ranges[cid] = {'start_para': para_idx, 'end_para': para_idx}
            elif tag == 'commentRangeEnd':
                cid = elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
                if cid and cid in comment_ranges:
                    comment_ranges[cid]['end_para'] = para_idx
        # 关联批注文本
        comments_by_id = {c['id']: c for c in comments}
        for cid, rng in comment_ranges.items():
            if cid in comments_by_id:
                rng['text'] = comments_by_id[cid]['text']
                rng['author'] = comments_by_id[cid]['author']
                for pi in range(rng['start_para'], rng['end_para'] + 1):
                    if pi not in para_comments:
                        para_comments[pi] = []
                    para_comments[pi].append(rng)
    except Exception as e:
        print(f"批注段落关联警告: {e}")

    if not all_paras:
        return _empty_result(file_path)

    # === 1. 提取元信息 ===
    title = ''
    author = ''
    author_nationality = ''
    version = ''
    meta_end = 0  # 元信息结束位置

    # 第一个 Heading 1 是书名
    for i, p in enumerate(all_paras):
        if 'Heading 1' in p['style'] and p['text']:
            title = p['text']
            meta_end = i + 1
            break

    # 紧跟书名后的 Normal 段落：作者「国籍」
    for i in range(meta_end, min(meta_end + 2, len(all_paras))):
        p = all_paras[i]
        if 'Heading' in p['style']:
            break
        if not p['text']:
            continue
        # 匹配 "作者「国籍」" 或 "作者[国籍]" 格式
        m = re.match(r'^(.+?)[\u300c\u300d\[\【]([^\u300d\]\】]+)[\u300d\]\】]', p['text'])
        if m:
            author = m.group(1).strip()
            author_nationality = m.group(2).strip()
            meta_end = i + 1
            break
        else:
            # 没有国籍标记，尝试作为版本信息
            if not version:
                version = p['text']
                meta_end = i + 1

    # 再下一段 Normal 可能是版本信息
    for i in range(meta_end, min(meta_end + 1, len(all_paras))):
        p = all_paras[i]
        if 'Heading' in p['style']:
            break
        if not p['text']:
            continue
        if not version:
            version = p['text']
            meta_end = i + 1
            break

    # === 2. 提取章节和节 ===
    chapters = []       # 章列表
    sections = []       # 节列表（扁平）
    current_chapter = None
    current_section = None
    section_number = 0

    for i in range(meta_end, len(all_paras)):
        p = all_paras[i]
        text = p['text']
        style = p['style']

        if not text:
            continue

        # Heading 1 = 章标题（书名之后的）
        if 'Heading 1' in style and i > 0:
            # 保存当前未完成的节
            if current_section and current_section.get('content'):
                sections.append(current_section)
                current_section = None
            current_chapter = {
                'chapter_number': len(chapters) + 1,
                'title': text
            }
            chapters.append(current_chapter)
            continue

        # Heading 2 = 节标题
        if 'Heading 2' in style:
            # 保存当前未完成的节
            if current_section and current_section.get('content'):
                sections.append(current_section)

            section_number += 1
            # 提取节名（"第X节  节名" 格式）
            sec_title = text
            m = re.match(r'^第\d+节\s+(.+)', text)
            if m:
                sec_title = m.group(1).strip()

            current_section = {
                'section_number': section_number,
                'title': sec_title,
                'content': '',
                'chapter_number': current_chapter['chapter_number'] if current_chapter else 1,
                'summary': '',      # 从批注中提取的小结
                'annotations': []   # 从批注中提取的点评
            }

            # 检查该节标题段落是否有批注 -> 作为小结
            if i in para_comments:
                for cm in para_comments[i]:
                    current_section['summary'] = cm.get('text', '')

            # 记录当前节在 all_paras 中的起始索引，用于后续关联正文批注
            current_section['_para_start'] = i
            continue

        # Normal = 正文内容
        if current_section is not None:
            if current_section['content']:
                current_section['content'] += '\n' + text
            else:
                current_section['content'] = text

            # 检查该正文段落是否有批注 -> 作为点评
            if i in para_comments:
                for cm in para_comments[i]:
                    # 找到批注原文在当前节content中的字符位置
                    original_text = text  # 批注关联的段落文本
                    start_char = current_section['content'].rfind(original_text)
                    if start_char >= 0:
                        end_char = start_char + len(original_text) - 1
                    else:
                        start_char = 0
                        end_char = len(text) - 1
                    current_section['annotations'].append({
                        'original_text': original_text,
                        'comment': cm.get('text', ''),
                        'start_char': start_char,
                        'end_char': end_char
                    })

    # 保存最后一个节
    if current_section and current_section.get('content'):
        sections.append(current_section)

    return {
        'title': title or get_book_title(file_path),
        'author': author,
        'author_nationality': author_nationality,
        'version': version,
        'chapters': chapters,
        'sections': sections
    }


def parse_txt_file(file_path):
    """
    解析 TXT 文件（兼容旧格式）
    返回与 parse_docx_file 相同结构的字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = clean_text(content)
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]

    if not paragraphs:
        return _empty_result(file_path)

    # 尝试按章节模式解析
    chapter_patterns = [
        r'^第[一二三四五六七八九十百千零]+章',
        r'^第\d+章',
        r'^Chapter\s+\d+',
    ]

    chapters = []
    current_chapter = {'title': '前言', 'paragraphs': []}

    for para in paragraphs:
        is_chapter = False
        for pattern in chapter_patterns:
            if re.match(pattern, para, re.IGNORECASE):
                if current_chapter['paragraphs']:
                    chapters.append(current_chapter)
                current_chapter = {'title': para, 'paragraphs': []}
                is_chapter = True
                break
        if not is_chapter:
            current_chapter['paragraphs'].append(para)

    if current_chapter['paragraphs']:
        chapters.append(current_chapter)

    # 将章节分割为小节
    sections = []
    section_number = 0
    for ch_idx, chapter in enumerate(chapters):
        chapter_text = '\n'.join(chapter['paragraphs'])
        chapter_sections = split_into_sections(chapter_text, section_number + 1)
        for sec in chapter_sections:
            sec['chapter_number'] = ch_idx + 1
            sec['title'] = ''
            sections.append(sec)
        section_number += len(chapter_sections)

    return {
        'title': get_book_title(file_path),
        'author': '',
        'author_nationality': '',
        'version': '',
        'chapters': [{'chapter_number': i + 1, 'title': ch['title']} for i, ch in enumerate(chapters)],
        'sections': sections
    }


def _empty_result(file_path):
    """返回空结果"""
    return {
        'title': get_book_title(file_path),
        'author': '',
        'author_nationality': '',
        'version': '',
        'chapters': [],
        'sections': []
    }


def clean_text(text):
    """清理文本"""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r' +', ' ', text)
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    return text.strip()


def split_into_sections(text, start_number=1):
    """将文本分割为小节，每节 300-800 字"""
    sections = []
    paragraphs = text.split('\n')

    current_section = []
    current_length = 0
    section_number = start_number

    MIN_SECTION_LENGTH = 300
    MAX_SECTION_LENGTH = 800

    for para in paragraphs:
        para_length = len(para)
        if not current_section:
            current_section.append(para)
            current_length = para_length
            continue
        if current_length + para_length > MAX_SECTION_LENGTH:
            if current_length >= MIN_SECTION_LENGTH:
                sections.append({
                    'section_number': section_number,
                    'content': '\n'.join(current_section),
                    'length': current_length
                })
                section_number += 1
                current_section = [para]
                current_length = para_length
            else:
                current_section.append(para)
                current_length += para_length
        else:
            current_section.append(para)
            current_length += para_length

    if current_section:
        sections.append({
            'section_number': section_number,
            'content': '\n'.join(current_section),
            'length': current_length
        })

    return sections


def get_book_title(file_path):
    """从文件名获取书名"""
    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0]
    return title


if __name__ == '__main__':
    # 测试
    test_path = '/workspace/.uploads/69ee5b33-6581-4cbe-8448-8830bae8bc8b_童年-高尔基-导入版.docx'
    result = parse_file(test_path)
    print(f"书名: {result['title']}")
    print(f"作者: {result['author']}")
    print(f"国籍: {result['author_nationality']}")
    print(f"版本: {result['version']}")
    print(f"章数: {len(result['chapters'])}")
    print(f"节数: {len(result['sections'])}")
    print()
    for sec in result['sections'][:3]:
        print(f"第{sec['section_number']}节: {sec['title']} ({len(sec['content'])}字)")
        print(f"  内容预览: {sec['content'][:80]}...")
        print()
