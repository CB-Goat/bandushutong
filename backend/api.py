# -*- coding: utf-8 -*-
"""
悦读小将 - API 路由
"""

from flask import Blueprint, request, jsonify, send_file
import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import (
    init_db, add_book, get_book, get_all_books,
    add_section, get_sections_by_book, get_section, update_section_audio,
    update_progress, get_progress,
    add_annotation, get_annotations_by_section, delete_annotation,
    update_book_sections_count,
    update_book, delete_book, update_book_chapters_count,
    add_chapter, get_chapters_by_book, get_chapter, update_chapter, delete_chapter, update_chapter_info,
    get_sections_by_chapter, update_section, delete_section, update_section_word_count,
    set_section_status, get_section_status, get_all_section_status, get_book_reading_stats,
    # 用户系统
    create_user, get_user, get_user_by_phone, get_user_by_wechat_openid, get_all_users, update_user_role, delete_user,
    update_user_profile, update_user_phone, update_user_password, update_user_wechat, verify_user_phone_password,
    add_message, get_messages_by_user, get_all_messages, reply_message,
    # 设备管理
    update_user_device, create_transfer_code, verify_transfer_code,
    # 订阅系统
    subscribe_book, get_user_subscriptions, check_book_access, get_subscription_requests, add_subscription_request, approve_subscription_request, reject_subscription_request,
    # 思考系统
    add_thought, get_thoughts_by_section, get_all_thoughts_by_section, delete_thought, update_thought,
    # 书籍查找
    get_book_by_title_author_version,
    # 管理员统计
    get_users_with_stats, get_books_with_stats, update_book_price, get_book_catalog_stats,
    get_user_subscription_stats, admin_add_subscription, admin_remove_subscription,
    get_user_by_phone as _get_user_by_phone,
    # 军衔等级系统
    get_user_military_rank,
    get_db,
)
from backend.text_parser import parse_file, get_book_title
from backend.tts_service import generate_audio
from backend.ai_score import rate_thought
import hashlib
import xml.etree.ElementTree as ET

api_bp = Blueprint('api', __name__)

# 微信公众号配置（需要在环境变量中设置）
WECHAT_TOKEN = os.environ.get('WECHAT_TOKEN', 'bandushutong2024')  # 公众号Token

# 文件上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'books')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ===== 微信公众号 API =====

@api_bp.route('/wechat', methods=['GET', 'POST'])
def wechat_handler():
    """微信公众号消息处理入口"""
    if request.method == 'GET':
        # 验证服务器地址有效性
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        
        # 验证签名
        tmp_list = [WECHAT_TOKEN, timestamp, nonce]
        tmp_list.sort()
        tmp_str = ''.join(tmp_list)
        tmp_hash = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        
        if tmp_hash == signature:
            return echostr
        else:
            return 'invalid', 403
    
    else:
        # 处理微信消息
        try:
            xml_data = request.data.decode('utf-8')
            root = ET.fromstring(xml_data)
            
            msg_type = root.find('MsgType').text
            from_user = root.find('FromUserName').text
            to_user = root.find('ToUserName').text
            
            if msg_type == 'event':
                event = root.find('Event').text
                if event == 'subscribe':
                    # 用户关注公众号
                    return _make_text_reply(to_user, from_user, 
                        '欢迎关注悦读小将！\n\n点击下方菜单"开始阅读"即可进入系统。')
                elif event == 'CLICK':
                    # 菜单点击事件
                    event_key = root.find('EventKey').text
                    if event_key == 'start_reading':
                        # 返回带用户openid的链接
                        url = f"{request.host_url}?wechat_openid={from_user}"
                        return _make_text_reply(to_user, from_user, 
                            f'点击链接进入悦读小将：\n{url}')
            
            # 默认回复
            return _make_text_reply(to_user, from_user, '收到消息，请使用菜单功能。')
            
        except Exception as e:
            print(f"[WeChat] Error: {e}")
            return 'success'

def _make_text_reply(to_user, from_user, content):
    """生成文本回复XML"""
    import time
    return f'''<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>'''

@api_bp.route('/init', methods=['POST'])
def init_database():
    """初始化数据库"""
    init_db()
    return jsonify({'message': '数据库初始化成功'})

@api_bp.route('/public/books', methods=['GET'])
def list_public_books():
    """获取公版书籍列表（无需登录）"""
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, title, author, author_nationality, version, total_sections, total_chapters, is_public
                      FROM books WHERE is_public=1 ORDER BY id DESC''')
    books = [dict(row) for row in cursor.fetchall()]
    # 附加总字数和点评总数
    for book in books:
        bid = book['id']
        cursor.execute('SELECT COALESCE(SUM(word_count),0) as total_words FROM sections WHERE book_id=?', (bid,))
        book['total_words'] = cursor.fetchone()['total_words']
        cursor.execute('''SELECT COUNT(*) as cnt FROM annotations a 
                          JOIN sections s ON a.section_id = s.id WHERE s.book_id=?''', (bid,))
        book['total_annotations'] = cursor.fetchone()['cnt']
    conn.close()
    return jsonify({'books': books})

@api_bp.route('/books', methods=['GET'])
def list_books():
    """获取书籍列表（含统计信息）"""
    from backend.database import get_db
    user_id = request.args.get('user_id', type=int)
    books = get_all_books()
    # 为每本书附加统计信息
    for book in books:
        bid = book['id']
        stats = get_book_reading_stats(user_id, bid)
        book['reading_stats'] = stats
        # 获取总字数和点评总数
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COALESCE(SUM(word_count),0) as total_words FROM sections WHERE book_id=?', (bid,))
        book['total_words'] = cursor.fetchone()['total_words']
        cursor.execute('''SELECT COUNT(*) as cnt FROM annotations a 
                          JOIN sections s ON a.section_id = s.id WHERE s.book_id=?''', (bid,))
        book['total_annotations'] = cursor.fetchone()['cnt']
        conn.close()
    return jsonify({'books': books})

@api_bp.route('/books/<int:book_id>', methods=['GET'])
def book_detail(book_id):
    """获取书籍详情"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    
    sections = get_sections_by_book(book_id)
    user_id = request.args.get('user_id', type=int)
    progress = get_progress(user_id, book_id)
    from database import get_progress_v2 as _get_progress_v2
    progress_v2 = _get_progress_v2(user_id, book_id)

    # 获取每个小节的点评点
    for sec in sections:
        sec['annotations'] = get_annotations_by_section(sec['id'])
    
    # Debug: log annotations count
    for sec in sections[:2]:
        print(f"[API] Section {sec['id']}: {len(sec.get('annotations', []))} annotations")
    
    return jsonify({
        'book': book,
        'sections': sections,
        'progress': progress,
        'progress_v2': progress_v2
    })

@api_bp.route('/upload', methods=['POST'])
def upload_book():
    """上传书籍文件（支持 TXT / DOCX）"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名不能为空'}), 400
    
    # 保存文件
    filename = file.filename
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)
    
    # 解析文件（提取元信息 + 章节 + 节）
    try:
        # 优先使用 Word 结构解析器
        if filepath.endswith('.docx'):
            from backend.word_parser import parse_file as parse_word
            result = parse_word(filepath)
        else:
            result = parse_file(filepath)
        
        title = result.get('title', get_book_title(filepath))
        author = result.get('author', '')
        author_nationality = result.get('author_nationality', '')
        version = result.get('version', '')
        chapters = result.get('chapters', [])
        sections = result.get('sections', [])
        
        print(f"[UPLOAD] 解析结果: 标题={title}, 作者={author}, 国籍={author_nationality}, 版本={version}")
        
        # 检查是否已存在相同书名+作者+版本的书籍
        existing_book = get_book_by_title_author_version(title, author, version)
        is_update = False
        
        if existing_book:
            # 更新现有书籍
            book_id = existing_book['id']
            is_update = True
            # 更新文件路径
            from backend.database import get_db
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE books SET file_path = ? WHERE id = ?', (filepath, book_id))
            conn.commit()
            conn.close()
            # 删除旧的章节、节、点评，重新导入
            old_chapters = get_chapters_by_book(book_id)
            for ch in old_chapters:
                delete_chapter(ch['id'])
            # 直接删除所有旧的节（防止无章节时残留）
            from backend.database import get_db as _get_db
            _conn = _get_db()
            _c = _conn.cursor()
            _c.execute('DELETE FROM annotations WHERE section_id IN (SELECT id FROM sections WHERE book_id=?)', (book_id,))
            _c.execute('DELETE FROM sections WHERE book_id=?', (book_id,))
            _c.execute('DELETE FROM chapters WHERE book_id=?', (book_id,))
            _conn.commit()
            _conn.close()
        else:
            # 添加新书籍到数据库
            book_id = add_book(title=title, author=author, file_path=filepath)
        
        # 更新书籍元信息
        if author_nationality or version:
            update_book(book_id, title=title, author=author,
                       author_nationality=author_nationality, version=version)
        
        # 保存章节到数据库
        chapter_id_map = {}  # chapter_number -> chapter_id
        for ch in chapters:
            ch_id = add_chapter(
                book_id=book_id,
                chapter_number=ch['chapter_number'],
                title=ch.get('title', '')
            )
            chapter_id_map[ch['chapter_number']] = ch_id
        
        # 保存小节到数据库
        for sec in sections:
            ch_num = sec.get('chapter_number')
            ch_id = chapter_id_map.get(ch_num) if ch_num else None
            
            word_count = len(sec.get('content', ''))
            sec_id = add_section(
                book_id=book_id,
                chapter_id=ch_id,
                section_number=sec['section_number'],
                content=sec.get('content', ''),
                title=sec.get('title', '')
            )

            # 保存小结（从批注解析）
            if sec.get('summary'):
                from backend.database import get_db
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('UPDATE sections SET summary = ? WHERE id = ?', (sec['summary'], sec_id))
                conn.commit()
                conn.close()

            # 保存点评（从批注解析）
            annotations = sec.get('annotations', [])
            for idx, anno in enumerate(annotations):
                add_annotation(
                    section_id=sec_id,
                    annotation_index=idx + 1,
                    start_char=anno.get('start_char', 0),
                    end_char=anno.get('end_char', 0),
                    original_text=anno.get('original_text', ''),
                    comment=anno.get('comment', '')
                )
            
            # 创建 text_segments 和 insert_points
            from backend.database import create_text_segments, create_insert_points
            create_text_segments(sec_id)
            create_insert_points(sec_id)
        
        # 更新书籍统计
        update_book_sections_count(book_id, len(sections))
        update_book_chapters_count(book_id, len(chapters))
        
        # 更新章节统计信息
        for ch_num, ch_id in chapter_id_map.items():
            ch_sections = [s for s in sections if s.get('chapter_number') == ch_num]
            ch_total_words = sum(len(s.get('content', '')) for s in ch_sections)
            update_chapter_info(ch_id, len(ch_sections), ch_total_words)

        # 预生成所有节的音频（异步，不阻塞返回）
        try:
            from backend.baidu_tts import generate_book_audio
            generate_book_audio(book_id)
            print(f"[TTS] 已开始为书籍 {book_id} 预生成音频")
        except Exception as e:
            print(f"[TTS] 预生成音频失败: {e}")

        return jsonify({
            'message': '更新成功' if is_update else '上传成功',
            'book_id': book_id,
            'title': title,
            'author': author,
            'chapters_count': len(chapters),
            'sections_count': len(sections),
            'is_update': is_update
        })
    
    except Exception as e:
        return jsonify({'error': f'解析失败: {str(e)}'}), 500

@api_bp.route('/sections/<int:section_id>/audio', methods=['POST'])
def generate_section_audio(section_id):
    """生成小节的语音"""
    section = get_section(section_id)
    if not section:
        return jsonify({'error': '小节不存在'}), 404
    
    # 生成音频
    audio_path = generate_audio(section['content'], section_id)
    
    if audio_path:
        # 更新数据库
        update_section_audio(section_id, audio_path)
        return jsonify({
            'message': '音频生成成功',
            'audio_path': audio_path
        })
    else:
        return jsonify({'error': '音频生成失败'}), 500

@api_bp.route('/tts/synthesize', methods=['POST'])
def tts_synthesize():
    """百度 TTS 合成接口（供前端降级使用）"""
    data = request.get_json()
    text = data.get('text', '')
    section_id = data.get('section_id')
    
    if not text:
        return jsonify({'error': '文本不能为空'}), 400
    
    # 尝试百度 TTS
    from backend.baidu_tts import text_to_speech_long, is_configured
    
    if not is_configured():
        return jsonify({'error': 'TTS 服务未配置'}), 503
    
    audio_paths = text_to_speech_long(text, section_id=section_id)
    
    if audio_paths:
        return jsonify({
            'success': True,
            'audio_urls': ['/api/audio/' + os.path.basename(p) for p in audio_paths]
        })
    else:
        return jsonify({'error': '语音合成失败'}), 500

@api_bp.route('/tts/status', methods=['GET'])
def tts_status():
    """检查 TTS 服务状态"""
    from backend.baidu_tts import is_configured
    return jsonify({
        'browser_tts': True,  # 前端会自己检测
        'server_tts': is_configured()
    })

@api_bp.route('/sections/<int:section_id>/audio-timeline', methods=['GET'])
def get_section_audio_timeline_api(section_id):
    """获取节的音频时间轴信息（包含分段信息）"""
    from backend.database import get_section_audio_timeline, get_section_audio_segments
    timeline = get_section_audio_timeline(section_id)
    if timeline:
        # 尝试获取分段信息
        segments = get_section_audio_segments(section_id)
        if segments:
            timeline['audio_segments'] = segments
        return jsonify(timeline)
    else:
        return jsonify({'error': '音频时间轴不存在'}), 404

@api_bp.route('/sections/<int:section_id>/generate-audio', methods=['POST'])
def generate_section_audio_api(section_id):
    """为节生成音频和时间轴"""
    from backend.database import get_section, update_section_audio_timeline
    from backend.baidu_tts import generate_section_audio_with_timeline
    
    section = get_section(section_id)
    if not section:
        return jsonify({'error': '节不存在'}), 404
    
    result = generate_section_audio_with_timeline(
        section['content'], 
        section_id,
        speed=5,
        person=0  # 普通女声
    )
    
    if result:
        update_section_audio_timeline(
            section_id,
            result['audio_duration'],
            result['char_timeline'],
            result['audio_path']
        )
        return jsonify({
            'success': True,
            'audio_path': result['audio_path'],
            'audio_duration': result['audio_duration']
        })
    else:
        return jsonify({'error': '音频生成失败'}), 500

@api_bp.route('/sections/<int:section_id>/generate-segmented-audio', methods=['POST'])
def generate_segmented_audio_api(section_id):
    """为节生成分段音频（按点评边界分割）"""
    try:
        from backend.database import get_section, update_section_audio_timeline, update_section_audio_segments, get_annotations_by_section
        from backend.baidu_tts import generate_segmented_audio
        
        section = get_section(section_id)
        if not section:
            return jsonify({'error': '节不存在'}), 404
        
        # 获取该节的所有点评
        annotations = get_annotations_by_section(section_id)
        # 按 end_char 排序
        annotations = sorted(annotations, key=lambda a: a.get('end_char', 0))
        
        print(f"[TTS] 开始为节 {section_id} 生成分段音频，共 {len(annotations)} 个点评")
        
        result = generate_segmented_audio(
            section['content'], 
            section_id,
            annotations=annotations,
            speed=5,
            person=0
        )
        
        if result:
            update_section_audio_timeline(
                section_id,
                result['audio_duration'],
                result['char_timeline'],
                result['audio_path']
            )
            # 保存分段信息
            if result.get('audio_segments'):
                update_section_audio_segments(section_id, result['audio_segments'])
            
            return jsonify({
                'success': True,
                'audio_path': result['audio_path'],
                'audio_duration': result['audio_duration'],
                'segment_count': len(result.get('audio_segments', []))
            })
        else:
            return jsonify({'error': '分段音频生成失败'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/books/<int:book_id>/tts-status', methods=['GET'])
def get_book_tts_status(book_id):
    """获取书籍的TTS生成状态"""
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT tts_status, tts_progress, total_sections FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({
            'tts_status': row['tts_status'] or 'none',
            'tts_progress': row['tts_progress'] or '',
            'total_sections': row['total_sections'] or 0
        })
    return jsonify({'error': '书籍不存在'}), 404

@api_bp.route('/audio/<path:filename>', methods=['GET'])
def serve_audio(filename):
    """提供音频文件"""
    audio_dir = os.path.join(os.path.dirname(__file__), '..', 'audio_files')
    filepath = os.path.join(audio_dir, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='audio/mpeg')
    else:
        return jsonify({'error': '音频文件不存在'}), 404

@api_bp.route('/progress', methods=['POST'])
def save_progress():
    """保存阅读进度"""
    data = request.json
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    section_id = data.get('section_id')
    position = data.get('position', 0)
    audio_position = data.get('audio_position', 0)
    
    if not book_id or not section_id:
        return jsonify({'error': '缺少必要参数'}), 400
    
    update_progress(user_id, book_id, section_id, position, audio_position)
    return jsonify({'message': '进度保存成功'})

@api_bp.route('/progress/<int:book_id>', methods=['GET'])
def get_book_progress(book_id):
    """获取阅读进度"""
    user_id = request.args.get('user_id', type=int)
    progress = get_progress(user_id, book_id)
    if progress:
        return jsonify(progress)
    else:
        return jsonify({'message': '暂无阅读进度'})

@api_bp.route('/sections/<int:section_id>/playback-plan', methods=['GET'])
def get_section_playback_plan(section_id):
    """获取一节的完整播放计划"""
    from database import get_section_playback_plan
    plan = get_section_playback_plan(section_id)
    if not plan or not plan.get('playlist'):
        return jsonify({'error': '播放计划不存在'}), 404
    return jsonify(plan)

@api_bp.route('/sections/<int:section_id>/build-segments', methods=['POST'])
def build_segments(section_id):
    """手动触发段的切割和插入点创建"""
    from database import create_text_segments, create_insert_points
    seg_count = create_text_segments(section_id)
    create_insert_points(section_id)
    return jsonify({'message': f'已创建 {seg_count} 个文本段', 'segment_count': seg_count})

@api_bp.route('/progress/v2', methods=['POST'])
def save_progress_v2():
    """新版断点保存"""
    from database import update_progress_v2
    data = request.json
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    section_id = data.get('section_id')
    segment_id = data.get('segment_id')
    text_position = data.get('text_position', 0)
    audio_position = data.get('audio_position', 0)

    if not book_id or not section_id:
        return jsonify({'error': '缺少必要参数'}), 400

    update_progress_v2(user_id, book_id, section_id, segment_id, text_position, audio_position)
    return jsonify({'message': '进度保存成功'})

@api_bp.route('/progress/v2/<int:book_id>', methods=['GET'])
def get_progress_v2(book_id):
    """新版断点读取"""
    from database import get_progress_v2
    user_id = request.args.get('user_id', type=int)
    progress = get_progress_v2(user_id, book_id)
    if progress:
        return jsonify(progress)
    else:
        return jsonify({'message': '暂无阅读进度'})

# ===== 点评点 API =====

@api_bp.route('/sections/<int:section_id>/annotations', methods=['GET'])
def list_annotations(section_id):
    """获取小节的所有点评点"""
    annotations = get_annotations_by_section(section_id)
    return jsonify({'annotations': annotations})

@api_bp.route('/sections/<int:section_id>/annotations', methods=['POST'])
def create_annotation(section_id):
    """创建点评点"""
    data = request.json
    section = get_section(section_id)
    if not section:
        return jsonify({'error': '小节不存在'}), 404
    
    # 获取当前已有的点评数量，用于计算序号
    existing = get_annotations_by_section(section_id)
    annotation_index = len(existing) + 1
    
    annotation_id = add_annotation(
        section_id=section_id,
        annotation_index=annotation_index,
        start_char=data.get('start_char', 0),
        end_char=data.get('end_char', 0),
        original_text=data.get('original_text', ''),
        comment=data.get('comment', '')
    )
    
    return jsonify({
        'message': '点评点添加成功',
        'annotation_id': annotation_id,
        'annotation_index': annotation_index
    })

@api_bp.route('/annotations/<int:annotation_id>', methods=['DELETE'])
def remove_annotation(annotation_id):
    """删除点评点"""
    delete_annotation(annotation_id)
    return jsonify({'message': '点评点已删除'})

# ===== 管理员 API =====

@api_bp.route('/admin/books/<int:book_id>', methods=['PUT'])
def admin_update_book(book_id):
    """更新书籍信息"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    data = request.json
    update_book(book_id,
        title=data.get('title', book['title']),
        author=data.get('author', book['author']),
        author_nationality=data.get('author_nationality', book.get('author_nationality')),
        version=data.get('version', book.get('version'))
    )
    return jsonify({'message': '更新成功'})

@api_bp.route('/admin/books/<int:book_id>', methods=['DELETE'])
def admin_delete_book(book_id):
    """删除书籍"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    delete_book(book_id)
    return jsonify({'message': '删除成功'})

# ===== 章节 API =====

@api_bp.route('/books/<int:book_id>/chapters', methods=['GET'])
def list_chapters(book_id):
    """获取书籍的所有章节"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    chapters = get_chapters_by_book(book_id)
    return jsonify({'chapters': chapters})

@api_bp.route('/books/<int:book_id>/chapters', methods=['POST'])
def create_chapter(book_id):
    """创建章节"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    data = request.json
    chapter_id = add_chapter(
        book_id=book_id,
        chapter_number=data.get('chapter_number', 1),
        title=data.get('title', '')
    )
    return jsonify({'message': '章节创建成功', 'chapter_id': chapter_id})

@api_bp.route('/chapters/<int:chapter_id>', methods=['PUT'])
def edit_chapter(chapter_id):
    """更新章节"""
    chapter = get_chapter(chapter_id)
    if not chapter:
        return jsonify({'error': '章节不存在'}), 404
    data = request.json
    update_chapter(chapter_id, title=data.get('title', ''))
    return jsonify({'message': '更新成功'})

@api_bp.route('/chapters/<int:chapter_id>', methods=['DELETE'])
def remove_chapter(chapter_id):
    """删除章节"""
    chapter = get_chapter(chapter_id)
    if not chapter:
        return jsonify({'error': '章节不存在'}), 404
    delete_chapter(chapter_id)
    return jsonify({'message': '删除成功'})

@api_bp.route('/chapters/<int:chapter_id>/sections', methods=['GET'])
def list_chapter_sections(chapter_id):
    """获取章节的所有小节"""
    sections = get_sections_by_chapter(chapter_id)
    return jsonify({'sections': sections})

# ===== 小节管理 API =====

@api_bp.route('/admin/sections/<int:section_id>', methods=['PUT'])
def admin_update_section(section_id):
    """更新小节信息"""
    section = get_section(section_id)
    if not section:
        return jsonify({'error': '小节不存在'}), 404
    data = request.json
    update_section(section_id,
        title=data.get('title', section.get('title')),
        content=data.get('content', section['content']),
        summary=data.get('summary', section.get('summary'))
    )
    # 更新字数
    if data.get('content'):
        word_count = len(data['content'])
        update_section_word_count(section_id, word_count)
    return jsonify({'message': '更新成功'})

@api_bp.route('/admin/sections/<int:section_id>', methods=['DELETE'])
def admin_delete_section(section_id):
    """删除小节"""
    section = get_section(section_id)
    if not section:
        return jsonify({'error': '小节不存在'}), 404
    delete_section(section_id)
    return jsonify({'message': '删除成功'})

# ===== 阅读状态 API =====

@api_bp.route('/sections/<int:section_id>/status', methods=['GET'])
def get_status(section_id):
    """获取小节阅读状态"""
    data = request.args
    book_id = data.get('book_id')
    if not book_id:
        return jsonify({'error': '缺少book_id参数'}), 400
    status = get_section_status(book_id, section_id)
    return jsonify({'status': status})

@api_bp.route('/sections/<int:section_id>/status', methods=['POST'])
def set_status(section_id):
    """设置小节阅读状态"""
    data = request.json
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    status = data.get('status', 'unread')
    if not book_id:
        return jsonify({'error': '缺少book_id'}), 400
    if status not in ('unread', 'reading', 'read'):
        return jsonify({'error': '无效的状态值'}), 400
    set_section_status(user_id, book_id, section_id, status)

    # 当状态变为 'read' 时，自动重新计算军衔并返回
    result = {'message': '状态更新成功'}
    if status == 'read' and user_id:
        try:
            rank_info = get_user_military_rank(user_id)
            result['military_rank'] = rank_info
        except Exception as e:
            print(f"[军衔] 计算军衔失败: {e}")

    return jsonify(result)

@api_bp.route('/books/<int:book_id>/reading-status', methods=['GET'])
def get_reading_status(book_id):
    """获取书籍所有节的阅读状态"""
    user_id = request.args.get('user_id', type=int)
    statuses = get_all_section_status(user_id, book_id)
    stats = get_book_reading_stats(user_id, book_id)
    return jsonify({'statuses': statuses, 'stats': stats})

# ===== 用户 API =====

@api_bp.route('/auth/wechat-login', methods=['POST'])
def wechat_login():
    """微信登录（从公众号链接进入）"""
    data = request.json
    wechat_openid = data.get('wechat_openid', '').strip()
    wechat_nickname = data.get('wechat_nickname', '').strip()
    wechat_avatar = data.get('wechat_avatar', '').strip()
    
    if not wechat_openid:
        return jsonify({'error': '缺少微信身份信息'}), 400
    
    # 查找是否已有该微信openid的用户
    user = get_user_by_wechat_openid(wechat_openid)
    if user:
        # 已存在，更新微信信息
        update_user_wechat(user['id'], wechat_openid, wechat_nickname, wechat_avatar)
        user = get_user(user['id'])
    else:
        # 创建新用户
        user_id = create_user(
            wechat_openid=wechat_openid,
            wechat_nickname=wechat_nickname,
            wechat_avatar=wechat_avatar,
            role='user'
        )
        user = get_user(user_id)
    
    # 移除敏感信息
    user.pop('password', None)
    return jsonify({'user': user})

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """手机号密码登录（带设备校验）"""
    data = request.json
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    device_id = data.get('device_id', '').strip()
    transfer_code = data.get('transfer_code', '').strip()
    
    if not phone or not password:
        return jsonify({'error': '请输入手机号和密码'}), 400
    
    user = verify_user_phone_password(phone, password)
    if not user:
        return jsonify({'error': '手机号或密码错误'}), 401
    
    # 设备校验（管理员跳过）
    device_info = data.get('device_info', '').strip()
    is_admin = user.get('role') == 'admin'
    
    if not is_admin:
        if user.get('device_id') and user['device_id'] != device_id:
            # 设备不匹配，需要换机校验码
            if not transfer_code:
                # 获取之前绑定的设备信息
                bound_device_info = user.get('device_info') or '未知设备'
                return jsonify({
                    'error': '设备不匹配，请输入换机校验码',
                    'need_transfer_code': True,
                    'user_id': user['id'],
                    'bound_device': bound_device_info
                }), 403
            
            # 验证换机校验码
            success, msg = verify_transfer_code(user['id'], transfer_code)
            if not success:
                return jsonify({'error': msg, 'need_transfer_code': True}), 403
            
            # 验证成功，更新设备ID和设备信息
            update_user_device(user['id'], device_id, device_info)
        elif not user.get('device_id'):
            # 首次登录，绑定设备
            update_user_device(user['id'], device_id, device_info)
    
    user = get_user(user['id'])
    user.pop('password', None)
    return jsonify({'user': user})

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """用户注册（手机号+密码）"""
    data = request.json
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    
    if not phone or not password:
        return jsonify({'error': '请输入手机号和密码'}), 400
    
    if len(password) < 6:
        return jsonify({'error': '密码至少6位'}), 400
    
    existing = get_user_by_phone(phone)
    if existing:
        return jsonify({'error': '该手机号已注册'}), 400
    
    device_id = data.get('device_id', '').strip()
    device_info = data.get('device_info', '').strip()
    user_id = create_user(phone=phone, password=password, device_id=device_id, device_info=device_info, role='user')
    user = get_user(user_id)
    user.pop('password', None)
    return jsonify({'user': user, 'message': '注册成功'})

@api_bp.route('/auth/bind-phone', methods=['POST'])
def bind_phone():
    """绑定手机号（微信用户首次登录时）"""
    data = request.json
    user_id = data.get('user_id')
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    
    if not user_id or not phone:
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 检查手机号是否已被其他用户绑定
    existing = get_user_by_phone(phone)
    if existing and existing['id'] != user_id:
        return jsonify({'error': '该手机号已被其他用户绑定'}), 400
    
    update_user_phone(user_id, phone, password if password else None)
    user = get_user(user_id)
    user.pop('password', None)
    return jsonify({'user': user, 'message': '绑定成功'})

@api_bp.route('/auth/check', methods=['GET'])
def check_auth():
    """检查登录状态"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    user = get_user(int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 401
    user.pop('password', None)
    return jsonify({'user': user})

@api_bp.route('/users/<int:user_id>/profile', methods=['PUT'])
def update_profile(user_id):
    """更新用户个人信息"""
    data = request.json
    gender = data.get('gender')
    age = data.get('age')
    grade = data.get('grade')
    update_user_profile(user_id, gender, age, grade)
    user = get_user(user_id)
    user.pop('password', None)
    return jsonify({'user': user, 'message': '更新成功'})

@api_bp.route('/users/<int:user_id>/password', methods=['PUT'])
def change_password(user_id):
    """修改密码"""
    data = request.json
    old_password = data.get('old_password', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': '新密码至少6位'}), 400
    
    user = get_user(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    # 如果已有密码，需要验证旧密码
    if user.get('password') and user['password'] != old_password:
        return jsonify({'error': '原密码错误'}), 401
    
    update_user_password(user_id, new_password)
    return jsonify({'message': '密码修改成功'})

# ===== 设备换机 API =====

@api_bp.route('/users/<int:user_id>/transfer-code', methods=['POST'])
def generate_transfer_code(user_id):
    """生成换机校验码"""
    transfer_code = create_transfer_code(user_id)
    return jsonify({
        'transfer_code': transfer_code,
        'message': '换机校验码已生成，1分钟内有效',
        'valid_seconds': 60
    })

# ===== 军衔等级 API =====

@api_bp.route('/users/<int:user_id>/military-rank', methods=['GET'])
def get_military_rank(user_id):
    """获取用户军衔等级信息"""
    user = get_user(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    rank_info = get_user_military_rank(user_id)
    return jsonify(rank_info)

@api_bp.route('/military-ranks', methods=['GET'])
def list_military_ranks():
    """获取所有军衔等级列表（管理用）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM military_ranks ORDER BY rank_level')
    ranks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'ranks': ranks})

# ===== 留言 API =====

@api_bp.route('/messages', methods=['POST'])
def post_message():
    """用户提交留言"""
    data = request.json
    user_id = data.get('user_id')
    content = data.get('content', '').strip()
    
    if not user_id or not content:
        return jsonify({'error': '缺少必要参数'}), 400
    
    message_id = add_message(user_id, content)
    return jsonify({'message_id': message_id, 'message': '留言提交成功'})

@api_bp.route('/users/<int:user_id>/messages', methods=['GET'])
def get_user_messages(user_id):
    """获取用户的留言列表"""
    messages = get_messages_by_user(user_id)
    return jsonify({'messages': messages})

@api_bp.route('/admin/messages', methods=['GET'])
def admin_get_messages():
    """管理员获取所有留言"""
    messages = get_all_messages()
    return jsonify({'messages': messages})

@api_bp.route('/admin/messages/<int:message_id>/reply', methods=['POST'])
def admin_reply_message(message_id):
    """管理员回复留言"""
    data = request.json
    admin_reply = data.get('reply', '').strip()
    if not admin_reply:
        return jsonify({'error': '回复内容不能为空'}), 400
    reply_message(message_id, admin_reply)
    return jsonify({'message': '回复成功'})

# ===== 订阅 API =====

@api_bp.route('/books/<int:book_id>/access', methods=['GET'])
def get_book_access(book_id):
    """获取用户对某本书的访问权限"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    user = get_user(int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 401
    access = check_book_access(int(user_id), book_id, user['role'])
    return jsonify(access)

@api_bp.route('/books/<int:book_id>/subscribe', methods=['POST'])
def request_subscribe(book_id):
    """申请订阅"""
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    user = get_user(int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 401
    if user['role'] == 'admin':
        return jsonify({'message': '系统用户无需订阅'})
    add_subscription_request(int(user_id), book_id)
    return jsonify({'message': '订阅申请已提交，请联系作者审批'})

@api_bp.route('/user/subscriptions', methods=['GET'])
def get_my_subscriptions():
    """获取我的订阅列表"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    subs = get_user_subscriptions(int(user_id))
    return jsonify({'book_ids': subs})

# ===== 管理员-用户管理 API =====

@api_bp.route('/admin/users', methods=['GET'])
def admin_list_users():
    """获取所有用户（支持筛选，含阅读统计）"""
    phone = request.args.get('phone', '').strip() or None
    role = request.args.get('role', '').strip() or None
    gender = request.args.get('gender', '').strip() or None
    age_above = request.args.get('age_above', type=int)
    age_below = request.args.get('age_below', type=int)
    users = get_users_with_stats(phone=phone, role=role, gender=gender, age_above=age_above, age_below=age_below)
    return jsonify({'users': users})

@api_bp.route('/admin/users/<int:user_id>/role', methods=['PUT'])
def admin_update_role(user_id):
    """更新用户角色"""
    data = request.json
    role = data.get('role', 'user')
    if role not in ('admin', 'user'):
        return jsonify({'error': '无效的角色'}), 400
    update_user_role(user_id, role)
    return jsonify({'message': '更新成功'})

@api_bp.route('/admin/users/<int:user_id>/reset-password', methods=['PUT'])
def admin_reset_password(user_id):
    """管理员重置用户密码"""
    data = request.json
    password = data.get('password', '').strip()
    if not password or len(password) < 6:
        return jsonify({'error': '密码至少6位'}), 400
    user = get_user(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    update_user_password(user_id, password)
    return jsonify({'message': '密码重置成功'})

@api_bp.route('/admin/users/<int:user_id>/clear-device', methods=['PUT'])
def admin_clear_device(user_id):
    """管理员清除用户绑定的设备"""
    user = get_user(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    update_user_device(user_id, '', '')
    return jsonify({'message': '设备已清除'})

# ===== 管理员-书籍管理 API =====

@api_bp.route('/admin/books', methods=['GET'])
def admin_list_books():
    """获取书籍列表（含统计信息）"""
    books = get_books_with_stats()
    return jsonify({'books': books})

@api_bp.route('/admin/books/<int:book_id>/price', methods=['PUT'])
def admin_update_book_price(book_id):
    """更新书籍订阅价格"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    data = request.json
    price = data.get('price', 0)
    update_book_price(book_id, price)
    return jsonify({'message': '价格更新成功'})

@api_bp.route('/admin/books/<int:book_id>/public', methods=['PUT'])
def admin_update_book_public(book_id):
    """设置/取消公版书籍"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    data = request.json
    is_public = 1 if data.get('is_public') else 0
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE books SET is_public=? WHERE id=?', (is_public, book_id))
    conn.commit()
    conn.close()
    return jsonify({'message': '公版设置更新成功', 'is_public': is_public})

@api_bp.route('/admin/books/<int:book_id>/icon', methods=['POST'])
def admin_upload_book_icon(book_id):
    """上传书籍图标"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    import os
    
    # api.py 在 backend/ 下，项目根目录是上一级
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_dir = os.path.join(project_root, 'frontend', 'book_icons')
    os.makedirs(icons_dir, exist_ok=True)
    
    # 保存原始文件
    icon_path = f'book_icons/book_{book_id}.png'
    full_path = os.path.join(project_root, 'frontend', icon_path)
    file.save(full_path)
    
    # 尝试用 Pillow 压缩，失败则忽略
    try:
        from PIL import Image
        img = Image.open(full_path)
        if img.mode not in ('RGBA', 'RGB'):
            img = img.convert('RGBA')
        img_resized = img.resize((64, 80), Image.Resampling.LANCZOS)
        img_resized.save(full_path, 'PNG', optimize=True)
    except Exception:
        pass  # Pillow 不可用时直接使用原图
    
    # 更新数据库
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE books SET icon_path=? WHERE id=?', (icon_path, book_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': '图标上传成功', 'icon_path': icon_path})

@api_bp.route('/book_icons/<path:filename>', methods=['GET'])
def serve_book_icon(filename):
    """提供书籍图标"""
    from flask import send_from_directory
    from backend.database import get_db
    icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'book_icons')
    return send_from_directory(icons_dir, filename)

# ===== 名言管理 API =====
@api_bp.route('/admin/quotes', methods=['GET'])
def admin_get_quotes():
    """获取名言列表"""
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, content, author, source, created_at FROM quotes ORDER BY id DESC')
    quotes = cursor.fetchall()
    conn.close()
    return jsonify([{
        'id': q[0], 'content': q[1], 'author': q[2], 'source': q[3], 'created_at': q[4]
    } for q in quotes])

@api_bp.route('/admin/quotes', methods=['POST'])
def admin_add_quote():
    """添加名言"""
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '名言内容不能为空'}), 400
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO quotes (content, author, source) VALUES (?, ?, ?)',
                   (content, data.get('author', ''), data.get('source', '')))
    conn.commit()
    quote_id = cursor.lastrowid
    conn.close()
    return jsonify({'id': quote_id, 'message': '添加成功'})

@api_bp.route('/admin/quotes/<int:quote_id>', methods=['PUT'])
def admin_update_quote(quote_id):
    """更新名言"""
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '名言内容不能为空'}), 400
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE quotes SET content=?, author=?, source=? WHERE id=?',
                   (content, data.get('author', ''), data.get('source', ''), quote_id))
    conn.commit()
    conn.close()
    return jsonify({'message': '更新成功'})

@api_bp.route('/admin/quotes/<int:quote_id>', methods=['DELETE'])
def admin_delete_quote(quote_id):
    """删除名言"""
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM quotes WHERE id=?', (quote_id,))
    cursor.execute('DELETE FROM quote_usage WHERE quote_id=?', (quote_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})

@api_bp.route('/admin/quotes/import', methods=['POST'])
def admin_import_quotes():
    """批量导入名言"""
    data = request.json
    quotes = data.get('quotes', [])
    if not quotes:
        return jsonify({'error': '没有名言数据'}), 400
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    count = 0
    for q in quotes:
        content = q.get('content', '').strip()
        if content:
            cursor.execute('INSERT INTO quotes (content, author, source) VALUES (?, ?, ?)',
                           (content, q.get('author', ''), q.get('source', '')))
            count += 1
    conn.commit()
    conn.close()
    return jsonify({'message': f'成功导入 {count} 条名言', 'count': count})

@api_bp.route('/quote/random', methods=['GET'])
def get_random_quote():
    """获取随机名言（用于阅读页面）"""
    book_id = request.args.get('book_id', type=int)
    section_id = request.args.get('section_id', type=int)
    user_id = request.args.get('user_id', type=int)
    
    from backend.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取总数
    cursor.execute('SELECT COUNT(*) FROM quotes')
    total = cursor.fetchone()[0]
    if total == 0:
        conn.close()
        return jsonify({'quotes': []})
    
    # 获取该书该用户已用过的名言ID
    if book_id and section_id and user_id:
        cursor.execute('''
            SELECT quote_id FROM quote_usage 
            WHERE book_id=? AND user_id=?
        ''', (book_id, user_id))
        used_ids = [r[0] for r in cursor.fetchall()]
    else:
        used_ids = []
    
    # 优先选择未用过的名言，取2条
    count = min(2, total)
    if used_ids and len(used_ids) < total:
        placeholders = ','.join('?' * len(used_ids))
        cursor.execute(f'''
            SELECT id, content, author, source FROM quotes 
            WHERE id NOT IN ({placeholders})
            ORDER BY RANDOM() LIMIT ?
        ''', used_ids + [count])
    else:
        cursor.execute('SELECT id, content, author, source FROM quotes ORDER BY RANDOM() LIMIT ?', (count,))
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        results.append({'id': row[0], 'content': row[1], 'author': row[2], 'source': row[3]})
        # 记录使用
        if book_id and section_id and user_id:
            cursor.execute('''
                INSERT INTO quote_usage (quote_id, book_id, section_id, user_id)
                VALUES (?, ?, ?, ?)
            ''', (row[0], book_id, section_id, user_id))
    
    if book_id and section_id and user_id:
        conn.commit()
    conn.close()
    return jsonify({'quotes': results})

@api_bp.route('/admin/quotes/parse-word', methods=['POST'])
def admin_parse_word_quotes():
    """解析Word文档中的名言"""
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    filename = file.filename.lower()
    text = ''
    
    try:
        if filename.endswith('.txt'):
            # 文本文件直接读取
            text = file.read().decode('utf-8')
        elif filename.endswith('.docx'):
            # Word文档用python-docx解析
            try:
                from docx import Document
                doc = Document(file.stream)
                paragraphs = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        paragraphs.append(para.text.strip())
                text = '\n'.join(paragraphs)
            except ImportError:
                return jsonify({'error': '服务器未安装python-docx，无法解析Word文档'}), 500
        elif filename.endswith('.doc'):
            # 旧版doc格式，尝试用antiword或其他工具
            return jsonify({'error': '暂不支持.doc格式，请转换为.docx或.txt后上传'}), 400
        else:
            return jsonify({'error': '不支持的文件格式'}), 400
        
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/books/<int:book_id>/catalog-stats', methods=['GET'])
def admin_book_catalog_stats(book_id):
    """获取书籍目录结构及统计"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    catalog = get_book_catalog_stats(book_id)
    return jsonify(catalog)

# ===== 管理员-订阅管理 API =====

@api_bp.route('/admin/subscriptions', methods=['GET'])
def admin_list_subscriptions():
    """获取用户订阅列表（按手机号搜索）"""
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify({'error': '缺少phone参数'}), 400
    user = get_user_by_phone(phone)
    if not user:
        return jsonify({'subscriptions': []})
    subs = get_user_subscription_stats(user['id'])
    return jsonify({'subscriptions': subs, 'user_id': user['id']})

@api_bp.route('/admin/subscriptions', methods=['POST'])
def admin_add_sub():
    """管理员添加订阅"""
    data = request.json
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    if not user_id or not book_id:
        return jsonify({'error': '缺少user_id或book_id'}), 400
    admin_add_subscription(user_id, book_id)
    return jsonify({'message': '订阅添加成功'})

@api_bp.route('/admin/subscriptions', methods=['DELETE'])
def admin_remove_sub():
    """管理员移除订阅"""
    data = request.json
    user_id = data.get('user_id')
    book_id = data.get('book_id')
    if not user_id or not book_id:
        return jsonify({'error': '缺少user_id或book_id'}), 400
    admin_remove_subscription(user_id, book_id)
    return jsonify({'message': '订阅已移除'})

# ===== 管理员-章节/节重新导入 API =====

@api_bp.route('/admin/books/<int:book_id>/reimport-chapter/<int:chapter_id>', methods=['POST'])
def admin_reimport_chapter(book_id, chapter_id):
    """重新导入章节：上传 .docx 文件，更新指定章节的所有小节（保持section_id不变）"""
    # 验证文件
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名不能为空'}), 400
    if not file.filename.endswith('.docx'):
        return jsonify({'error': '仅支持 .docx 文件'}), 400

    # 验证章节存在且属于该书籍
    chapter = get_chapter(chapter_id)
    if not chapter or chapter['book_id'] != book_id:
        return jsonify({'error': '章节不存在或不属于该书籍'}), 404

    # 保存文件
    filename = file.filename
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        # 解析文件
        from backend.word_parser import parse_file as parse_word
        result = parse_word(filepath)

        sections = result.get('sections', [])
        chapter_number = chapter['chapter_number']

        # 筛选属于该章节的小节
        matched_sections = [s for s in sections if s.get('chapter_number') == chapter_number]
        
        print(f"[Reimport] Found {len(matched_sections)} sections for chapter {chapter_number}")
        for s in matched_sections:
            print(f"[Reimport]   Section {s.get('section_number')}: {len(s.get('annotations', []))} annotations")

        if not matched_sections:
            return jsonify({'error': f'文件中未找到第 {chapter_number} 章的小节'}), 400

        # 获取该章节下现有的所有小节
        from backend.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, section_number FROM sections WHERE chapter_id=?', (chapter_id,))
        existing_sections = {row[1]: row[0] for row in cursor.fetchall()}  # section_number -> section_id
        conn.close()

        # 处理每个匹配的小节：更新现有或新增
        for sec in matched_sections:
            sec_number = sec['section_number']
            content = sec.get('content', '')
            title = sec.get('title', '')
            summary = sec.get('summary', '')
            word_count = len(content)

            if sec_number in existing_sections:
                # 更新现有小节（保持section_id不变）
                sec_id = existing_sections[sec_number]
                conn = get_db()
                cursor = conn.cursor()
                # 删除旧的点评
                cursor.execute('DELETE FROM annotations WHERE section_id = ?', (sec_id,))
                # 更新小节内容
                cursor.execute('UPDATE sections SET title = ?, content = ?, summary = ?, word_count = ? WHERE id = ?',
                              (title, content, summary, word_count, sec_id))
                conn.commit()
                conn.close()
            else:
                # 新增小节
                sec_id = add_section(
                    book_id=book_id,
                    chapter_id=chapter_id,
                    section_number=sec_number,
                    content=content,
                    title=title
                )
                # 设置小结
                if summary:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE sections SET summary = ? WHERE id = ?', (summary, sec_id))
                    conn.commit()
                    conn.close()

            # 保存点评（在同一连接中操作，确保事务一致性）
            annotations = sec.get('annotations', [])
            print(f"[Reimport Chapter] Section {sec_number}: {len(annotations)} annotations to save")
            if annotations:
                conn = get_db()
                cursor = conn.cursor()
                for idx, anno in enumerate(annotations):
                    cursor.execute(
                        '''INSERT INTO annotations (section_id, annotation_index, start_char, end_char, original_text, comment)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (sec_id, idx + 1, anno.get('start_char', 0), anno.get('end_char', 0),
                         anno.get('original_text', ''), anno.get('comment', ''))
                    )
                conn.commit()
                conn.close()

        # 更新章节统计
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(word_count), 0) FROM sections WHERE chapter_id=?', (chapter_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            update_chapter_info(chapter_id, row[0], row[1])

        # 更新书籍总小节数
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sections WHERE book_id=?', (book_id,))
        total_sections = cursor.fetchone()[0]
        conn.close()
        update_book_sections_count(book_id, total_sections)

        # 为更新的节生成分段TTS音频（按点评边界分割）
        try:
            from backend.baidu_tts import generate_segmented_audio
            from backend.database import update_section_audio_timeline, update_section_audio_segments, get_annotations_by_section
            import threading
            def generate_tts_for_chapter():
                for sec in matched_sections:
                    sec_number = sec['section_number']
                    if sec_number in existing_sections:
                        sec_id = existing_sections[sec_number]
                        # 从数据库重新加载点评（获取正确的id）
                        annotations = get_annotations_by_section(sec_id)
                        print(f"[TTS] 为节 {sec_id} 生成音频，点评数: {len(annotations)}")
                        # 按点评边界生成分段音频
                        result = generate_segmented_audio(
                            sec.get('content', ''),
                            sec_id,
                            annotations=annotations,
                            speed=5,
                            person=0
                        )
                        if result:
                            update_section_audio_timeline(sec_id, result['audio_duration'], result['char_timeline'], result['audio_path'])
                            if result.get('audio_segments'):
                                update_section_audio_segments(sec_id, result['audio_segments'])
                            print(f"[TTS] 节 {sec_id} 音频生成完成")
            t = threading.Thread(target=generate_tts_for_chapter)
            t.daemon = True
            t.start()
        except Exception as e:
            print(f'[TTS] 章节分段音频生成失败: {e}')

        return jsonify({
            'message': '章节导入成功（音频生成中）',
            'section_count': len(matched_sections),
            'section_ids': [existing_sections[s['section_number']] for s in matched_sections if s['section_number'] in existing_sections]
        })

    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

@api_bp.route('/admin/books/<int:book_id>/reimport-section/<int:section_id>', methods=['POST'])
def admin_reimport_section(book_id, section_id):
    """重新导入小节：上传 .docx 文件，更新指定小节的内容（保持section_id和阅读状态不变）"""
    # 验证文件
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名不能为空'}), 400
    if not file.filename.endswith('.docx'):
        return jsonify({'error': '仅支持 .docx 文件'}), 400

    # 验证小节存在且属于该书籍
    section = get_section(section_id)
    if not section or section['book_id'] != book_id:
        return jsonify({'error': '小节不存在或不属于该书籍'}), 404

    # 保存文件
    filename = file.filename
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        # 解析文件
        from backend.word_parser import parse_file as parse_word
        result = parse_word(filepath)

        sections = result.get('sections', [])
        target_section_number = section['section_number']
        chapter_id = section['chapter_id']

        # 查找匹配的小节（按 section_number 匹配）
        matched_section = None
        for sec in sections:
            if sec.get('section_number') == target_section_number:
                matched_section = sec
                break

        if not matched_section:
            return jsonify({'error': f'文件中未找到第 {target_section_number} 小节'}), 400

        content = matched_section.get('content', '')
        title = matched_section.get('title', '')
        summary = matched_section.get('summary', '')
        word_count = len(content)

        # 删除旧点评并更新内容（同一事务）
        from backend.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM annotations WHERE section_id = ?', (section_id,))
        cursor.execute('UPDATE sections SET title = ?, content = ?, summary = ?, word_count = ? WHERE id = ?',
                      (title, content, summary, word_count, section_id))
        conn.commit()
        conn.close()

        # 重新创建点评（同一事务）
        annotations = matched_section.get('annotations', [])
        if annotations:
            conn = get_db()
            cursor = conn.cursor()
            for idx, anno in enumerate(annotations):
                cursor.execute(
                    '''INSERT INTO annotations (section_id, annotation_index, start_char, end_char, original_text, comment)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (section_id, idx + 1, anno.get('start_char', 0), anno.get('end_char', 0),
                     anno.get('original_text', ''), anno.get('comment', ''))
                )
            conn.commit()
            conn.close()

        # 更新章节统计
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(word_count), 0) FROM sections WHERE chapter_id=?', (chapter_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            update_chapter_info(chapter_id, row[0], row[1])

        # 更新书籍总小节数
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sections WHERE book_id=?', (book_id,))
        total_sections = cursor.fetchone()[0]
        conn.close()
        update_book_sections_count(book_id, total_sections)

        # 为更新的节生成分段TTS音频（按点评边界分割）
        try:
            from backend.baidu_tts import generate_segmented_audio
            from backend.database import update_section_audio_timeline, update_section_audio_segments, get_annotations_by_section
            import threading
            def generate_tts_for_section():
                # 从数据库重新加载点评（获取正确的id）
                db_annotations = get_annotations_by_section(section_id)
                print(f"[TTS] 为节 {section_id} 生成音频，点评数: {len(db_annotations)}")
                # 按点评边界生成分段音频
                result = generate_segmented_audio(
                    content,
                    section_id,
                    annotations=db_annotations,
                    speed=5,
                    person=0
                )
                if result:
                    update_section_audio_timeline(section_id, result['audio_duration'], result['char_timeline'], result['audio_path'])
                    if result.get('audio_segments'):
                        update_section_audio_segments(section_id, result['audio_segments'])
                    print(f"[TTS] 节 {section_id} 音频生成完成")
            t = threading.Thread(target=generate_tts_for_section)
            t.daemon = True
            t.start()
        except Exception as e:
            print(f'[TTS] 小节分段音频生成失败: {e}')

        return jsonify({'message': '小节导入成功（音频生成中）', 'section_ids': [section_id]})

    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

# ===== 管理员-订阅审批 API =====

@api_bp.route('/admin/subscription-requests', methods=['GET'])
def admin_list_sub_requests():
    """获取所有订阅申请"""
    requests = get_subscription_requests()
    return jsonify({'requests': requests})

@api_bp.route('/admin/subscription-requests/<int:request_id>/approve', methods=['POST'])
def admin_approve_sub(request_id):
    """审批通过订阅"""
    approve_subscription_request(request_id)
    return jsonify({'message': '已通过'})

@api_bp.route('/admin/subscription-requests/<int:request_id>/reject', methods=['POST'])
def admin_reject_sub(request_id):
    """拒绝订阅"""
    reject_subscription_request(request_id)
    return jsonify({'message': '已拒绝'})

# ===== 思考 API =====

@api_bp.route('/sections/<int:section_id>/thoughts', methods=['GET'])
def list_thoughts(section_id):
    """获取节的思考（仅自己可见）"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'thoughts': []})
    # 只返回当前用户自己的思考
    thoughts = get_thoughts_by_section(section_id, int(user_id))
    return jsonify({'thoughts': thoughts})

@api_bp.route('/sections/<int:section_id>/thoughts', methods=['POST'])
def create_thought(section_id):
    """创建思考（带 AI 评分）"""
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    
    original_text = data.get('original_text', '')
    thought_content = data.get('content', '')
    
    # AI 评分
    ai_score, score_reason = rate_thought(original_text, thought_content)
    print(f"[思考评分] 用户 {user_id} 的思考评分: {ai_score} - {score_reason}")
    
    thought_id = add_thought(
        user_id=int(user_id),
        section_id=section_id,
        start_char=data.get('start_char', 0),
        end_char=data.get('end_char', 0),
        original_text=original_text,
        content=thought_content,
        ai_score=ai_score
    )
    return jsonify({
        'thought_id': thought_id,
        'ai_score': ai_score,
        'score_reason': score_reason,
        'message': '思考已保存'
    })

@api_bp.route('/thoughts/<int:thought_id>', methods=['DELETE'])
def remove_thought(thought_id):
    """删除思考"""
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    delete_thought(thought_id, int(user_id))
    return jsonify({'message': '已删除'})

@api_bp.route('/thoughts/<int:thought_id>', methods=['PUT'])
def edit_thought(thought_id):
    """更新思考"""
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    update_thought(thought_id, int(user_id), data.get('content', ''))
    return jsonify({'message': '已更新'})
