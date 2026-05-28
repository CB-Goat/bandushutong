"""
悦读小将 - 百度 TTS 语音合成服务
支持 Web Speech API 降级到百度云端 TTS
"""

import os
import json
import time
import hashlib
import requests
from datetime import datetime

# 尝试从 .env 文件加载环境变量
def _load_env_file():
    """从 .env 文件加载环境变量"""
    env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
        '/opt/bandushutong/.env',
        '/opt/bandushutong/backend/.env'
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and value and key not in os.environ:
                                os.environ[key] = value
                                print(f"[ENV] 从 {env_path} 加载: {key}")
            except Exception as e:
                print(f"[ENV] 加载 {env_path} 失败: {e}")
            break

_load_env_file()

# 百度 TTS 配置（通过环境变量或 .env 文件）
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
            0: 普通女声
            1: 普通男声（默认）
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
    
    # 去掉换行符，统一使用显示索引（与前端 _allChars 一致）
    text = text.replace('\n', '')
    
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
    
    # 计算每段对应的字符范围（strip后）
    char_ranges = []
    char_pos = 0
    for seg in segments:
        seg_chars = len(seg)  # strip后的长度
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
    
    # 基于每段实际时长构建精确字符时间轴（不含换行符，与前端一致）
    char_timeline = []
    for seg_idx, seg in enumerate(segments):
        start_char = char_ranges[seg_idx][0]
        end_char = char_ranges[seg_idx][1]
        seg_text = text[start_char:end_char]
        seg_dur = segment_durations[seg_idx] if seg_idx < len(segment_durations) else 1
        
        # 该段之前的累计时长
        time_offset = sum(segment_durations[:seg_idx])
        
        # 该段内每个字符的时间点（跳过换行符）
        visible_chars = [c for c in seg_text if c != '\n']
        seg_len = len(visible_chars)
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
    
    # 去掉换行符，统一使用显示索引（与前端 _allChars 一致）
    text = text.replace('\n', '')
    
    # 1. 确定分割点：按点评的 start_char 和 end_char 分割
    # 建立 start_char 和 end_char 到点评的映射
    ann_by_start_char = {}
    ann_by_end_char = {}
    for ann in annotations:
        if ann.get('start_char') is not None:
            ann_by_start_char[ann['start_char']] = ann
        if ann.get('end_char') is not None:
            ann_by_end_char[ann['end_char']] = ann
    
    # 获取所有唯一的分割点（包括0、所有点评的start_char和end_char、文本结尾）
    split_points = sorted(set([0] + list(ann_by_start_char.keys()) + list(ann_by_end_char.keys()) + [len(text)]))
    
    print(f"[TTS] 分割点: {split_points}")
    print(f"[TTS] 点评映射: {list(ann_by_end_char.keys())}")
    
    # 2. 为每段原文生成独立音频
    audio_segments = []
    full_timeline = []
    full_duration = 0
    
    for seg_idx in range(len(split_points) - 1):
        start_char = split_points[seg_idx]
        next_point = split_points[seg_idx + 1]
        # Python切片是左闭右开的，text[start:next]包含start到next-1
        seg_text = text[start_char:next_point]
        # 段的实际结束字符是next_point-1（最后一个包含的字符）
        actual_end_char = next_point - 1
        
        print(f"[TTS] 处理段 {seg_idx}: chars {start_char}-{actual_end_char}, 长度 {len(seg_text)}")
        
        if not seg_text.strip():
            print(f"[TTS] 段 {seg_idx} 为空，跳过")
            continue
        
        # 为该段生成音频
        # 传入actual_end_char确保段的结束位置正确（next_point-1）
        seg_result = _generate_single_segment_audio(
            seg_text, section_id, seg_idx, start_char, actual_end_char, speed, person, token
        )
        
        if seg_result:
            audio_segments.append(seg_result)
            # 加上前面所有原文段的时间偏移
            time_offset = full_duration
            for t in seg_result['char_timeline']:
                full_timeline.append(round(t + time_offset, 3))
            full_duration += seg_result['audio_duration']
            print(f"[TTS] 段 {seg_idx} 音频生成成功: {seg_result['audio_path']}")
        else:
            print(f"[TTS] 段 {seg_idx} 音频生成失败，跳过")
            # 继续生成其他段，而不是直接返回None
        
        # 查找该段结束位置对应的点评（使用next_point，因为ann_by_end_char的key是点评的end_char）
        if next_point in ann_by_end_char:
            ann = ann_by_end_char[next_point]
            print(f"[TTS] 段 {seg_idx} 结束后有点评 id={ann['id']}")
            # 为点评生成音频
            comment = ann.get('comment', '')
            original_text = ann.get('original_text', '')
            if comment or original_text:
                # 生成引用原文音频（quote）
                if original_text:
                    try:
                        from backend.database import get_db
                        conn = get_db()
                        cursor = conn.cursor()
                        # 为引用原文生成音频（使用 person=0 原文男声）
                        # 使用 quote_{id} 作为文件名，避免与点评音频冲突
                        quote_audio = _generate_quote_audio(ann['id'], original_text, person=0, speed=speed)
                        if quote_audio:
                            quote_audio_path = quote_audio['audio_path']
                            quote_duration = quote_audio['audio_duration']
                            # 更新 insert_points 表的 quote_audio_path
                            cursor.execute(
                                "UPDATE insert_points SET quote_audio_path = ?, quote_audio_duration = ? WHERE section_id = ? AND annotation_id = ?",
                                (quote_audio_path, quote_duration, section_id, ann['id'])
                            )
                            print(f"[TTS] 引用音频生成完成: {quote_audio_path}, 时长 {quote_duration:.1f}s")
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        print(f"[TTS] 生成引用音频失败: {e}")
                # 生成点评音频（comment）
                if comment:
                    ann_audio = generate_annotation_audio(ann['id'], '', comment, person=person, speed=speed)
                    if ann_audio:
                        audio_segments.append({
                            'type': 'annotation',
                            'annotation_id': ann['id'],
                            'audio_path': ann_audio['audio_path'],
                            'audio_duration': ann_audio['audio_duration']
                        })
                        full_duration += ann_audio['audio_duration']
                        # 更新数据库中的点评音频信息（annotations表 + insert_points表）
                        try:
                            from backend.database import update_annotation_audio, get_db
                            update_annotation_audio(ann['id'], ann_audio['audio_path'], ann_audio['audio_duration'])
                            # 同时更新 insert_points 表的 audio_path
                            conn = get_db()
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE insert_points SET audio_path = ?, audio_duration = ? WHERE section_id = ? AND annotation_index = ?",
                                (ann_audio['audio_path'], ann_audio['audio_duration'], section_id, ann['annotation_index'])
                            )
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            print(f"[TTS] 更新点评音频到数据库失败: {e}")
        else:
            print(f"[TTS] 段 {seg_idx} 结束后无点评")
    
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
    # 从数据库获取小结内容
    try:
        from backend.database import get_section, get_db
        section = get_section(section_id)
        if section and section.get('summary'):
            summary_audio = generate_summary_audio(section_id, section['summary'], person=person, speed=speed)
            if summary_audio:
                audio_segments.append({
                    'type': 'summary',
                    'audio_path': summary_audio['audio_path'],
                    'audio_duration': summary_audio['audio_duration']
                })
                full_duration += summary_audio['audio_duration']
                # 更新 insert_points 表中小结的 audio_path
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE insert_points SET audio_path = ?, audio_duration = ? WHERE section_id = ? AND point_type = 'summary'",
                        (summary_audio['audio_path'], summary_audio['audio_duration'], section_id)
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"[TTS] 更新小结音频到insert_points失败: {e}")
    except Exception as e:
        print(f"[TTS] 小结音频生成失败: {e}")
    
    # 5. 更新 text_segments 表的 audio_path
    try:
        from backend.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        # 获取该节的所有 text_segments，按 segment_number 排序
        cursor.execute('SELECT id, segment_number FROM text_segments WHERE section_id = ? ORDER BY segment_number', (section_id,))
        db_segments = {row['segment_number']: row['id'] for row in cursor.fetchall()}
        # 更新每个 original 类型段的 audio_path 和 char_timeline
        for seg in audio_segments:
            if seg['type'] == 'original':
                seg_num = seg.get('segment_number', 0)
                if seg_num in db_segments:
                    char_timeline_json = json.dumps(seg['char_timeline']) if seg.get('char_timeline') else None
                    cursor.execute(
                        'UPDATE text_segments SET audio_path = ?, audio_duration = ?, char_timeline = ? WHERE id = ?',
                        (seg['audio_path'], seg['audio_duration'], char_timeline_json, db_segments[seg_num])
                    )
                    print(f"[TTS] 更新 text_segments id={db_segments[seg_num]} audio_path={seg['audio_path']} char_timeline长度={len(seg.get('char_timeline', []))}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[TTS] 更新 text_segments 音频路径失败: {e}")
    
    return {
        'audio_segments': audio_segments,
        'audio_path': f'/api/audio/section_{section_id}.mp3',
        'audio_duration': full_duration,
        'char_timeline': full_timeline
    }


def _generate_single_segment_audio(text, section_id, seg_idx, start_char, actual_end_char, speed, person, token):
    """
    为单段文本生成音频，返回分段信息。
    
    参数:
        text: 该段的原始文本
        section_id: 节ID
        seg_idx: 段索引
        start_char: 该段在原文中的起始字符位置（包含）
        actual_end_char: 该段在原文中的结束字符位置（包含）
        speed: 语速
        person: 音色
        token: 百度TTS token
    
    返回: {
        'type': 'original',
        'audio_path': '/api/audio/segment_{section_id}_{seg_idx}.mp3',
        'audio_duration': 10.5,
        'start_char': 0,
        'end_char': 79,  # 注意：这是包含的结束位置
        'char_timeline': [0.0, 0.1, ...]
    } 或 None
    """
    import subprocess
    
    # 按 TTS 限制分段（每段约 500 字符）
    # 注意：保留原始文本，不要 strip()，否则字符数会不匹配
    sub_segments = []
    current = ''
    for char in text:
        current += char
        if len(current.encode('utf-8')) >= 900 or char in '。！？\n':
            if current:
                sub_segments.append(current)
            current = ''
    if current:
        sub_segments.append(current)
    
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
                error_text = response.text[:200] if response.text else '无错误信息'
                print(f"[TTS] 子段 {seg_idx}-{i} 合成失败: status={response.status_code}, content-type={content_type}, error={error_text}")
                return None
        except Exception as e:
            print(f"[TTS] 子段 {seg_idx}-{i} 合成异常: {type(e).__name__}: {e}")
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
    
    # 使用传入的actual_end_char，确保段的结束位置正确
    # 验证actual_end_char与text长度是否匹配
    expected_end = start_char + len(text) - 1
    if actual_end_char != expected_end:
        print(f"[TTS] 警告: 分段 {seg_idx} actual_end_char({actual_end_char}) != expected({expected_end})")
    
    print(f"[TTS] 分段 {seg_idx} 完成: chars {start_char}-{actual_end_char}, 时长 {seg_total_duration:.1f}s")
    
    return {
        'type': 'original',
        'segment_number': seg_idx,
        'audio_path': f'/api/audio/segment_{section_id}_{seg_idx}.mp3',
        'audio_duration': seg_total_duration,
        'start_char': start_char,
        'end_char': actual_end_char,
        'char_timeline': char_timeline
    }


def generate_book_audio(book_id, person=3, speed=5):
    """
    为书籍的所有节预生成音频（后台线程调用）
    新版：基于 text_segments + insert_points 架构
    """
    import sys
    import threading
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.database import get_sections_by_book, update_book_tts_status, check_section_audio_complete

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

            # 跳过已有完整音频的节
            if check_section_audio_complete(section_id):
                done_count += 1
                update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                print(f"[TTS] 节 {section_id} 已有音频，跳过")
                continue

            if not content or len(content.strip()) == 0:
                done_count += 1
                update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                continue

            try:
                # 使用新版音频生成（基于 text_segments + insert_points）
                result = generate_section_audio_v2(section_id, speed=speed, person=person)
                if result:
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
                import traceback
                traceback.print_exc()

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


def _generate_quote_audio(annotation_id, original_text, person=3, speed=5):
    """
    生成引用原文音频
    格式：直接朗读原文，不加前缀
    
    返回: {'audio_path': 路径, 'audio_duration': 时长} 或 None
    """
    import subprocess
    
    token = get_access_token()
    if not token:
        return None
    
    # 直接使用原文
    text = original_text
    
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
                filename = f'quote_{annotation_id}_{i}.mp3'
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
                print(f"[TTS] 引用段 {i} 合成失败: {response.text}")
                return None
        except Exception as e:
            print(f"[TTS] 引用段 {i} 合成异常: {e}")
            return None
    
    # 合并音频文件
    final_path = os.path.join(AUDIO_DIR, f'quote_{annotation_id}.mp3')
    
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
            print(f"[TTS] 引用音频合并异常: {e}")
            return None
    
    audio_duration = sum(segment_durations)
    print(f"[TTS] 引用音频生成完成: quote_{annotation_id}.mp3, 时长 {audio_duration:.1f}s")
    
    return {
        'audio_path': f'/api/audio/quote_{annotation_id}.mp3',
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


# ==================== 新版音频生成辅助函数 ====================

def call_baidu_tts(text, token, speed=5, person=3):
    """调用百度 TTS API，返回音频字节数据"""
    params = {
        'tok': token,
        'tex': text,
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
            return response.content
        else:
            print(f"[TTS] call_baidu_tts 错误: {response.text}")
            return None
    except Exception as e:
        print(f"[TTS] call_baidu_tts 异常: {e}")
        return None


def get_audio_duration_and_timeline(audio_path, text):
    """获取音频时长和字符时间轴"""
    import subprocess

    # 获取音频时长
    audio_duration = 0
    try:
        dur_result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        audio_duration = float(dur_result.stdout.strip())
    except:
        audio_duration = len(text) / 200 * 60

    # 构建字符时间轴（均匀分布）
    char_timeline = []
    text_len = len(text)
    if text_len > 0 and audio_duration > 0:
        for j in range(text_len):
            t = (j / text_len) * audio_duration
            char_timeline.append(round(t, 3))

    return audio_duration, char_timeline


# ==================== 新版音频生成（基于 text_segments） ====================

def generate_text_segment_audio(text, segment_id, speed=5, person=3):
    """为单个 text_segment 生成音频"""
    token = get_access_token()
    if not token:
        return None
    
    if not text or len(text.strip()) == 0:
        return None
    
    # 调用百度TTS
    result = call_baidu_tts(text, token, speed=speed, person=person)
    if not result:
        return None

    audio_path = os.path.join(AUDIO_DIR, f'segment_{segment_id}.mp3')
    with open(audio_path, 'wb') as f:
        f.write(result)

    # 获取音频时长和字符时间轴
    audio_duration, char_timeline = get_audio_duration_and_timeline(audio_path, text)

    return {
        'audio_path': f'/api/audio/segment_{segment_id}.mp3',
        'audio_duration': audio_duration,
        'char_timeline': char_timeline
    }

def generate_fixed_audio_files(speed=5, person=3):
    """生成系统固定音频文件（开场白、结束语）"""
    token = get_access_token()
    if not token:
        return False
    
    files = {
        'annotation_opening.mp3': '我们来看下这里：',
        'annotation_closing.mp3': '回到原文',
        'summary_opening.mp3': '这篇内容已读完，我们回顾一下：',
        'summary_closing.mp3': '小结之外有其他思考，请添加到右上角。'
    }
    
    for filename, text in files.items():
        audio_path = os.path.join(AUDIO_DIR, filename)
        # 如果已存在且不为空，跳过
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            print(f"[TTS] 固定音频已存在: {filename}")
            continue
        
        result = call_baidu_tts(text, token, speed=speed, person=person)
        if result:
            with open(audio_path, 'wb') as f:
                f.write(result)
            print(f"[TTS] 生成固定音频: {filename}")
        else:
            print(f"[TTS] 生成固定音频失败: {filename}")
    
    return True

def get_fixed_audio_path(filename):
    """获取固定音频文件的URL路径"""
    audio_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(audio_path):
        return f'/api/audio/{filename}'
    return None

def generate_insert_point_audio(quote_text, comment_text, insert_point_id, speed=5, person=3):
    """为单个 insert_point 生成两个音频：引用音频 + 评论音频"""
    token = get_access_token()
    if not token:
        return None

    result = {
        'quote_audio_path': None,
        'quote_audio_duration': 0,
        'comment_audio_path': None,
        'comment_audio_duration': 0
    }

    # 1. 生成引用音频
    if quote_text and len(quote_text.strip()) > 0:
        quote_result = call_baidu_tts(quote_text, token, speed=speed, person=person)
        if quote_result:
            quote_audio_path = os.path.join(AUDIO_DIR, f'insert_point_{insert_point_id}_quote.mp3')
            with open(quote_audio_path, 'wb') as f:
                f.write(quote_result)
            result['quote_audio_duration'], _ = get_audio_duration_and_timeline(quote_audio_path, quote_text)
            result['quote_audio_path'] = f'/api/audio/insert_point_{insert_point_id}_quote.mp3'
            print(f"[TTS] 点评 {insert_point_id} 引用音频完成: {result['quote_audio_duration']:.1f}s")

    # 2. 生成评论音频
    if comment_text and len(comment_text.strip()) > 0:
        comment_result = call_baidu_tts(comment_text, token, speed=speed, person=person)
        if comment_result:
            comment_audio_path = os.path.join(AUDIO_DIR, f'insert_point_{insert_point_id}_comment.mp3')
            with open(comment_audio_path, 'wb') as f:
                f.write(comment_result)
            result['comment_audio_duration'], _ = get_audio_duration_and_timeline(comment_audio_path, comment_text)
            result['comment_audio_path'] = f'/api/audio/insert_point_{insert_point_id}_comment.mp3'
            print(f"[TTS] 点评 {insert_point_id} 评论音频完成: {result['comment_audio_duration']:.1f}s")

    return result

def generate_section_audio_v2(section_id, speed=5, person=3):
    """新版整节音频生成：基于 text_segments 和 insert_points"""
    from database import (
        create_text_segments, create_insert_points,
        get_text_segments, get_insert_points_by_segment,
        update_text_segment_audio, update_insert_point_audio,
        update_insert_point_quote_audio
    )

    # 0. 生成固定音频文件
    generate_fixed_audio_files(speed, person)

    # 1. 创建 text_segments 和 insert_points
    create_text_segments(section_id)
    create_insert_points(section_id)

    # 2. 获取 text_segments
    segments = get_text_segments(section_id)
    if not segments:
        print(f"[TTS v2] 节 {section_id} 没有文本段")
        return False

    # 3. 逐个生成段音频
    for seg in segments:
        print(f"[TTS v2] 生成段 {seg['id']} 音频 ({seg['word_count']}字)")
        result = generate_text_segment_audio(seg['content'], seg['id'], speed, person)
        if result:
            update_text_segment_audio(
                seg['id'],
                result['audio_path'],
                result['audio_duration'],
                json.dumps(result['char_timeline']) if result.get('char_timeline') else None
            )
            print(f"[TTS v2] 段 {seg['id']} 完成: {result['audio_duration']:.1f}s")
        else:
            print(f"[TTS v2] 段 {seg['id']} 生成失败")

    # 4. 逐个生成插入点音频（引用音频 + 评论音频）
    for seg in segments:
        insert_points = get_insert_points_by_segment(seg['id'])
        
        for ip in insert_points:
            if ip['point_type'] == 'annotation':
                print(f"[TTS v2] 生成点评 {ip['id']} 音频")
                result = generate_insert_point_audio(ip['quote_text'], ip['comment'], ip['id'], speed, person)
                if result:
                    # 更新引用音频
                    if result['quote_audio_path']:
                        update_insert_point_quote_audio(ip['id'], result['quote_audio_path'], result['quote_audio_duration'])
                    # 更新评论音频
                    if result['comment_audio_path']:
                        update_insert_point_audio(ip['id'], result['comment_audio_path'], result['comment_audio_duration'])
                    print(f"[TTS v2] 点评 {ip['id']} 完成: 引用{result['quote_audio_duration']:.1f}s + 评论{result['comment_audio_duration']:.1f}s")
            elif ip['point_type'] == 'summary':
                print(f"[TTS v2] 生成小结 {ip['id']} 音频")
                # 小结只有评论音频
                result = generate_insert_point_audio(None, ip['comment'], ip['id'], speed, person)
                if result and result['comment_audio_path']:
                    update_insert_point_audio(ip['id'], result['comment_audio_path'], result['comment_audio_duration'])
                    print(f"[TTS v2] 小结 {ip['id']} 完成: {result['comment_audio_duration']:.1f}s")

    return True


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
