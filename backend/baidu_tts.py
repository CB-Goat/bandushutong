"""
伴读书童 - 百度 TTS 语音合成服务
支持 Web Speech API 降级到百度云端 TTS
"""

import os
import json
import time
import hashlib
import requests
from datetime import datetime

# 百度 TTS 配置（通过环境变量或直接填写）
BAIDU_TTS_APP_ID = os.environ.get('BAIDU_TTS_APP_ID', '')
BAIDU_TTS_API_KEY = os.environ.get('BAIDU_TTS_API_KEY', '')
BAIDU_TTS_SECRET_KEY = os.environ.get('BAIDU_TTS_SECRET_KEY', '')

# 百度 TTS API
BAIDU_TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
BAIDU_TTS_URL = 'https://tsn.baidu.com/text2audio'

# 音频文件保存目录
AUDIO_DIR = os.path.join(os.path.dirname(__file__), '..', 'audio_files')
os.makedirs(AUDIO_DIR, exist_ok=True)

# 缓存 access_token
_cached_token = ''
_token_expire_time = 0


def get_access_token():
    """获取百度 API access_token"""
    global _cached_token, _token_expire_time
    
    # 如果 token 还没过期，直接返回
    if _cached_token and time.time() < _token_expire_time:
        return _cached_token
    
    if not BAIDU_TTS_APP_ID or not BAIDU_TTS_API_KEY or not BAIDU_TTS_SECRET_KEY:
        print("警告：未配置百度 TTS 密钥")
        return None
    
    try:
        params = {
            'grant_type': 'client_credentials',
            'client_id': BAIDU_TTS_API_KEY,
            'client_secret': BAIDU_TTS_SECRET_KEY
        }
        response = requests.post(BAIDU_TOKEN_URL, params=params, timeout=10)
        result = response.json()
        
        if 'access_token' in result:
            _cached_token = result['access_token']
            _token_expire_time = time.time() + result.get('expires_in', 2592000) - 600
            print("百度 TTS token 获取成功")
            return _cached_token
        else:
            print(f"获取 token 失败: {result}")
            return None
    except Exception as e:
        print(f"获取 token 异常: {e}")
        return None


def text_to_speech(text, section_id=None, speed=5, pitch=5, volume=5, person=3):
    """
    调用百度 TTS 合成语音
    
    参数:
        text: 要合成的文本（最多1024字节）
        section_id: 小节ID（用于缓存文件名）
        speed: 语速 0-15，默认5
        pitch: 音调 0-15，默认5
        volume: 音量 0-15，默认5
        person: 发音人选择
            0: 普通女声（默认）
            1: 普通男声
            3: 情感合成-度逍遥
            4: 情感合成-度丫丫
            5: 情感合成-度小娇
            103: 情感合成-度米朵
            106: 情感合成-度小萌
            111: 情感合成-度小甜
    
    返回:
        audio_path: 音频文件路径，失败返回 None
    """
    token = get_access_token()
    if not token:
        return None
    
    # 百度 TTS 单次最多 1024 字节，需要分段
    # 先尝试直接合成
    try:
        params = {
            'tok': token,
            'tex': text,
            'per': person,
            'spd': speed,
            'pit': pitch,
            'vol': volume,
            'aue': 3,  # MP3 格式
            'cuid': 'bandushutong_app',
            'lan': 'zh',
            'ctp': 1
        }
        
        response = requests.post(BAIDU_TTS_URL, params=params, timeout=30)
        
        content_type = response.headers.get('Content-Type', '')
        
        if 'audio' in content_type:
            # 成功返回音频
            if section_id:
                filename = f'section_{section_id}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return f'audio_files/{filename}'
            else:
                # 临时文件
                filename = f'temp_{int(time.time())}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return f'audio_files/{filename}'
        else:
            # 返回了错误信息
            result = response.json()
            print(f"百度 TTS 错误: {result}")
            return None
            
    except Exception as e:
        print(f"百度 TTS 异常: {e}")
        return None


def text_to_speech_long(text, section_id=None, speed=5, pitch=5, volume=5, person=3):
    """
    合成长文本（自动分段合成）
    百度 TTS 单次最多 1024 字节（约 500 个中文字符）
    
    返回: 音频文件路径列表
    """
    # 按句号分段，每段不超过 500 字符
    segments = []
    current = ''
    for char in text:
        current += char
        if len(current.encode('utf-8')) >= 900 or char in '。！？\n':
            if current.strip():
                segments.append(current.strip())
            current = ''
    if current.strip():
        segments.append(current.strip())
    
    if not segments:
        return []
    
    # 合成每段
    audio_paths = []
    for i, seg in enumerate(segments):
        path = text_to_speech(seg, 
                              section_id=f'{section_id}_{i}' if section_id else None,
                              speed=speed, pitch=pitch, volume=volume, person=person)
        if path:
            audio_paths.append(path)
    
    return audio_paths


def is_configured():
    """检查百度 TTS 是否已配置"""
    return bool(BAIDU_TTS_APP_ID and BAIDU_TTS_API_KEY and BAIDU_TTS_SECRET_KEY)


def generate_section_audio_with_timeline(text, section_id, speed=5, person=3):
    """
    生成节的完整音频并计算字符时间轴
    
    返回: {
        'audio_path': 音频文件路径,
        'audio_duration': 音频时长（秒）,
        'char_timeline': [每个字符显示的时间点数组]
    }
    """
    import subprocess
    import math
    
    token = get_access_token()
    if not token:
        return None
    
    # 分段处理（每段约 500 字符）
    segments = []
    current = ''
    for char in text:
        current += char
        if len(current.encode('utf-8')) >= 900 or char in '。！？\n':
            if current.strip():
                segments.append(current.strip())
            current = ''
    if current.strip():
        segments.append(current.strip())
    
    if not segments:
        return None
    
    # 计算每段对应的字符范围
    char_ranges = []
    char_pos = 0
    for seg in segments:
        seg_chars = len(seg)
        char_ranges.append((char_pos, char_pos + seg_chars))
        char_pos += seg_chars
    
    # 合成所有段，同时记录每段时长
    audio_files = []
    segment_durations = []  # 每段音频的实际时长
    
    for i, seg in enumerate(segments):
        params = {
            'tok': token,
            'tex': seg,
            'per': person,
            'spd': speed,
            'pit': 5,
            'vol': 5,
            'aue': 3,
            'cuid': 'bandushutong_app',
            'lan': 'zh',
            'ctp': 1
        }
        
        try:
            response = requests.post(BAIDU_TTS_URL, params=params, timeout=30)
            content_type = response.headers.get('Content-Type', '')
            
            if 'audio' in content_type:
                filename = f'section_{section_id}_{i}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                audio_files.append(filepath)
                
                # 获取该段音频的实际时长
                seg_duration = 0
                try:
                    dur_result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    seg_duration = float(dur_result.stdout.strip())
                except:
                    # 估算：按每分钟200字
                    seg_duration = len(seg) / 200 * 60
                segment_durations.append(seg_duration)
            else:
                print(f"段 {i} 合成失败: {response.text}")
                return None
        except Exception as e:
            print(f"段 {i} 合成异常: {e}")
            return None
    
    # 合并音频文件（使用 Python 直接拼接，避免 ffmpeg 兼容问题）
    final_path = os.path.join(AUDIO_DIR, f'section_{section_id}.mp3')
    
    if len(audio_files) == 1:
        os.rename(audio_files[0], final_path)
        print(f"[TTS] 单段音频，直接重命名")
    else:
        print(f"[TTS] 开始合并 {len(audio_files)} 个音频段...")
        try:
            with open(final_path, 'wb') as outfile:
                for af in audio_files:
                    with open(af, 'rb') as infile:
                        outfile.write(infile.read())
            print(f"[TTS] 合并成功: {final_path}")
            # 删除临时文件
            for af in audio_files:
                os.remove(af)
            list_file = os.path.join(AUDIO_DIR, f'section_{section_id}_list.txt')
            if os.path.exists(list_file):
                os.remove(list_file)
        except Exception as e:
            print(f"[TTS] 合并异常: {e}")
            return None
    
    # 计算总时长
    audio_duration = sum(segment_durations)
    
    # 基于每段实际时长构建精确字符时间轴
    char_timeline = []
    for seg_idx, seg in enumerate(segments):
        start_char = char_ranges[seg_idx][0]
        end_char = char_ranges[seg_idx][1]
        seg_len = end_char - start_char
        seg_dur = segment_durations[seg_idx] if seg_idx < len(segment_durations) else 1
        
        # 该段之前的累计时长
        time_offset = sum(segment_durations[:seg_idx])
        
        # 该段内每个字符的时间点
        if seg_len > 0 and seg_dur > 0:
            for j in range(seg_len):
                t = time_offset + (j / seg_len) * seg_dur
                char_timeline.append(round(t, 3))
    
    print(f"[TTS] 时间轴构建完成: {len(char_timeline)} 个字符, 总时长 {audio_duration:.1f}s")
    
    return {
        'audio_path': f'/api/audio/section_{section_id}.mp3',
        'audio_duration': audio_duration,
        'char_timeline': char_timeline
    }


def generate_segmented_audio(text, section_id, annotations, speed=5, person=3):
    """
    按点评边界分割原文为多段，每段独立生成音频。
    
    参数:
        text: 原文内容
        section_id: 节ID
        annotations: 该节的点评列表，按 end_char 排序，例如:
            [{'id': 119, 'start_char': 46, 'end_char': 80}, ...]
        speed: 语速
        person: 音色
    
    返回: {
        'audio_segments': [
            {
                'type': 'original',
                'audio_path': '/api/audio/segment_{section_id}_0.mp3',
                'audio_duration': 10.5,
                'start_char': 0,
                'end_char': 80,
                'char_timeline': [0.0, 0.1, ...]  # 该段内每个字符的时间点
            },
            {
                'type': 'annotation',
                'annotation_id': 119,
                'audio_path': '/api/audio/annotation_119.mp3',
                'audio_duration': 5.0
            },
            ...
        ],
        'audio_path': '/api/audio/section_{section_id}.mp3',  # 完整合并音频（兼容）
        'audio_duration': 75.3,
        'char_timeline': [...]  # 完整时间轴（兼容）
    }
    """
    token = get_access_token()
    if not token:
        return None
    
    # 1. 确定分割点：按点评的 end_char 分割
    split_points = [0]  # 从0开始
    for ann in annotations:
        if ann.get('end_char') and ann['end_char'] > split_points[-1]:
            split_points.append(ann['end_char'])
    split_points.append(len(text))  # 到结尾
    
    # 2. 为每段原文生成独立音频
    audio_segments = []
    full_timeline = []
    full_duration = 0
    
    for seg_idx in range(len(split_points) - 1):
        start_char = split_points[seg_idx]
        end_char = split_points[seg_idx + 1]
        seg_text = text[start_char:end_char]
        
        if not seg_text.strip():
            continue
        
        # 为该段生成音频（复用现有的分段合成逻辑）
        seg_result = _generate_single_segment_audio(
            seg_text, section_id, seg_idx, start_char, speed, person, token
        )
        
        if seg_result:
            audio_segments.append(seg_result)
            full_timeline.extend(seg_result['char_timeline'])
            full_duration += seg_result['audio_duration']
            
            # 如果该段后面有点评，添加点评段
            if seg_idx < len(annotations):
                ann = annotations[seg_idx]
                if ann.get('audio_path'):
                    audio_segments.append({
                        'type': 'annotation',
                        'annotation_id': ann['id'],
                        'audio_path': ann['audio_path'],
                        'audio_duration': ann.get('audio_duration', 0)
                    })
                    full_duration += ann.get('audio_duration', 0)
    
    # 3. 合并所有段为完整音频（兼容旧模式）
    final_path = os.path.join(AUDIO_DIR, f'section_{section_id}.mp3')
    original_segments = [s for s in audio_segments if s['type'] == 'original']
    seg_files = []
    for seg in original_segments:
        # 从 audio_path 提取文件名
        filename = seg['audio_path'].split('/')[-1]
        filepath = os.path.join(AUDIO_DIR, filename)
        if os.path.exists(filepath):
            seg_files.append(filepath)
    
    if seg_files:
        try:
            with open(final_path, 'wb') as outfile:
                for sf in seg_files:
                    with open(sf, 'rb') as infile:
                        outfile.write(infile.read())
            print(f"[TTS] 合并分段音频完成: {final_path}")
        except Exception as e:
            print(f"[TTS] 合并分段音频失败: {e}")
    
    # 4. 添加小结段（如果有）
    # 小结音频在 generate_book_audio 中单独生成，这里不处理
    
    return {
        'audio_segments': audio_segments,
        'audio_path': f'/api/audio/section_{section_id}.mp3',
        'audio_duration': full_duration,
        'char_timeline': full_timeline
    }


def _generate_single_segment_audio(text, section_id, seg_idx, start_char, speed, person, token):
    """
    为单段文本生成音频，返回分段信息。
    
    返回: {
        'type': 'original',
        'audio_path': '/api/audio/segment_{section_id}_{seg_idx}.mp3',
        'audio_duration': 10.5,
        'start_char': 0,
        'end_char': 80,
        'char_timeline': [0.0, 0.1, ...]
    } 或 None
    """
    import subprocess
    
    # 按 TTS 限制分段（每段约 500 字符）
    sub_segments = []
    current = ''
    for char in text:
        current += char
        if len(current.encode('utf-8')) >= 900 or char in '。！？\n':
            if current.strip():
                sub_segments.append(current.strip())
            current = ''
    if current.strip():
        sub_segments.append(current.strip())
    
    if not sub_segments:
        return None
    
    # 计算每段对应的字符范围（相对于该段的起始位置）
    char_ranges = []
    char_pos = 0
    for seg in sub_segments:
        seg_chars = len(seg)
        char_ranges.append((char_pos, char_pos + seg_chars))
        char_pos += seg_chars
    
    # 合成所有子段
    audio_files = []
    segment_durations = []
    
    for i, seg in enumerate(sub_segments):
        params = {
            'tok': token,
            'tex': seg,
            'per': person,
            'spd': speed,
            'pit': 5,
            'vol': 5,
            'aue': 3,
            'cuid': 'bandushutong_app',
            'lan': 'zh',
            'ctp': 1
        }
        
        try:
            response = requests.post(BAIDU_TTS_URL, params=params, timeout=30)
            content_type = response.headers.get('Content-Type', '')
            
            if 'audio' in content_type:
                filename = f'segment_{section_id}_{seg_idx}_{i}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                audio_files.append(filepath)
                
                seg_duration = 0
                try:
                    dur_result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    seg_duration = float(dur_result.stdout.strip())
                except:
                    seg_duration = len(seg) / 200 * 60
                segment_durations.append(seg_duration)
            else:
                print(f"子段 {seg_idx}-{i} 合成失败: {response.text}")
                return None
        except Exception as e:
            print(f"子段 {seg_idx}-{i} 合成异常: {e}")
            return None
    
    # 合并子段为该段的完整音频
    final_filename = f'segment_{section_id}_{seg_idx}.mp3'
    final_path = os.path.join(AUDIO_DIR, final_filename)
    
    if len(audio_files) == 1:
        os.rename(audio_files[0], final_path)
    else:
        with open(final_path, 'wb') as outfile:
            for af in audio_files:
                with open(af, 'rb') as infile:
                    outfile.write(infile.read())
        for af in audio_files:
            os.remove(af)
    
    # 计算该段的总时长
    seg_total_duration = sum(segment_durations)
    
    # 构建该段的字符时间轴（相对于该段音频的起始时间）
    char_timeline = []
    for sub_idx, seg in enumerate(sub_segments):
        sub_start = char_ranges[sub_idx][0]
        sub_end = char_ranges[sub_idx][1]
        sub_len = sub_end - sub_start
        sub_dur = segment_durations[sub_idx] if sub_idx < len(segment_durations) else 1
        time_offset = sum(segment_durations[:sub_idx])
        
        if sub_len > 0 and sub_dur > 0:
            for j in range(sub_len):
                t = time_offset + (j / sub_len) * sub_dur
                char_timeline.append(round(t, 3))
    
    end_char = start_char + len(text)
    
    print(f"[TTS] 分段 {seg_idx} 完成: chars {start_char}-{end_char}, 时长 {seg_total_duration:.1f}s")
    
    return {
        'type': 'original',
        'audio_path': f'/api/audio/segment_{section_id}_{seg_idx}.mp3',
        'audio_duration': seg_total_duration,
        'start_char': start_char,
        'end_char': end_char,
        'char_timeline': char_timeline
    }


def generate_book_audio(book_id, person=3, speed=5):
    """
    为书籍的所有节预生成音频（后台线程调用）
    包括：原文音频、点评音频、小结音频
    """
    import sys
    import threading
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.database import get_sections_by_book, update_section_audio_timeline, update_book_tts_status, get_annotations_by_section, update_annotation_audio, update_section_summary_audio

    def _generate():
        if not is_configured():
            update_book_tts_status(book_id, 'error', 'TTS未配置')
            return

        sections = get_sections_by_book(book_id)
        if not sections:
            update_book_tts_status(book_id, 'error', '无节内容')
            return

        total = len(sections)
        update_book_tts_status(book_id, 'generating', f'0/{total}')
        print(f"[TTS] 开始为书籍 {book_id} 生成 {total} 个节的音频...")

        done_count = 0
        for i, section in enumerate(sections):
            section_id = section['id']
            content = section.get('content', '')

            # 跳过已有音频的节
            if section.get('has_audio') and section.get('audio_path') and section.get('audio_duration', 0) > 0:
                done_count += 1
                update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                continue

            if not content or len(content.strip()) == 0:
                done_count += 1
                update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                continue

            try:
                # 1. 生成原文音频
                result = generate_section_audio_with_timeline(content, section_id, speed=speed, person=person)
                if result:
                    update_section_audio_timeline(section_id, result['audio_duration'], result['char_timeline'], result['audio_path'])
                    print(f"[TTS] 节 {section_id} 原文音频完成")
                    
                    # 2. 生成所有点评音频
                    annotations = get_annotations_by_section(section_id)
                    for ann in annotations:
                        ann_result = generate_annotation_audio(
                            ann['id'], 
                            ann['original_text'], 
                            ann['comment'],
                            person=person, 
                            speed=speed
                        )
                        if ann_result:
                            update_annotation_audio(ann['id'], ann_result['audio_path'], ann_result['audio_duration'])
                            print(f"[TTS] 点评 {ann['id']} 音频完成")
                    
                    # 3. 生成小结音频
                    summary = section.get('summary', '')
                    if summary:
                        sum_result = generate_summary_audio(section_id, summary, person=person, speed=speed)
                        if sum_result:
                            update_section_summary_audio(section_id, sum_result['audio_path'], sum_result['audio_duration'])
                            print(f"[TTS] 节 {section_id} 小结音频完成")
                    
                    done_count += 1
                    update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                    print(f"[TTS] 节 {section_id} 全部完成 ({done_count}/{total})")
                else:
                    done_count += 1
                    update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                    print(f"[TTS] 节 {section_id} 失败")
            except Exception as e:
                done_count += 1
                update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                print(f"[TTS] 节 {section_id} 异常: {e}")

            time.sleep(0.3)

        update_book_tts_status(book_id, 'done', f'{total}/{total}')
        print(f"[TTS] 书籍 {book_id} 音频生成完成")

    # 后台线程执行
    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()
    return True


def generate_annotation_audio(annotation_id, original_text, comment, person=3, speed=5):
    """
    生成点评音频
    格式：点评内容（不再重复读原文，因为原文已经在触发点评前播放过了）
    
    返回: {'audio_path': 路径, 'audio_duration': 时长} 或 None
    """
    import subprocess
    
    token = get_access_token()
    if not token:
        return None
    
    # 构建点评文本（不包含原文引用，避免重复）
    text = f"{comment}"
    
    # 分段处理
    segments = []
    current = ''
    for char in text:
        current += char
        if len(current.encode('utf-8')) >= 900 or char in '。！？\n':
            if current.strip():
                segments.append(current.strip())
            current = ''
    if current.strip():
        segments.append(current.strip())
    
    if not segments:
        return None
    
    # 合成所有段
    audio_files = []
    segment_durations = []
    
    for i, seg in enumerate(segments):
        params = {
            'tok': token,
            'tex': seg,
            'per': person,
            'spd': speed,
            'pit': 5,
            'vol': 5,
            'aue': 3,
            'cuid': 'bandushutong_app',
            'lan': 'zh',
            'ctp': 1
        }
        
        try:
            response = requests.post(BAIDU_TTS_URL, params=params, timeout=30)
            content_type = response.headers.get('Content-Type', '')
            
            if 'audio' in content_type:
                filename = f'annotation_{annotation_id}_{i}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                audio_files.append(filepath)
                
                # 获取该段音频的实际时长
                seg_duration = 0
                try:
                    dur_result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    seg_duration = float(dur_result.stdout.strip())
                except:
                    seg_duration = len(seg) / 200 * 60
                segment_durations.append(seg_duration)
            else:
                print(f"[TTS] 点评段 {i} 合成失败: {response.text}")
                return None
        except Exception as e:
            print(f"[TTS] 点评段 {i} 合成异常: {e}")
            return None
    
    # 合并音频文件
    final_path = os.path.join(AUDIO_DIR, f'annotation_{annotation_id}.mp3')
    
    if len(audio_files) == 1:
        os.rename(audio_files[0], final_path)
    else:
        try:
            with open(final_path, 'wb') as outfile:
                for af in audio_files:
                    with open(af, 'rb') as infile:
                        outfile.write(infile.read())
            for af in audio_files:
                os.remove(af)
        except Exception as e:
            print(f"[TTS] 点评音频合并异常: {e}")
            return None
    
    audio_duration = sum(segment_durations)
    print(f"[TTS] 点评音频生成完成: annotation_{annotation_id}.mp3, 时长 {audio_duration:.1f}s")
    
    return {
        'audio_path': f'/api/audio/annotation_{annotation_id}.mp3',
        'audio_duration': audio_duration
    }


def generate_summary_audio(section_id, summary, person=3, speed=5):
    """
    生成小结音频
    格式："让我们回顾一下本篇内容" + 小结内容
    
    返回: {'audio_path': 路径, 'audio_duration': 时长} 或 None
    """
    import subprocess
    
    token = get_access_token()
    if not token:
        return None
    
    # 构建小结文本
    text = f"让我们回顾一下本篇内容。{summary}"
    
    # 分段处理
    segments = []
    current = ''
    for char in text:
        current += char
        if len(current.encode('utf-8')) >= 900 or char in '。！？\n':
            if current.strip():
                segments.append(current.strip())
            current = ''
    if current.strip():
        segments.append(current.strip())
    
    if not segments:
        return None
    
    # 合成所有段
    audio_files = []
    segment_durations = []
    
    for i, seg in enumerate(segments):
        params = {
            'tok': token,
            'tex': seg,
            'per': person,
            'spd': speed,
            'pit': 5,
            'vol': 5,
            'aue': 3,
            'cuid': 'bandushutong_app',
            'lan': 'zh',
            'ctp': 1
        }
        
        try:
            response = requests.post(BAIDU_TTS_URL, params=params, timeout=30)
            content_type = response.headers.get('Content-Type', '')
            
            if 'audio' in content_type:
                filename = f'summary_{section_id}_{i}.mp3'
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                audio_files.append(filepath)
                
                # 获取该段音频的实际时长
                seg_duration = 0
                try:
                    dur_result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    seg_duration = float(dur_result.stdout.strip())
                except:
                    seg_duration = len(seg) / 200 * 60
                segment_durations.append(seg_duration)
            else:
                print(f"[TTS] 小结段 {i} 合成失败: {response.text}")
                return None
        except Exception as e:
            print(f"[TTS] 小结段 {i} 合成异常: {e}")
            return None
    
    # 合并音频文件
    final_path = os.path.join(AUDIO_DIR, f'summary_{section_id}.mp3')
    
    if len(audio_files) == 1:
        os.rename(audio_files[0], final_path)
    else:
        try:
            with open(final_path, 'wb') as outfile:
                for af in audio_files:
                    with open(af, 'rb') as infile:
                        outfile.write(infile.read())
            for af in audio_files:
                os.remove(af)
        except Exception as e:
            print(f"[TTS] 小结音频合并异常: {e}")
            return None
    
    audio_duration = sum(segment_durations)
    print(f"[TTS] 小结音频生成完成: summary_{section_id}.mp3, 时长 {audio_duration:.1f}s")
    
    return {
        'audio_path': f'/api/audio/summary_{section_id}.mp3',
        'audio_duration': audio_duration
    }


if __name__ == '__main__':
    if is_configured():
        print("百度 TTS 已配置")
        result = text_to_speech("你好，这是一个测试。", section_id=999)
        print(f"测试结果: {result}")
    else:
        print("百度 TTS 未配置，请设置环境变量:")
        print("  BAIDU_TTS_APP_ID")
        print("  BAIDU_TTS_API_KEY")
        print("  BAIDU_TTS_SECRET_KEY")
