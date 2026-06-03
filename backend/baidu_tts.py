"""
悦读小将 - 百度 TTS 语音合成服务

统一文件命名规范（v10 重构）：
  原文段：segment_{book_id}_{section_id}_{seg_idx}.mp3
  点评内容：annotations_{book_id}_{section_id}_{idx}.mp3
  小结内容：summary_{book_id}_{section_id}.mp3
  固定音频：annotation_opening_male.mp3 等（不变）

音频生成流程（两阶段切割）：
  第1层：按点评边界（start_char/end_char）→ 将原文切成 N 段 text_segments
  第2层：若某段超过 TTS 字数限制(~500字符) → 再按句子分子块，分别调TTS后拼接

入口函数：generate_section_audio_v2(book_id, section_id)
"""

import os
import json
import time
import hashlib
import requests
import subprocess
from datetime import datetime

# 尝试从 .env 文件加载环境变量
def _load_env_file():
    """从 .env 文件加载环境变量"""
    env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
        '/opt/bandushutong/.env',
        '/opt/bandushutong/backend/.env',
        '/www/dk_project/wwwroot/lit.handy.xin/.env'
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


# ==================== 基础工具函数 ====================

def get_access_token():
    """获取百度 API access_token"""
    global _cached_token, _token_expire_time

    # 如果 token 还没过期，直接返回
    if _cached_token and time.time() < _token_expire_time:
        return _cached_token

    # 每次从环境变量读取最新值（解决模块加载顺序问题）
    app_id = os.environ.get('BAIDU_TTS_APP_ID', '')
    api_key = os.environ.get('BAIDU_TTS_API_KEY', '')
    secret_key = os.environ.get('BAIDU_TTS_SECRET_KEY', '')

    print(f"[TTS-DEBUG] 获取token - APP_ID: {app_id[:4]}***, API_KEY: {api_key[:4]}***, SECRET_KEY: {secret_key[:4]}***")

    if not app_id or not api_key or not secret_key:
        print("警告：未配置百度 TTS 密钥")
        return None

    try:
        params = {
            'grant_type': 'client_credentials',
            'client_id': api_key,
            'client_secret': secret_key
        }
        print(f"[TTS-DEBUG] 请求URL: {BAIDU_TOKEN_URL}")
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


def call_baidu_tts(text, token, speed=5, person=4001):
    """调用单次百度 TTS API，返回音频字节数据或 None"""
    params = {
        'tok': token,
        'tex': text,
        'per': person,
        'spd': speed,
        'pit': 5,
        'vol': 5,
        'aue': 3,  # MP3 格式
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


def _split_text_for_tts(text):
    """
    将长文本按 TTS 字符限制分段。
    按 UTF-8 字节数 (~900 bytes) 或句号分割。
    返回: [segment_text, ...]
    """
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
    return segments


def _merge_mp3_files(mp3_file_list, output_path):
    """
    用 ffmpeg concat demuxer 合并多个 MP3 文件。
    单个文件时直接重命名。
    返回: 成功 bool
    """
    if not mp3_file_list:
        return False

    if len(mp3_file_list) == 1:
        try:
            os.rename(mp3_file_list[0], output_path)
            return True
        except Exception as e:
            print(f"[TTS] 重命名失败: {e}")
            return False

    # 多文件用 ffmpeg concat
    try:
        list_file = output_path + '_list.txt'
        with open(list_file, 'w', encoding='utf-8') as f:
            for fp in mp3_file_list:
                f.write(f"file '{fp}'\n")
        subprocess.run(
            ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
             '-i', list_file, '-c', 'copy', output_path],
            capture_output=True, timeout=60
        )
        # 清理临时文件
        for fp in mp3_file_list:
            if os.path.exists(fp) and fp != output_path:
                os.remove(fp)
        if os.path.exists(list_file):
            os.remove(list_file)
        return True
    except Exception as e:
        print(f"[TTS] ffmpeg 合并失败: {e}")
        return False


def _measure_duration(filepath):
    """用 ffprobe 获取音频时长（秒），失败则返回 0"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet',
             '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1',
             filepath],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            return round(float(result.stdout.strip()), 3)
    except Exception as e:
        print(f"[TTS] 测量时长失败 {os.path.basename(filepath)}: {e}")
    return 0


def build_char_timeline(text, duration):
    """
    构建字符时间轴（考虑标点符号停顿权重）。
    返回: [t0, t1, t2, ..., tN]，每个元素是该字符的时间点（秒）
    """
    if not text or duration <= 0:
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
    if total_weight <= 0:
        return []

    accumulated_weight = 0
    timeline = []
    for w in char_weights:
        t = (accumulated_weight / total_weight) * duration
        timeline.append(round(t, 3))
        accumulated_weight += w
    return timeline


def get_audio_duration_and_timeline(audio_path, text):
    """获取音频时长和构建字符时间轴（组合操作）"""
    dur = _measure_duration(audio_path)
    if dur <= 0:
        dur = len(text) / 200 * 60  # 估算 fallback
    tl = build_char_timeline(text, dur)
    return dur, tl


def is_configured():
    """检查百度 TTS 是否已配置"""
    return bool(BAIDU_TTS_APP_ID and BAIDU_TTS_API_KEY and BAIDU_TTS_SECRET_KEY)


# ==================== 内部核心：长文本 TTS 合成 ====================

def _synthesize_long_text(output_filename, text, token, speed=5, person=4001):
    """
    内部通用函数：长文本 → 自动分段调TTS → 合并为一个 MP3 文件。

    参数:
        output_filename: 最终输出的文件名（不含路径），如 'segment_4_662_0.mp3'
        text: 要合成的完整文本（可能很长）
        token: 已有的 access_token
        speed, person: TTS 参数

    返回:
        {'audio_path': '/api/audio/{output_filename}', 'audio_duration': 秒}
        或 None（失败）
    """
    if not text or len(text.strip()) == 0:
        return None

    # 分段
    parts = _split_text_for_tts(text)
    if not parts:
        return None

    output_path = os.path.join(AUDIO_DIR, output_filename)

    # 单段不需要合并
    if len(parts) == 1:
        audio_data = call_baidu_tts(parts[0], token, speed=speed, person=person)
        if not audio_data:
            print(f"[TTS] 单段 TTS 合成失败: {output_filename}")
            return None
        with open(output_path, 'wb') as f:
            f.write(audio_data)
        dur = _measure_duration(output_path)
        return {
            'audio_path': f'/api/audio/{output_filename}',
            'audio_duration': dur
        }

    # 多段：逐个合成再合并
    temp_files = []
    for i, part in enumerate(parts):
        audio_data = call_baidu_tts(part, token, speed=speed, person=person)
        if not audio_data:
            print(f"[TTS] 子段 {i}/{len(parts)} TTS 合成失败")
            return None
        temp_path = os.path.join(AUDIO_DIR, f'_tmp_{output_filename}_{i}.mp3')
        with open(temp_path, 'wb') as f:
            f.write(audio_data)
        temp_files.append(temp_path)

    success = _merge_mp3_files(temp_files, output_path)
    if not success:
        print(f"[TTS] 合并失败: {output_filename}")
        return None

    dur = _measure_duration(output_path)
    return {
        'audio_path': f'/api/audio/{output_filename}',
        'audio_duration': dur
    }


# ==================== 固定音频（开场白/结束语）====================

def text_to_speech_long(text, section_id=None, speed=5, person=4001):
    """
    轻量级长文本合成（用于 TTS 预览/修复端点，不参与主流程）。
    按 TTS 字符限制分段，逐段调 API，返回文件路径列表。

    注意：此函数保留是为了兼容 api.py 中的预览/修复端点。
    主音频生成请使用 generate_section_audio_v2()。
    """
    token = get_access_token()
    if not token:
        return []

    parts = _split_text_for_tts(text)
    if not parts:
        return []

    audio_paths = []
    for i, part in enumerate(parts):
        audio_data = call_baidu_tts(part, token, speed=speed, person=person)
        if not audio_data:
            continue
        filename = f'section_{section_id}_{i}.mp3' if section_id else f'preview_{int(time.time())}_{i}.mp3'
        filepath = os.path.join(AUDIO_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        audio_paths.append(f'audio_files/{filename}')

    return audio_paths


def ensure_fixed_audio_files(speed=5):
    """系统启动时检查固定音频文件是否完整，缺失则自动补齐

    固定音频共 8 个文件（男声4个 + 女声4个），供阅读页播放点评/小结时使用。
    此函数幂等：已存在的文件不会重新生成。

    返回: True（完整或补齐成功） / False（TTS未配置或生成失败）
    """
    if not is_configured():
        print("[TTS] 固定音频跳过: TTS 未配置")
        return False

    # 两套各4个文件
    required_files = []
    for voice in ['male', 'female']:
        for name in ['annotation_opening', 'annotation_closing', 'summary_opening', 'summary_closing']:
            required_files.append(f'{name}_{voice}.mp3')

    # 检查哪些缺失
    missing = [f for f in required_files if not os.path.exists(os.path.join(AUDIO_DIR, f))]

    if not missing:
        print(f"[TTS] 固定音频已完整 ({len(required_files)} 个文件)")
        return True

    print(f"[TTS] 固定音频缺失 {len(missing)}/{len(required_files)} 个，开始补齐...")

    # 按音色分组生成（只生成缺失的）
    for voice in ['male', 'female']:
        voice_missing = [f for f in missing if f.endswith(f'_{voice}.mp3')]
        if voice_missing:
            generate_fixed_audio_files_by_voice(voice, speed)

    # 验证是否全部就位
    still_missing = [f for f in required_files if not os.path.exists(os.path.join(AUDIO_DIR, f))]
    if still_missing:
        print(f"[TTS] 固定音频仍有 {len(still_missing)} 个缺失: {still_missing}")
        return False

    print(f"[TTS] 固定音频补齐完成 ({len(required_files)} 个文件)")
    return True


def generate_fixed_audio_files(speed=5, person=4001):
    """生成系统固定音频文件（男声女声各一套）

    已废弃：启动时请使用 ensure_fixed_audio_files()（带存在检查，不重复生成）。
    此函数保留仅供向后兼容。
    """
    ensure_fixed_audio_files(speed)


def generate_fixed_audio_files_by_voice(voice_type='male', speed=5):
    """生成系统固定音频文件

    voice_type 实际指「点评/固定语使用的音色」（与原文互补）：
        'male':   person=4001(度逍遥男声-精品), 后缀 '_male'
        'female': person=5001(度小娇女声-精品), 后缀 '_female'

    前端选择逻辑：
        原文 voice_type='male'   → 点评用女声 → 找 *_female.mp3
        原文 voice_type='female' → 点评用男声 → 找 *_male.mp3
    """
    token = get_access_token()
    if not token:
        return False

    person = 4001 if voice_type == 'male' else 5001
    suffix = f'_{voice_type}'

    files = {
        f'annotation_opening{suffix}.mp3': '我们来看下这里：',
        f'annotation_closing{suffix}.mp3': '回到原文',
        f'summary_opening{suffix}.mp3': '这篇内容已读完，我们回顾一下：',
        f'summary_closing{suffix}.mp3': '小结之外有其他思考，请添加到右上角。'
    }

    for filename, text in files.items():
        audio_path = os.path.join(AUDIO_DIR, filename)
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


def get_fixed_audio_path(filename, voice_type='male'):
    """获取固定音频文件的 URL 路径"""
    suffix = '_female' if voice_type == 'female' else '_male'

    # 先尝试带后缀的文件
    audio_path = os.path.join(AUDIO_DIR, filename.replace('.mp3', f'{suffix}.mp3'))
    if os.path.exists(audio_path):
        return f'/api/audio/{filename.replace(".mp3", f"{suffix}.mp3")}'

    # 回退到旧版文件名（兼容旧数据）
    audio_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(audio_path):
        return f'/api/audio/{filename}'
    return None


# ==================== 业务音频生成函数 ====================

def generate_text_segment_audio(book_id, section_id, seg_idx, text, speed=5, person=4001):
    """
    为单个原文段（text_segment）生成音频。

    文件命名：segment_{book_id}_{section_id}_{seg_idx}.mp3
    例：book=4, section=662, idx=0 → segment_4_662_0.mp3

    返回:
        {'audio_path': str, 'audio_duration': float, 'char_timeline': [float]}
        或 None
    """
    token = get_access_token()
    if not token:
        return None

    output_filename = f'segment_{book_id}_{section_id}_{seg_idx}.mp3'
    result = _synthesize_long_text(output_filename, text, token, speed, person)
    if not result:
        return None

    # 构建字符时间轴
    audio_path = os.path.join(AUDIO_DIR, output_filename)
    _, char_timeline = get_audio_duration_and_timeline(audio_path, text)

    result['char_timeline'] = char_timeline
    print(f"[TTS] 原文段音频完成: {output_filename}, {result['audio_duration']:.1f}s, {len(char_timeline)}个时间点")
    return result


def generate_annotations_audio(book_id, section_id, ann_idx, comment_text, speed=5, person=4001):
    """
    为单条点评的评论内容生成音频。

    文件命名：annotations_{book_id}_{section_id}_{ann_idx}.mp3
    例：book=4, section=662, idx=0 → annotations_4_662_0.mp3

    返回:
        {'audio_path': str, 'audio_duration': float}
        或 None
    """
    token = get_access_token()
    if not token:
        return None

    output_filename = f'annotations_{book_id}_{section_id}_{ann_idx}.mp3'
    result = _synthesize_long_text(output_filename, comment_text, token, speed, person)
    if result:
        print(f"[TTS] 点评音频完成: {output_filename}, {result['audio_duration']:.1f}s")
    return result


def generate_summary_audio(book_id, section_id, summary_text, speed=5, person=4001):
    """
    为小结生成音频。

    文件命名：summary_{book_id}_{section_id}.mp3
    例：book=4, section=662 → summary_4_662.mp3

    返回:
        {'audio_path': str, 'audio_duration': float}
        或 None
    """
    token = get_access_token()
    if not token:
        return None

    output_filename = f'summary_{book_id}_{section_id}.mp3'
    result = _synthesize_long_text(output_filename, summary_text, token, speed, person)
    if result:
        print(f"[TTS] 小结音频完成: {output_filename}, {result['audio_duration']:.1f}s")
    return result


# ==================== 主入口：整节音频生成 ====================

def generate_section_audio_v2(book_id, section_id, speed=5, person=4001):
    """
    新版整节音频生成（唯一入口）。

    完整流程：
    1. 创建 text_segments（按点评边界切分原文为 N 段）
    2. 创建 insert_points（将点评/小结绑定到对应段后面）
    3. 对每个 text_segment 调用 TTS → segment_{book_id}_{section_id}_{seg_idx}.mp3
    4. 对每条点评评论调 TTS → annotations_{book_id}_{section_id}_{idx}.mp3
    5. 对小结调 TTS → summary_{book_id}_{section_id}.mp3
    6. 写回数据库（text_segments.audio_path/char_timeline + insert_points.audio_path）

    参数:
        book_id: 书籍 ID（用于文件命名）
        section_id: 节 ID
        speed: 语速 0-15
        person: 发音人（原文使用）

    返回: True（成功）或 False（失败）
    """
    from backend.database import (
        create_text_segments, create_insert_points,
        get_text_segments, get_insert_points_by_segment,
        update_text_segment_audio, update_insert_point_audio,
        update_insert_point_quote_audio
    )

    # 1. 创建/刷新 text_segments 和 insert_points
    create_text_segments(section_id)
    create_insert_points(section_id)

    # 2. 获取该节所有 text_segments
    segments = get_text_segments(section_id)
    if not segments:
        print(f"[TTS v2] 节 {section_id} 没有文本段")
        return False

    # 确定声音配置
    # 原文用 person（传入值），点评用互补音色
    comment_person = 5001 if person == 4001 else 4001

    # 3. 为每个原文段生成音频，并记录 segment_id → 音频信息 映射
    print(f"[TTS v2] 节 {section_id}: 开始生成 {len(segments)} 个原文段音频...")
    seg_audio_map = {}  # segment_id → {'audio_path', 'audio_duration'}
    for seg in segments:
        seg_idx = seg.get('segment_number', 0)
        print(f"[TTS v2]   生成原文段 #{seg_idx} (id={seg['id']}, {seg.get('word_count', '?')}字)")
        result = generate_text_segment_audio(
            book_id, section_id, seg_idx, seg['content'], speed, person
        )
        if result:
            update_text_segment_audio(
                seg['id'],
                result['audio_path'],
                result['audio_duration'],
                json.dumps(result['char_timeline']) if result.get('char_timeline') else None
            )
            seg_audio_map[seg['id']] = {
                'audio_path': result['audio_path'],
                'audio_duration': result['audio_duration']
            }
            print(f"[TTS v2]   原文段 #{seg_idx} 完成: {result['audio_duration']:.1f}s")
        else:
            print(f"[TTS v2]   原文段 #{seg_idx} 生成失败!")

    # 4. 为每个插入点生成音频（点评 + 小结）
    ann_idx = 0  # 点评序号，用于文件命名
    for seg in segments:
        insert_points = get_insert_points_by_segment(seg['id'])
        for ip in insert_points:
            if ip['point_type'] == 'annotation':
                print(f"[TTS v2]   生成点评 #{ann_idx} (id={ip['id']}) 音频")
                # 点评的 comment 是评论内容
                comment_text = ip.get('comment', '') or ''
                result = generate_annotations_audio(
                    book_id, section_id, ann_idx, comment_text, speed, comment_person
                )
                if result and result.get('audio_path'):
                    update_insert_point_audio(ip['id'], result['audio_path'], result['audio_duration'])
                    print(f"[TTS v2]   点评 #{ann_idx} 评论音频完成: {result['audio_duration']:.1f}s")

                # quote_audio_path 直接指向对应的 segment 音频（引用原文就是该段原文）
                seg_audio_info = seg_audio_map.get(seg['id'])
                if seg_audio_info:
                    update_insert_point_quote_audio(
                        ip['id'],
                        seg_audio_info['audio_path'],
                        seg_audio_info['audio_duration']
                    )
                    print(f"[TTS v2]   点评 #{ann_idx} quote_audio → {seg_audio_info['audio_path']}")

                ann_idx += 1

            elif ip['point_type'] == 'summary':
                print(f"[TTS v2]   生成小结 (id={ip['id']}) 音频")
                comment_text = ip.get('comment', '') or ''
                result = generate_summary_audio(book_id, section_id, comment_text, speed, comment_person)
                if result and result.get('audio_path'):
                    update_insert_point_audio(ip['id'], result['audio_path'], result['audio_duration'])
                    print(f"[TTS v2]   小结完成: {result['audio_duration']:.1f}s")

    print(f"[TTS v2] 节 {section_id} 全部完成 (book={book_id})")
    return True


def generate_book_audio(book_id, person=4001, speed=5):
    """
    为书籍的所有节预生成音频（后台线程调用）。
    遍历每节，调用 generate_section_audio_v2()。
    """
    import sys
    import threading
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.database import (
        get_sections_by_book, update_book_tts_status, check_section_audio_complete
    )

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
                result = generate_section_audio_v2(book_id, section_id, speed=speed, person=person)
                done_count += 1
                update_book_tts_status(book_id, 'generating', f'{done_count}/{total}')
                status_msg = '成功' if result else '失败'
                print(f"[TTS] 节 {section_id} {status_msg} ({done_count}/{total})")
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


if __name__ == '__main__':
    if is_configured():
        print("百度 TTS 已配置")
        token = get_access_token()
        if token:
            result = _synthesize_long_text('test_tts.mp3', "你好，这是一个测试。", token)
            print(f"测试结果: {result}")
    else:
        print("百度 TTS 未配置，请设置环境变量:")
        print("  BAIDU_TTS_APP_ID")
        print("  BAIDU_TTS_API_KEY")
        print("  BAIDU_TTS_SECRET_KEY")
