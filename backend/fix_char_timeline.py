#!/usr/bin/env python3
"""
修复脚本：为已有音频但 char_timeline 为空的 text_segments 重新生成 char_timeline

特点：
- 不调用 TTS API（零费用）
- 不重新生成音频（零时间）
- 只修复数据库记录
- 支持从磁盘音频文件读取真实时长（解决 audio_duration=0 的数据问题）
"""

import os
import sys
import json
import struct

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
            # 尝试从 ID3v1 标签前的最后一帧计算（适用于 CBR）
            # 简单方案：搜索 MPEG 帧头
            f.seek(-128, 2)
            data = f.read(128)

            # 检查是否有 ID3v1 标签
            has_id3v1 = data[:3] == b'TAG'
            if has_id3v1:
                f.seek(-256, 2)
            else:
                f.seek(0)

            # 从文件末尾往前找有效的帧头
            # 更可靠的方法：扫描文件找第一个有效帧头
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

            # 解析帧头
            first_frame_header = header + f.read(4 - len(header))
            if len(first_frame_header) < 4:
                return None

            b1 = first_frame_header[1] & 0xE0
            version = (first_frame_header[1] >> 3) & 0x03

            # MPEG Version
            if version in (2, 3):  # v1
                bitrate_idx = (first_frame_header[2] >> 4) & 0x0F
                sample_rate_idx = (first_frame_header[3] >> 2) & 0x03
                padding = (first_frame_header[3] >> 1) & 0x01
            else:  # v2 / reserved
                return None

            # 位率表（kbps）- Layer III
            bitrates_v1l3 = [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320,0]
            sample_rates_v1 = [44100,48000,32000,0]

            bitrate = bitrates_v1l3[bitrate_idx] * 1000
            sample_rate = sample_rates_v1[sample_rate_idx]

            if bitrate == 0 or sample_rate == 0:
                return None

            # 计算帧长和总时长
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

            # 每帧采样数
            samples_per_frame = 1152  # MPEG1 Layer III
            duration = (num_frames * samples_per_frame) / float(sample_rate)

            return round(duration, 3)

    except Exception as e:
        print(f"[FIX] 读取音频时长失败 {filepath}: {e}")
        return None


def resolve_audio_file_path(audio_path, segment_number=None):
    """
    将 API 路径解析为实际的音频文件路径。

    如果 audio_path 在数据库中全部相同（数据问题），
    则尝试用 segment_number 匹配正确的文件。
    """
    if not audio_path:
        return None

    # 从 API 路径提取文件名，如 /api/audio/section_662_0.mp3 -> section_662_0.mp3
    basename = os.path.basename(audio_path)
    filepath = os.path.join(AUDIO_FILES_DIR, basename)

    if os.path.exists(filepath):
        return filepath

    # 文件不存在，尝试用 segment_number 推测正确文件名
    if segment_number is not None and '_' in basename:
        parts = basename.rsplit('_', 1)
        if len(parts) == 2:
            base_name = parts[0]
            ext = os.path.splitext(parts[1])[1] or '.mp3'
            guessed_name = base_name + '_' + str(segment_number) + ext
            guessed_path = os.path.join(AUDIO_FILES_DIR, guessed_name)
            if os.path.exists(guessed_path):
                return guessed_path

            # 也试试不带扩展名的编号
            for i in range(20):
                alt_name = base_name + '_' + str(i) + ext
                alt_path = os.path.join(AUDIO_FILES_DIR, alt_name)
                if os.path.exists(alt_path):
                    return alt_path

    return None


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
            seg_num = seg.get('segment_number', 0)
            audio_path = seg.get('audio_path', '')
            audio_duration = float(seg.get('audio_duration') or 0)
            char_timeline = seg.get('char_timeline', '')

            # 尝试获取实际音频时长
            real_duration = audio_duration

            # 如果数据库中的时长为 0，尝试从磁盘文件读取
            if audio_duration <= 0 and audio_path:
                resolved_path = resolve_audio_file_path(audio_path, seg_num)
                if resolved_path:
                    file_duration = get_mp3_duration(resolved_path)
                    if file_duration and file_duration > 0:
                        real_duration = file_duration
                        print(f"[FIX] segment {seg_id}: 数据库时长={audio_duration}, "
                              f"从文件读取实际时长={real_duration}s ({os.path.basename(resolved_path)})")

            if not audio_path:
                print(f"[FIX] 跳过 segment {seg_id}: 无音频路径")
                continue

            if real_duration <= 0:
                print(f"[FIX] 跳过 segment {seg_id}: 无法确定音频时长 (db={audio_path})")
                continue

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

            if existing_timeline and len(existing_timeline) > 0:
                print(f"[FIX] 跳过 segment {seg_id}: char_timeline 已有 {len(existing_timeline)} 个时间点")
                continue

            # 获取该段的内容
            seg_content = seg.get('content', '')
            if not seg_content and section_content:
                start_char = seg.get('start_char', 0)
                end_char = seg.get('end_char', 0)
                seg_content = section_content[start_char:end_char]

            # 重新生成 char_timeline
            new_timeline = rebuild_char_timeline(seg_content, real_duration)

            if new_timeline:
                # 更新数据库：同时修复 char_timeline 和 audio_duration
                update_sql = 'UPDATE text_segments SET char_timeline = %s WHERE id = %s'
                update_params = (json.dumps(new_timeline), seg_id)

                # 如果是从文件读取的时长，顺便更新数据库的 audio_duration
                if real_duration != audio_duration:
                    update_sql = ('UPDATE text_segments SET char_timeline = %s, '
                                 'audio_duration = %s WHERE id = %s')
                    update_params = (json.dumps(new_timeline), real_duration, seg_id)

                cursor.execute(update_sql, update_params)
                fixed_count += 1
                duration_note = f" (更新时长 {audio_duration}→{real_duration}s)" if real_duration != audio_duration else ""
                print(f"[FIX] ✅ 修复 segment {seg_id}: 生成 {len(new_timeline)} 字符时间点, "
                      f"时长={real_duration}s{duration_note}")
            else:
                print(f"[FIX] 跳过 segment {seg_id}: 无法生成 char_timeline")

        conn.commit()
        print(f"[FIX] 节 {section_id} 修复完成，共修复 {fixed_count}/{len(segments)} 个 segments")
        return True

    except Exception as e:
        import traceback
        print(f"[FIX] 修复节 {section_id} 失败: {e}")
        traceback.print_exc()
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

    print(f"\n[FIX] 书籍 {book_id} 修复完成，共处理 {total_fixed} 个节")


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
    print("增强：支持从磁盘音频文件读取真实时长")
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
