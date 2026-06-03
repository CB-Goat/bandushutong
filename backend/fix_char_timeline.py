#!/usr/bin/env python3
"""
修复脚本：为已有音频但 char_timeline 为空的 text_segments 重新生成 char_timeline

特点：
- 不调用 TTS API（零费用）
- 不重新生成音频（零时间）
- 只修复数据库记录
"""

import os
import sys
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, get_sections_by_book


def rebuild_char_timeline(content, audio_duration):
    """
    基于文本内容和音频时长重新生成 char_timeline
    
    参数：
        content: 文本内容
        audio_duration: 音频时长（秒）
    
    返回：
        char_timeline: 字符时间轴数组
    """
    if not content or audio_duration <= 0:
        return []
    
    # 去掉换行符，与前端保持一致
    text = content.replace('\n', '')
    text_len = len(text)
    
    if text_len == 0:
        return []
    
    # 计算每个字符的时间权重
    char_weights = []
    for char in text:
        if char in '。！？；：':  # 长停顿
            char_weights.append(3.0)
        elif char in '，、':  # 短停顿
            char_weights.append(2.0)
        elif char in '""''（）【】《》':  # 中等停顿
            char_weights.append(1.5)
        else:
            char_weights.append(1.0)
    
    total_weight = sum(char_weights)
    accumulated_weight = 0
    char_timeline = []
    
    for j in range(text_len):
        t = (accumulated_weight / total_weight) * audio_duration
        char_timeline.append(round(t, 3))
        accumulated_weight += char_weights[j]
    
    return char_timeline


def fix_section_char_timeline(section_id):
    """
    修复单个节的所有 text_segments 的 char_timeline
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # 获取该节的内容（用于计算字符时间轴）
        cursor.execute('SELECT content FROM sections WHERE id = %s', (section_id,))
        section_row = cursor.fetchone()
        if not section_row:
            print(f"[FIX] 节 {section_id} 不存在")
            return False
        
        section_content = section_row.get('content', '')
        
        # 获取该节的所有 text_segments
        cursor.execute(
            'SELECT id, segment_number, content, start_char, end_char, audio_path, audio_duration, char_timeline '
            'FROM text_segments WHERE section_id = %s ORDER BY segment_number',
            (section_id,)
        )
        segments = cursor.fetchall()
        
        if not segments:
            print(f"[FIX] 节 {section_id} 没有 text_segments")
            return False
        
        fixed_count = 0
        for seg in segments:
            seg_id = seg['id']
            audio_path = seg.get('audio_path', '')
            audio_duration = seg.get('audio_duration', 0)
            char_timeline = seg.get('char_timeline', '')

            print(f"[FIX] DEBUG segment {seg_id}: audio_path={repr(audio_path)[:80]}, audio_duration={repr(audio_duration)}, content_len={len(seg.get('content', '') or '')}")

            # 检查是否需要修复：有音频但 char_timeline 为空
            if audio_path and audio_duration > 0:
                # 解析现有的 char_timeline
                existing_timeline = []
                if char_timeline:
                    try:
                        if isinstance(char_timeline, str):
                            existing_timeline = json.loads(char_timeline)
                        elif isinstance(char_timeline, list):
                            existing_timeline = char_timeline
                    except:
                        existing_timeline = []
                
                if not existing_timeline or len(existing_timeline) == 0:
                    # 获取该段的内容
                    seg_content = seg.get('content', '')
                    if not seg_content and section_content:
                        # 从节内容中提取
                        start_char = seg.get('start_char', 0)
                        end_char = seg.get('end_char', 0)
                        seg_content = section_content[start_char:end_char]
                    
                    # 重新生成 char_timeline
                    new_timeline = rebuild_char_timeline(seg_content, audio_duration)
                    
                    if new_timeline:
                        # 更新数据库
                        cursor.execute(
                            'UPDATE text_segments SET char_timeline = %s WHERE id = %s',
                            (json.dumps(new_timeline), seg_id)
                        )
                        fixed_count += 1
                        print(f"[FIX] 修复 segment {seg_id}: 生成 {len(new_timeline)} 个字符时间点")
                    else:
                        print(f"[FIX] 跳过 segment {seg_id}: 无法生成 char_timeline")
                else:
                    print(f"[FIX] 跳过 segment {seg_id}: char_timeline 已有 {len(existing_timeline)} 个时间点")
            else:
                print(f"[FIX] 跳过 segment {seg_id}: 无音频或时长为0")
        
        conn.commit()
        print(f"[FIX] 节 {section_id} 修复完成，共修复 {fixed_count} 个 segments")
        return True
        
    except Exception as e:
        print(f"[FIX] 修复节 {section_id} 失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def fix_book_char_timeline(book_id):
    """
    修复整本书的所有节
    """
    sections = get_sections_by_book(book_id)
    if not sections:
        print(f"[FIX] 书籍 {book_id} 没有节")
        return
    
    total_fixed = 0
    for section in sections:
        section_id = section['id']
        print(f"\n[FIX] 处理节 {section_id}: {section.get('title', '')}")
        if fix_section_char_timeline(section_id):
            total_fixed += 1
    
    print(f"\n[FIX] 书籍 {book_id} 修复完成，共修复 {total_fixed} 个节")


def fix_all_books():
    """
    修复所有书籍
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, title FROM books WHERE is_public = 1 ORDER BY id')
        books = cursor.fetchall()
        
        for book in books:
            book_id = book['id']
            book_title = book.get('title', '未知')
            print(f"\n" + "="*60)
            print(f"[FIX] 开始修复书籍: {book_id} - {book_title}")
            print("="*60)
            fix_book_char_timeline(book_id)
        
    finally:
        conn.close()


def main():
    print("="*60)
    print("修复脚本：为已有音频的节重新生成 char_timeline")
    print("特点：不调用 TTS API，不重新生成音频，只修复数据库")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\n使用方法：")
        print(f"  python {sys.argv[0]} all              # 修复所有书籍")
        print(f"  python {sys.argv[0]} book <book_id>   # 修复指定书籍")
        print(f"  python {sys.argv[0]} section <section_id> # 修复指定节")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'all':
        fix_all_books()
    elif command == 'book' and len(sys.argv) >= 3:
        book_id = int(sys.argv[2])
        fix_book_char_timeline(book_id)
    elif command == 'section' and len(sys.argv) >= 3:
        section_id = int(sys.argv[2])
        fix_section_char_timeline(section_id)
    else:
        print("参数错误！")
        sys.exit(1)


if __name__ == '__main__':
    main()
