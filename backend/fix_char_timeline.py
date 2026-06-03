#!/usr/bin/env python3
"""
修复脚本 v6 — 用现有 TTS 音频块重建正确的分段音频文件

问题根因：
- 磁盘上有旧模式生成的 section_{id}_*.mp3（按~300字/TTS限制切块）
- 但数据库期望新模式文件 segment_{id}_{seg_idx}.mp3（按点评边界切块）
- 两者切分逻辑不同，无法直接一一对应

v6 修复策略（不重新生成 TTS，零费用）：
1. 读取该节所有 section_{id}_*.mp3 文件，测量每个的时长和估算字符范围
2. 对每个 text_segment（按点评边界切的逻辑段）：
   a. 确定它覆盖了哪些 TTS 块（可能跨越多个块）
   b. 用 ffmpeg 从相关 TTS 块中裁剪+拼接，重建出 segment_{id}_{seg_idx}.mp3
   c. 测量新文件的时长
   d. 生成匹配新文件的 char_timeline（从0开始的相对时间）
3. 更新数据库：audio_path / audio_duration / char_timeline

两层切分逻辑：
  第1层：按点评边界 → text_segments（原文段/点评/小结）
  第2层：如果单段超TTS字数限制 → 再按字数切分子块（这就是 section_*.mp3）
"""

import os
import sys
import json
import struct
import subprocess
import glob as glob_module
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, get_sections_by_book

AUDIO_FILES_DIR = os.environ.get('AUDIO_FILES_DIR', '/app/audio_files')


def get_mp3_duration(filepath):
    """读取 MP3 文件的时长（秒），纯 Python 解析"""
    try:
        if not os.path.exists(filepath):
            return None
        size = os.path.getsize(filepath)
        if size < 10:
            return None

        with open(filepath, 'rb') as f:
            # 跳过 ID3v2 标签
            header = f.read(3)
            if header[:3] == b'ID3':
                f.seek(3)
                id3_size = struct.unpack('>I', f.read(4))[0]
                id3_size ^= 0x80808080  # syncsafe integer
                f.seek(id3_size + 6)  # 跳过剩余 header
            else:
                f.seek(0)

            # 找到第一个 MPEG 帧头
            data = f.read(4)
            while len(data) == 4:
                if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
                    break
                data = data[1:] + f.read(1)

            if len(data) < 4:
                return None

            first_frame_header = data

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

            # 计算文件中 ID3v1 标签大小
            has_id3v1 = False
            f.seek(-128, 2)
            if f.read(3) == b'TAG':
                has_id3v1 = True

            total_data_size = size - f.tell()  # 排除ID3标签
            num_frames = total_data_size // frame_length
            if num_frames <= 0:
                return None

            samples_per_frame = 1152
            duration = (num_frames * samples_per_frame) / float(sample_rate)
            return round(duration, 3)

    except Exception as e:
        print(f"[FIX] 读取音频时长失败 {filepath}: {e}")
        return None


def find_tts_chunk_files(section_id):
    """
    查找该节的 TTS 分块音频文件（旧模式：section_{id}_*.mp3）。

    这些文件是 generate_section_audio_with_timeline() 按 ~300字/块 切分的，
    合并成 section_{id}.mp3 后本应删除，但可能因为错误仍保留在磁盘上。
    
    返回：[(filepath, duration), ...] 按文件名序号排序
    """
    results = []
    pattern = os.path.join(AUDIO_FILES_DIR, f'section_{section_id}_*.mp3')
    files = sorted(glob_module.glob(pattern))

    for fp in files:
        d = get_mp3_duration(fp)
        if d and d > 0:
            results.append((fp, d))

    if results:
        print(f"[FIX] 找到 {len(results)} 个 TTS 分块音频 (section_{section_id}_*.mp3)")
    else:
        print(f"[FIX] 未找到 section_{section_id}_*.mp3 分块文件")

    return results


def compute_tts_chunk_char_ranges(total_chars, num_chunks, chunk_durations):
    """
    计算 每个 TTS 音频块对应的字符范围。
    
    generate_section_audio_with_timeline() 的切分规则：
    - 每 ~900 字节 UTF-8（约 ~300 中文字）或遇到 。！？\n 时切分
    
    这里用均分估算，同时考虑时长的细微差异做微调：
    字符数与时长大致成正比（同一语速下）
    
    返回：[(start_char, end_char), ...] 
    """
    if num_chunks <= 0 or total_chars <= 0:
        return []

    total_duration = sum(chunk_durations)
    ranges = []
    pos = 0

    for i in range(num_chunks):
        if i == num_chunks - 1:
            # 最后一块包含所有剩余字符
            end = total_chars
        elif total_duration > 0:
            # 按时长比例分配字符数
            ratio = chunk_durations[i] / total_duration
            end = pos + int(round(total_chars * ratio))
            # 确保至少前进1个字符
            end = max(end, pos + 1)
        else:
            end = pos + int(total_chars / num_chunks)

        ranges.append((pos, end))
        pos = end

    # 确保最后一块到达末尾
    if ranges:
        ranges[-1] = (ranges[-1][0], total_chars)

    return ranges


def build_segment_audio_ffmpeg(segment_file, chunk_sources):
    """
    用 ffmpeg 从多个 TTS 块中裁剪并拼接，构建一个 text_segment 的完整音频。
    
    参数：
        segment_file: 输出文件路径
        chunk_sources: [(chunk_filepath, start_time, end_time), ...]
                       start_time/end_time 为 None 表示取整个文件
                       单位：秒

    返回：(成功bool, 时长秒数)
    """
    if not chunk_sources:
        return False, 0

    # 如果只有一个源且不需要裁剪，直接复制
    if len(chunk_sources) == 1 and chunk_sources[0][1] is None:
        src_fp = chunk_sources[0][0]
        try:
            import shutil
            shutil.copy2(src_fp, segment_file)
            d = get_mp3_duration(segment_file)
            return True, d or 0
        except Exception as e:
            print(f"[FIX] 复制文件失败: {e}")

    # 构建 ffmpeg concat 列表（需要先裁剪的用中间文件）
    parts_to_concat = []
    temp_files = []

    try:
        for i, (src_fp, t_start, t_end) in enumerate(chunk_sources):
            if t_start is not None and t_end is not None:
                # 需要时间裁剪
                temp_fp = segment_file.replace('.mp3', f'_part{i}.mp3')
                temp_files.append(temp_fp)

                duration = t_end - t_start
                cmd = [
                    'ffmpeg', '-y',
                    '-i', src_fp,
                    '-ss', str(t_start),
                    '-t', str(duration),
                    '-acodec', 'copy',
                    temp_fp
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode != 0:
                    print(f"[FIX] ⚠️ ffmpeg 裁剪失败 (part{i}): {result.stderr.decode()[-100:]}")
                    continue
                parts_to_concat.append(temp_fp)
            else:
                # 整块使用
                parts_to_concat.append(src_fp)

        if not parts_to_concat:
            return False, 0

        # 只有一个部分且就是目标本身
        if len(parts_to_concat) == 1 and parts_to_concat[0] == segment_file:
            d = get_mp3_duration(segment_file)
            return bool(d), d or 0

        # 多部分拼接
        list_file = segment_file + '.list.txt'
        with open(list_file, 'w') as f:
            for pf in parts_to_concat:
                f.write(f"file '{pf}'\n")

        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            segment_file
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if os.path.exists(list_file):
            os.remove(list_file)

        if result.returncode != 0:
            print(f"[FIX] ⚠️ ffmpeg 拼接失败: {result.stderr.decode()[-200:]}")
            return False, 0

        duration = get_mp3_duration(segment_file)
        return bool(duration), duration or 0

    finally:
        # 清理临时文件
        for tf in temp_files:
            if os.path.exists(tf) and tf != segment_file:
                try:
                    os.remove(tf)
                except:
                    pass


def build_char_timeline(content, duration):
    """构建字符时间轴（从 0 开始的相对时间），带标点权重"""
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
    修复单个节：用现有的 TTS 分块音频重建正确的分段音频文件。
    
    流程：
    1. 找到 section_{id}_*.mp3（TTS 字数切块）
    2. 估算每个 TTS 块对应的字符范围和时间范围
    3. 对每个 text_segment：
       - 确定它跨了哪些 TTS 块
       - 用 ffmpeg 裁剪+拼接 → 新建 segment_{id}_{seg_idx}.mp3
       - 测量新文件时长
       - 生成 char_timeline
       - 更新数据库
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

        # 获取 TTS 分块音频
        tts_chunks = find_tts_chunk_files(section_id)
        if not tts_chunks:
            print(f"[FIX] 节 {section_id} 无可用 TTS 分块音频，无法重建")
            return False

        num_chunks = len(tts_chunks)
        chunk_durations = [d for _, d in tts_chunks]
        total_duration = sum(chunk_durations)

        # 计算每个 TTS 块对应的字符范围和时间范围
        chunk_ranges = compute_tts_chunk_char_ranges(total_chars, num_chunks, chunk_durations)

        # 构建时间范围（累计偏移）
        chunk_time_ranges = []  # [(start_time, end_time), ...]
        time_offset = 0.0
        for i, (_, d) in enumerate(tts_chunks):
            chunk_time_ranges.append((time_offset, time_offset + d))
            time_offset += d

        print(f"[FIX] 节 {section_id}: 文本={total_chars}字, "
              f"TTS块={num_chunks}个, 总时长={total_duration:.1f}s")
        print(f"[FIX] TTS 块映射:")
        for i, ((fp, d), (cs, ce), (ts, te)) in enumerate(zip(tts_chunks, chunk_ranges, chunk_time_ranges)):
            basename = os.path.basename(fp)
            print(f"[FIX]   块{i} ({basename}): "
                  f"字[{cs}:{ce}]={ce-cs}字, "
                  f"时间[{ts:.1f}s:{te:.1f}s]={d:.1f}s")

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

            # 检查是否已有数据
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
                print(f"[FIX] 跳过 segment {seg_id}#{seg_num}: 已有 {len(existing_timeline)} 点 (force=True 覆盖)")
                continue

            if existing_timeline and len(existing_timeline) > 0 and force:
                print(f"[FIX] 🔄 force 覆盖 segment {seg_id}#{seg_num} 的 {len(existing_timeline)} 个旧点")

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

            # === 核心：确定这个 segment 跨了哪些 TTS 块 ===
            chunk_sources = []
            seg_start_time = None
            seg_end_time = None

            for i, ((fp, _d), (cs, ce), (ts, te)) in enumerate(
                zip(tts_chunks, chunk_ranges, chunk_time_ranges)):

                # 计算 segment 和 TTS 块之间的字符重叠
                overlap_start = max(start_char, cs)
                overlap_end = min(end_char, ce)
                overlap_chars = max(0, overlap_end - overlap_start)

                if overlap_chars <= 0:
                    continue  # 这个 TTS 块与当前 segment 无重叠

                # 计算需要的时间裁剪范围
                # 该 TTS 块内，segment 占据的比例
                chunk_total_chars = ce - cs
                if chunk_total_chars > 0:
                    ratio_start = (overlap_start - cs) / chunk_total_chars
                    ratio_end = (overlap_end - cs) / chunk_total_chars
                else:
                    ratio_start = 0.0
                    ratio_end = 1.0

                # 时间裁剪点（相对于这个 TTS 块的开始时间）
                t_clip_start = ts + ratio_start * _d
                t_clip_end = ts + ratio_end * _d

                # 如果几乎占满整个块（>95%），不做裁剪以避免精度损失
                use_whole = (ratio_start <= 0.01 and ratio_end >= 0.99)

                if use_whole:
                    chunk_sources.append((fp, None, None))
                else:
                    chunk_sources.append((fp, t_clip_start, t_clip_end))

                # 记录 segment 的绝对时间范围
                if seg_start_time is None:
                    seg_start_time = t_clip_start if not use_whole else ts
                seg_end_time = t_clip_end if not use_whole else te

            if not chunk_sources:
                print(f"[FIX] 跳过 segment {seg_id}#{seg_num}: 无匹配的 TTS 块")
                continue

            # === 用 ffmpeg 重建该 segment 的音频文件 ===
            segment_filename = f'segment_{section_id}_{seg_num}.mp3'
            segment_filepath = os.path.join(AUDIO_FILES_DIR, segment_filename)

            success, actual_dur = build_segment_audio_ffmpeg(segment_filepath, chunk_sources)

            if not success or actual_dur <= 0:
                print(f"[FIX] ⚠️ segment {seg_id}#{seg_num}: 重建音频失败")
                continue

            new_audio_path = f'/api/audio/{segment_filename}'

            # 生成新的 char_timeline（相对于新建的分段音频，从 0 开始）
            new_timeline = build_char_timeline(seg_clean, actual_dur)

            if new_timeline:
                cursor.execute(
                    'UPDATE text_segments SET audio_path = %s, audio_duration = %s, char_timeline = %s '
                    'WHERE id = %s',
                    (new_audio_path, actual_dur, json.dumps(new_timeline), seg_id)
                )

                changed_path = '' if new_audio_path == old_audio_path else f'路径: {old_audio_path} → {new_audio_path}'
                fixed_count += 1
                chunks_used = len(chunk_sources)
                print(f"[FIX] ✅ segment {seg_id}#{seg_num}: "
                      f"字[{start_char}:{end_char}]={seg_char_count}字 → "
                      f"{segment_filename} ({actual_dur:.1f}s, "
                      f"由{chunks_used}个TTS块拼接{f' ({changed_path})' if changed_path else ''}), "
                      f"timeline={len(new_timeline)}点")
            else:
                print(f"[FIX] ⚠️ segment {seg_id}#{seg_num}: 无法生成 timeline")

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


def main():
    print("="*60)
    print("char_timeline 修复工具 v6 — 重建分段音频文件")
    print("使用现有 TTS 音频块 ffmpeg 拼接，零 TTS 费用")
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


if __name__ == '__main__':
    main()
