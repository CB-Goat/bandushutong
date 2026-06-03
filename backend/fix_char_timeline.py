#!/usr/bin/env python3
"""
修复脚本：为已有音频但 char_timeline 为空的 text_segments 重新生成 char_timeline

核心逻辑：
- 磁盘上的音频文件是按 TTS 字数限制切分的子文件（section_{id}_0.mp3, _1.mp3 ...）
- text_segments 是按点评边界切的逻辑段
- 修复方式：读取所有子文件的时长得到总时长，按字符位置比例分配给每个 text_segment
- 不调用 TTS API（零费用），不重新生成音频（零时间），只修复数据库
"""

import os
import sys
import json
import struct
import glob as glob_module

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, get_sections_by_book

# 音频文件根目录（Docker 容器内路径）
AUDIO_FILES_DIR = os.environ.get('AUDIO_FILES_DIR', '/app/audio_files')


def get_mp3_duration(filepath):
    """读取 MP3 文件的时长（秒），不依赖第三方库"""
    try:
        if not os.path.exists(filepath):
            return None
        size = os.path.getsize(filepath)
        if size < 10:
            return None

        with open(filepath, 'rb') as f:
            # ID3v1 标签检查
            f.seek(-128, 2)
            data = f.read(128)
            has_id3v1 = data[:3] == b'TAG'
            if has_id3v1:
                f.seek(-256, 2)
            else:
                f.seek(0)

            header = f.read(4)
            if len(header) < 4:
                return None

            # ID3v2 标签跳过
            if header[:3] == b'ID3':
                id3_size = struct.unpack('>I', f.read(4))[0]
                f.seek(id3_size + 10)
                header = f.read(4)

            if len(header) < 4:
                return None

            # 找第一个同步字
            while True:
                if header[0] != 0xFF or (header[1] & 0xE0) != 0xE0:
                    byte = f.read(1)
                    if not byte:
                        return None
                    header = header[1:] + byte
                else:
                    break

            first_frame_header = header + f.read(4 - len(header))
            if len(first_frame_header) < 4:
                return None

            version = (first_frame_header[1] >> 3) & 0x03

            if version not in (2, 3):
                return None

            bitrate_idx = (first_frame_header[2] >> 4) & 0x0F
            sample_rate_idx = (first_frame_header[3] >> 2) & 0x03
            padding = (first_frame_header[3] >> 1) & 0x01

            bitrates_v1l3 = [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320,0]
            sample_rates_v1 = [44100,48000,32000,0]

            bitrate = bitrates_v1l3[bitrate_idx] * 1000
            sample_rate = sample_rates_v1[sample_rate_idx]

            if bitrate == 0 or sample_rate == 0:
                return None

            if version == 3:  # MPEG1
                frame_length = int((144 * bitrate) / sample_rate) + padding
            else:  # MPEG2 / 2.5
                frame_length = int((72 * bitrate) / sample_rate) + padding

            if frame_length <= 0:
                return None

            total_size = size
            if has_id3v1:
                total_size -= 128

            num_frames = total_size // frame_length
            if num_frames <= 0:
                return None

            samples_per_frame = 1152  # MPEG1 Layer III
            duration = (num_frames * samples_per_frame) / float(sample_rate)

            return round(duration, 3)

    except Exception as e:
        print(f"[FIX] 读取音频时长失败 {filepath}: {e}")
        return None


def find_section_audio_files(section_id):
    """
    查找该节的所有音频子文件。
    
    匹配两种命名模式：
      - section_{id}_0.mp3, section_{id}_1.mp3 ... (generate_section_audio_with_timeline 产生的 TTS 分块)
      - segment_{id}_0.mp3, segment_{id}_1.mp3 ... (generate_segmented_audio 产生的分段音频)
      
    返回：[(filepath, duration), ...] 按文件名排序
    """
    results = []

    # 模式1：section_{id}_*.mp3（TTS 分块，最常见）
    pattern1 = os.path.join(AUDIO_FILES_DIR, f'section_{section_id}_*.mp3')
    files1 = sorted(glob_module.glob(pattern1))

    # 模式2：segment_{id}_*.mp3（分段音频）
    pattern2 = os.path.join(AUDIO_FILES_DIR, f'segment_{section_id}_*.mp3')
    files2 = sorted(glob_module.glob(pattern2))

    # 模式3：section_{id}.mp3（合并后的单文件）
    single_file = os.path.join(AUDIO_FILES_DIR, f'section_{section_id}.mp3')

    # 优先使用分块文件（更精确）
    if files1 and len(files1) > 1:
        for fp in files1:
            d = get_mp3_duration(fp)
            if d and d > 0:
                results.append((fp, d))
        print(f"[FIX] 找到 {len(results)} 个 TTS 分块音频 (section_{section_id}_*.mp3)")
        return results

    if files2 and len(files2) > 1:
        for fp in files2:
            d = get_mp3_duration(fp)
            if d and d > 0:
                results.append((fp, d))
        print(f"[FIX] 找到 {len(results)} 个分段音频 (segment_{section_id}_*.mp3)")
        return results

    # 回退到单个合并文件
    if os.path.exists(single_file):
        d = get_mp3_duration(single_file)
        if d and d > 0:
            results.append((single_file, d))
            print(f"[FIX] 使用合并音频文件 (section_{section_id}.mp3), 时长={d}s")
            return results

    print(f"[FIX] ⚠️ 未找到节 {section_id} 的任何音频文件！")
    return results


def rebuild_char_timeline_for_segment(content, segment_start_time, segment_end_time):
    """
    为单个 text_segment 构建字符时间轴
    
    时间轴的起点是 segment_start_time（相对于整节音频的偏移），
    这样前端的播放进度才能正确对应到完整音频的时间线上。
    
    参数：
        content: 该段的文本内容
        segment_start_time: 该段在完整音频中的起始时间（秒）
        segment_end_time: 该段在完整音频中的结束时间（秒）
        
    返回：
        char_timeline: 字符时间轴数组（每个值是该字符的绝对播放时间点）
    """
    seg_duration = segment_end_time - segment_start_time
    if not content or seg_duration <= 0:
        return []

    text = content.replace('\n', '')
    text_len = len(text)

    if text_len == 0:
        return []

    # 计算每个字符的时间权重
    char_weights = []
    for char in text:
        if char in '。！？；：':
            char_weights.append(3.0)
        elif char in '，、':
            char_weights.append(2.0)
        elif char in '""''（）【】《》':
            char_weights.append(1.5)
        else:
            char_weights.append(1.0)

    total_weight = sum(char_weights)
    accumulated_weight = 0
    char_timeline = []

    for j in range(text_len):
        t = segment_start_time + (accumulated_weight / total_weight) * seg_duration
        char_timeline.append(round(t, 3))
        accumulated_weight += char_weights[j]

    return char_timeline


def fix_section_char_timeline(section_id, force=False):
    """
    修复单个节的所有 text_segments 的 char_timeline
    
    核心策略：
    1. 从磁盘找到该节的所有音频子文件
    2. 计算总时长
    3. 按 text_segments 的 start/end_char 在总文本中的比例，分配时间
    4. 为每个 segment 生成 char_timeline（绝对时间，相对于整节音频开头）
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        # 获取该节的内容
        cursor.execute('SELECT content FROM sections WHERE id = %s', (section_id,))
        section_row = cursor.fetchone()
        if not section_row:
            print(f"[FIX] 节 {section_id} 不存在")
            return False

        section_content = section_row.get('content', '')
        clean_text = section_content.replace('\n', '')
        total_chars = len(clean_text)

        if total_chars == 0:
            print(f"[FIX] 节 {section_id} 内容为空")
            return False

        # 获取该节的所有音频文件及其时长
        audio_files = find_section_audio_files(section_id)
        if not audio_files:
            print(f"[FIX] 节 {section_id} 无可用音频文件")
            return False

        # 计算总时长
        total_duration = sum(d for _, d in audio_files)
        if total_duration <= 0:
            print(f"[FIX] 节 {section_id} 总音频时长为0")
            return False

        print(f"[FIX] 节 {section_id}: 文本={total_chars}字, 音频共{len(audio_files)}个文件, "
              f"总时长={total_duration:.1f}s")

        # 打印每个音频文件的信息
        for fp, d in audio_files:
            print(f"[FIX]   📄 {os.path.basename(fp)}: {d}s")

        # 获取该节的所有 text_segments
        cursor.execute(
            'SELECT id, segment_number, content, start_char, end_char, '
            'audio_path, audio_duration, char_timeline '
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
            seg_num = seg.get('segment_number', 0)
            char_timeline_raw = seg.get('char_timeline', '')

            # 解析现有的 char_timeline — 如果已有有效数据则跳过
            existing_timeline = []
            if char_timeline_raw:
                try:
                    if isinstance(char_timeline_raw, str):
                        existing_timeline = json.loads(char_timeline_raw)
                    elif isinstance(char_timeline_raw, list):
                        existing_timeline = char_timeline_raw
                except:
                    existing_timeline = []

            if existing_timeline and len(existing_timeline) > 0 and not force:
                print(f"[FIX] 跳过 segment {seg_id}#{seg_num}: 已有 {len(existing_timeline)} 个时间点 (用 force=True 强制覆盖)")
                continue

            if existing_timeline and len(existing_timeline) > 0 and force:
                print(f"[FIX] 🔄 force 模式: 覆盖 segment {seg_id}#{seg_num} 的 {len(existing_timeline)} 个旧时间点")

            # 获取该段的字符范围和内容
            start_char = seg.get('start_char', 0)
            end_char = seg.get('end_char', 0)
            seg_content = seg.get('content', '')
            
            if not seg_content and section_content:
                seg_content = clean_text[start_char:end_char]

            if not seg_content:
                # 尝试用 char range 提取
                seg_content = clean_text[start_char:end_char]

            if not seg_content or not seg_content.strip():
                print(f"[FIX] 跳过 segment {seg_id}#{seg_num}: 内容为空 (start={start_char}, end={end_char})")
                continue
            
            seg_content_clean = seg_content.replace('\n', '')
            seg_char_count = len(seg_content_clean)

            # 计算该段在整节中的时间范围
            # 基于字符位置按比例分配（考虑标点符号权重）
            # 先计算整个文本的权重分布，确定这个段的起止时间
            seg_start_ratio = start_char / max(total_chars, 1)
            seg_end_ratio = end_char / max(total_chars, 1)
            
            # 用字符数比例作为粗略估算，再微调
            seg_start_time = seg_start_ratio * total_duration
            seg_end_time = seg_end_ratio * total_duration
            seg_duration = seg_end_time - seg_start_time

            if seg_duration <= 0:
                seg_duration = (seg_char_count / max(total_chars, 1)) * total_duration
                seg_end_time = seg_start_time + seg_duration

            # 重新生成 char_timeline（使用绝对时间）
            new_timeline = rebuild_char_timeline_for_segment(
                seg_content_clean, seg_start_time, seg_end_time
            )

            if new_timeline:
                cursor.execute(
                    'UPDATE text_segments SET char_timeline = %s, audio_duration = %s WHERE id = %s',
                    (json.dumps(new_timeline), round(seg_duration, 3), seg_id)
                )
                fixed_count += 1
                print(f"[FIX] ✅ segment {seg_id}#{seg_num}: "
                      f"chars [{start_char}:{end_char}]={seg_char_count}字, "
                      f"time [{seg_start_time:.1f}s:{seg_end_time:.1f}s]={seg_duration:.1f}s, "
                      f"timeline={len(new_timeline)}点")
            else:
                print(f"[FIX] 跳过 segment {seg_id}#: 无法生成 char_timeline")

        conn.commit()
        print(f"\n[FIX] 节 {section_id} 修复完成: {fixed_count}/{len(segments)} segments")
        return True

    except Exception as e:
        import traceback
        print(f"[FIX] 修复节 {section_id} 失败: {e}")
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()


def fix_book_char_timeline(book_id, force=False):
    """修复整本书的所有节"""
    sections = get_sections_by_book(book_id)
    if not sections:
        print(f"[FIX] 书籍 {book_id} 没有节")
        return

    total_fixed = 0
    for section in sections:
        section_id = section['id']
        print(f"\n{'='*60}")
        print(f"[FIX] 处理节 {section_id}: {section.get('title', '')}")
        print('='*60)
        if fix_section_char_timeline(section_id, force=force):
            total_fixed += 1

    print(f"\n[FIX] 书籍 {book_id} 完成, 共处理 {total_fixed} 个节")


def fix_all_books():
    """修复所有书籍"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id, title FROM books WHERE is_public = 1 ORDER BY id')
        books = cursor.fetchall()

        for book in books:
            book_id = book['id']
            book_title = book.get('title', '未知')
            print(f"\n{'#'*60}")
            print(f"# 修复书籍: {book_id} - {book_title}")
            print('#'*60)
            fix_book_char_timeline(book_id)

    finally:
        conn.close()


def main():
    print("="*60)
    print("char_timeline 修复工具 v3")
    print("原理：从磁盘音频文件读取真实时长，按字符位置比例分配给各 segment")
    print("="*60)

    if len(sys.argv) < 2:
        print("\n用法:")
        print(f"  python {sys.argv[0]} all                  # 所有公版书")
        print(f"  python {sys.argv[0]} book <book_id>       # 指定书籍")
        print(f"  python {sys.argv[0]} section <section_id>  # 指定节")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'all':
        fix_all_books()
    elif command == 'book' and len(sys.argv) >= 3:
        fix_book_char_timeline(int(sys.argv[2]))
    elif command == 'section' and len(sys.argv) >= 3:
        fix_section_char_timeline(int(sys.argv[2]))
    else:
        print("参数错误!")
        sys.exit(1)


if __name__ == '__main__':
    main()
