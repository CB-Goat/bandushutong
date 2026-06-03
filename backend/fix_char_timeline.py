#!/usr/bin/env python3
"""
修复脚本 v5 — 同时修复 audio_path 映射和 char_timeline

问题根因：
- TTS 按 ~300字/块 切分音频 → section_{id}_0.mp3, _1.mp3, _2.mp3 ...
- text_segments 按点评边界切分 → 原文段/点评/小结，两者切分逻辑完全不同
- 数据库中所有 text_segments 的 audio_path 错误地指向同一个文件
- 导致前端反复播放同一段音频

修复策略：
1. 计算每个 TTS 音频块对应的字符范围（均分总字符数）
2. 对每个 text_segment，找到字符重叠最多的那个音频块作为主音频
3. 修正 audio_path 指向正确的音频文件
4. 重新生成 char_timeline（相对于该段自己的音频，从 0 开始）
"""

import os
import sys
import json
import struct
import glob as glob_module

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, get_sections_by_book

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

            if header[:3] == b'ID3':
                id3_size = struct.unpack('>I', f.read(4))[0]
                f.seek(id3_size + 10)
                header = f.read(4)

            if len(header) < 4:
                return None

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

            if version == 3:
                frame_length = int((144 * bitrate) / sample_rate) + padding
            else:
                frame_length = int((72 * bitrate) / sample_rate) + padding

            if frame_length <= 0:
                return None

            total_size = size
            if has_id3v1:
                total_size -= 128

            num_frames = total_size // frame_length
            if num_frames <= 0:
                return None

            samples_per_frame = 1152
            duration = (num_frames * samples_per_frame) / float(sample_rate)
            return round(duration, 3)

    except Exception as e:
        print(f"[FIX] 读取音频时长失败 {filepath}: {e}")
        return None


def find_section_audio_files(section_id):
    """查找该节的所有 TTS 分块音频子文件"""
    results = []

    pattern1 = os.path.join(AUDIO_FILES_DIR, f'section_{section_id}_*.mp3')
    files1 = sorted(glob_module.glob(pattern1))

    pattern2 = os.path.join(AUDIO_FILES_DIR, f'segment_{section_id}_*.mp3')
    files2 = sorted(glob_module.glob(pattern2))

    single_file = os.path.join(AUDIO_FILES_DIR, f'section_{section_id}.mp3')

    # 优先使用分块文件
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

    # 回退到合并后的单文件
    if os.path.exists(single_file):
        d = get_mp3_duration(single_file)
        if d and d > 0:
            results.append((single_file, d))
            print(f"[FIX] 使用合并音频 (section_{section_id}.mp3), 时长={d}s")
            return results

    print(f"[FIX] ⚠️ 未找到节 {section_id} 的任何音频文件！")
    return results


def compute_tts_chunk_ranges(total_chars, num_chunks):
    """
    计算 TTS 每个音频块大致对应的字符范围。
    
    generate_section_audio_with_timeline 按 ~900字节(~300中文字)切分，
    这里用均分估算，最后一块可能不均等。
    
    返回：[(start, end), ...] 每个块的字符范围
    """
    if num_chunks <= 0:
        return []
    chars_per_chunk = total_chars / num_chunks
    ranges = []
    for i in range(num_chunks):
        start = round(i * chars_per_chunk)
        end = round((i + 1) * chars_per_chunk) if i < num_chunks - 1 else total_chars
        ranges.append((start, end))
    return ranges


def find_best_audio_chunk(seg_start, seg_end, chunk_ranges):
    """
    为一个 text_segment 找到字符重叠最大的 TTS 音频块索引。
    
    返回：(best_chunk_index, overlap_count)
    """
    best_idx = 0
    best_overlap = 0
    for idx, (chunk_start, chunk_end) in enumerate(chunk_ranges):
        # 计算重叠字符数
        overlap_start = max(seg_start, chunk_start)
        overlap_end = min(seg_end, chunk_end)
        overlap = max(0, overlap_end - overlap_start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_idx = idx
    return best_idx, best_overlap


def build_char_timeline(content, duration):
    """
    构建一段文本的字符时间轴（从 0 开始的相对时间）
    
    参数：
        content: 文本内容
        duration: 该段音频的总时长（秒）
        
    返回：
        char_timeline: 时间点数组，每个值是该字符在音频中的时间位置
    """
    text = content.replace('\n', '')
    text_len = len(text)
    if text_len == 0 or duration <= 0:
        return []

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
        t = (accumulated_weight / total_weight) * duration
        char_timeline.append(round(t, 3))
        accumulated_weight += char_weights[j]

    return char_timeline


def fix_section_char_timeline(section_id, force=False):
    """
    修复单个节：同时修正 audio_path 和 char_timeline
    
    策略：
    1. 从磁盘找到所有 TTS 分块音频
    2. 估算每个音频块对应的字符范围
    3. 对每个 text_segment：
       a. 找到最匹配的音频块
       b. 更新 audio_path 指向该音频块
       c. 更新 audio_duration 为该音频块的实际时长
       d. 用该时长生成新的 char_timeline（从 0 开始的相对时间）
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        # 获取节内容
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

        # 获取所有音频文件
        audio_files = find_section_audio_files(section_id)
        if not audio_files:
            print(f"[FIX] 节 {section_id} 无可用音频文件")
            return False

        num_chunks = len(audio_files)
        total_duration = sum(d for _, d in audio_files)

        # 计算每个 TTS 块的字符范围
        chunk_ranges = compute_tts_chunk_ranges(total_chars, num_chunks)

        print(f"[FIX] 节 {section_id}: 文本={total_chars}字, "
              f"音频={num_chunks}个块, 总时长={total_duration:.1f}s")
        print(f"[FIX] TTS 字符范围映射:")
        for i, (fp, d) in enumerate(audio_files):
            if i < len(chunk_ranges):
                cs, ce = chunk_ranges[i]
                print(f"[FIX]   块{i} ({os.path.basename(fp)}): 字[{cs}:{ce}]={ce-cs}字, 时长={d}s")
            else:
                print(f"[FIX]   块{i} ({os.path.basename(fp)}): 时长={d}s")

        # 获取所有 text_segments
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
            old_audio_path = seg.get('audio_path', '') or ''
            char_timeline_raw = seg.get('char_timeline', '')

            # 检查是否已有数据（force 模式下也继续）
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
                print(f"[FIX] 跳过 segment {seg_id}#{seg_num}: 已有数据 (用 force=True 覆盖)")
                continue

            if existing_timeline and len(existing_timeline) > 0 and force:
                print(f"[FIX] 🔄 segment {seg_id}#{seg_num}: 强制覆盖")

            # 字符范围
            start_char = seg.get('start_char', 0)
            end_char = seg.get('end_char', 0)
            seg_content = seg.get('content', '')

            if not seg_content and section_content:
                seg_content = clean_text[start_char:end_char]
            if not seg_content:
                seg_content = clean_text[start_char:end_char]

            if not seg_content or not seg_content.strip():
                print(f"[FIX] 跳过 segment {seg_id}#{seg_num}: 内容为空 [{start_char}:{end_char}]")
                continue

            seg_clean = seg_content.replace('\n', '')
            seg_char_count = len(seg_clean)

            # === 核心修正：找到最佳匹配的音频块 ===
            best_idx, overlap = find_best_audio_chunk(start_char, end_char, chunk_ranges)
            matched_fp, matched_dur = audio_files[best_idx]
            matched_basename = os.path.basename(matched_fp)

            # 构建 API 路径
            new_audio_path = f'/api/audio/{matched_basename}'
            
            # 如果 audio_path 没变且不是强制模式，跳过
            if new_audio_path == old_audio_path and existing_timeline and not force:
                print(f"[FIX] 跳过 segment {seg_id}#{seg_num}: audio_path 未变且有 timeline")
                continue

            # 生成新的 char_timeline（相对于这个音频块，从 0 开始）
            new_timeline = build_char_timeline(seg_clean, matched_dur)

            if new_timeline:
                cursor.execute(
                    'UPDATE text_segments SET audio_path = %s, audio_duration = %s, char_timeline = %s '
                    'WHERE id = %s',
                    (new_audio_path, matched_dur, json.dumps(new_timeline), seg_id)
                )
                
                changed_path = '' if new_audio_path == old_audio_path else f' (路径: {old_audio_path} → {new_audio_path})'
                fixed_count += 1
                print(f"[FIX] ✅ segment {seg_id}#{seg_num}: "
                      f"chars[{start_char}:{end_char}]={seg_char_count}字 → "
                      f"音频块#{best_idx} ({matched_basename}, {matched_dur}s, 重叠{overlap}字)"
                      f"{changed_path}, timeline={len(new_timeline)}点")
            else:
                print(f"[FIX] ⚠️ segment {seg_id}#{seg_num}: 无法生成 timeline")

        conn.commit()
        print(f"\n[FIX] 节 {section_id} 修复完成: {fixed_count}/{len(segments)} segments (audio_path+char_timeline)")
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
    print("char_timeline + audio_path 修复工具 v5")
    print("同时修复:")
    print("  1. text_segments.audio_path → 指向正确的 TTS 分块音频")
    print("  2. text_segments.char_timeline → 匹配对应音频的真实时长")
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
