# -*- coding: utf-8 -*-
"""
悦读小将 - API 路由
"""

from flask import Blueprint, request, jsonify, send_file
import os
import sys
import threading
import time
import pymysql

# 导入状态存储 {book_id: {'status': str, 'message': str, 'updated_at': float}}
_import_status = {}
_import_lock = threading.Lock()

def _set_import_status(book_id, status, message):
    with _import_lock:
        _import_status[book_id] = {'status': status, 'message': message, 'updated_at': time.time()}

def _get_import_status(book_id):
    with _import_lock:
        return _import_status.get(book_id)

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
    # 军功勋章系统
    check_and_award_merits, check_and_award_medals, get_user_merits, get_user_medals,
    get_db,
)
from backend.text_parser import parse_file, get_book_title
from backend.tts_service import generate_audio
from backend.ai_score import rate_thought
import hashlib
import xml.etree.ElementTree as ET

api_bp = Blueprint('api', __name__)

# 微信公众号配置（需要在环境变量中设置）
WECHAT_TOKEN = os.environ.get('WECHAT_TOKEN', 'reading2026')  # 公众号Token
WECHAT_APPID = os.environ.get('WECHAT_APPID', 'wx6032ec9465fc7483')
WECHAT_APPSECRET = os.environ.get('WECHAT_APPSECRET', '')

# 文件上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'books')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def reimport_section_core(section_id, content, annotations, title='', summary='', voice_type='male'):
    """
    统一的节导入核心函数：清除历史数据，重新创建分段，生成音频
    返回: {'success': bool, 'audio_segments_count': int, 'error': str}
    """
    from backend.database import (
        get_db, update_section_audio_timeline, update_section_audio_segments,
        get_annotations_by_section, create_text_segments, create_insert_points,
        get_section
    )
    from backend.baidu_tts import generate_section_audio_v2, is_configured

    result = {'success': False, 'audio_segments_count': 0, 'error': ''}

    # 获取 book_id（用于文件命名）
    book_id = None
    try:
        section = get_section(section_id)
        if section:
            book_id = section.get('book_id')
    except Exception as e:
        print(f"[reimport_core] 获取book_id失败: {e}")
    
    # 如果没有传入voice_type，从数据库获取
    if not voice_type or voice_type not in ['male', 'female']:
        try:
            if not section:
                section = get_section(section_id)
            if section:
                bid = section.get('book_id') or book_id
                if bid:
                    from backend.database import get_book
                    book = get_book(bid)
                    if book:
                        voice_type = book.get('voice_type', 'male')
        except Exception as e:
            print(f"[reimport_core] 获取voice_type失败: {e}")
            voice_type = 'male'

    try:
        # 1. 清除节的历史数据
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM annotations WHERE section_id = %s', (section_id,))
        cursor.execute('DELETE FROM text_segments WHERE section_id = %s', (section_id,))
        cursor.execute('DELETE FROM insert_points WHERE section_id = %s', (section_id,))
        cursor.execute('UPDATE sections SET audio_path = NULL, audio_duration = NULL, char_timeline = NULL, summary_audio_path = NULL WHERE id = %s', (section_id,))
        if title:
            cursor.execute('UPDATE sections SET title = %s WHERE id = %s', (title, section_id))
        if summary:
            cursor.execute('UPDATE sections SET summary = %s WHERE id = %s', (summary, section_id))
        conn.commit()
        conn.close()
        print(f"[reimport_core] 节 {section_id}: 历史数据已清除")

        # 2. 保存新的点评
        if annotations:
            conn = get_db()
            cursor = conn.cursor()
            for idx, anno in enumerate(annotations):
                cursor.execute(
                    '''INSERT INTO annotations (section_id, annotation_index, start_char, end_char, original_text, comment)
                       VALUES (%s, %s, %s, %s, %s, %s)''',
                    (section_id, idx + 1, anno.get('start_char', 0), anno.get('end_char', 0),
                     anno.get('original_text', ''), anno.get('comment', ''))
                )
            conn.commit()
            conn.close()
            print(f"[reimport_core] 节 {section_id}: 保存 {len(annotations)} 个点评")

        # 3. 检查 TTS 配置
        if not is_configured():
            result['error'] = 'TTS未配置'
            print(f"[reimport_core] 节 {section_id}: TTS未配置")
            return result

        # 4. 调用新版 v2 音频生成（内部自动完成：创建分段 + TTS + 更新DB）
        print(f"[reimport_core] 节 {section_id}: 开始生成音频 (book={book_id})...")
        audio_success = generate_section_audio_v2(
            book_id, section_id,
            speed=5,
            person=3  # person=3 度逍遥（原文男声）
        )

        if audio_success:
            result['success'] = True
            result['audio_segments_count'] = -1  # v2 内部处理段数，返回True即全部成功
            print(f"[reimport_core] 节 {section_id}: 音频生成完成")
        else:
            result['error'] = 'v2音频生成返回False'
            print(f"[reimport_core] 节 {section_id}: 音频生成失败")

    except Exception as e:
        result['error'] = f'{type(e).__name__}: {e}'
        print(f"[reimport_core] 节 {section_id}: 异常: {result['error']}")
        import traceback
        traceback.print_exc()

    return result


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
        
        # 记录验证请求日志
        import logging
        logging.basicConfig(level=logging.INFO)
        logging.info(f"WeChat verify: signature={signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")
        logging.info(f"Using TOKEN: {WECHAT_TOKEN}")
        
        # 验证签名
        tmp_list = [WECHAT_TOKEN, timestamp, nonce]
        tmp_list.sort()
        tmp_str = ''.join(tmp_list)
        tmp_hash = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        
        logging.info(f"Calculated hash: {tmp_hash}, Expected: {signature}")
        
        if tmp_hash == signature:
            logging.info("WeChat verification success")
            return echostr
        else:
            logging.warning("WeChat verification failed")
            return 'invalid signature', 403
    
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
                    if event_key == 'welcome':
                        return _make_text_reply(to_user, from_user,
                            '🎉 欢迎来到悦读小将！\n\n'
                            '这里是专为儿童设计的课外阅读辅助工具。\n'
                            '帮助孩子养成阅读习惯，提升阅读能力。\n\n'
                            '点击"悦读小将"开始阅读之旅吧！')
                    elif event_key == 'start_reading':
                        # 返回带用户openid的链接
                        url = f"https://lit.handy.xin/?wechat_openid={from_user}"
                        return _make_text_reply(to_user, from_user, 
                            f'点击链接进入悦读小将：\n{url}')
                    elif event_key == 'help':
                        return _make_text_reply(to_user, from_user,
                            '📖 悦读小将使用帮助\n\n'
                            '1. 点击"悦读小将"进入系统\n'
                            '2. 首次使用需绑定手机号\n'
                            '3. 选择书籍开始阅读\n'
                            '4. 阅读后可提交思考获得AI评分\n'
                            '5. 累计阅读可提升军衔等级\n\n'
                            '如有问题请留言反馈～')
            
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
    cursor.execute('''SELECT id, title, author, author_nationality, version, total_sections, total_chapters, is_public, icon_path
                      FROM books WHERE is_public=1 ORDER BY id DESC''')
    books = [dict(row) for row in cursor.fetchall()]
    
    # 验证图标文件是否存在
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for book in books:
        bid = book['id']
        icon_path = book.get('icon_path')
        if icon_path:
            # 检查默认路径
            full_path = os.path.join(project_root, 'frontend', icon_path)
            if not os.path.exists(full_path):
                # 检查环境变量配置的路径
                env_path = os.environ.get('BOOK_ICONS_PATH')
                if env_path:
                    full_path = os.path.join(env_path, os.path.basename(icon_path))
                if not os.path.exists(full_path):
                    book['icon_path'] = None
        
        cursor.execute('SELECT COALESCE(SUM(word_count),0) as total_words FROM sections WHERE book_id=%s', (bid,))
        book['total_words'] = cursor.fetchone()['total_words']
        cursor.execute('''SELECT COUNT(*) as cnt FROM annotations a
                          JOIN sections s ON a.section_id = s.id WHERE s.book_id=%s''', (bid,))
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
        cursor.execute('SELECT COALESCE(SUM(word_count),0) as total_words FROM sections WHERE book_id=%s', (bid,))
        book['total_words'] = cursor.fetchone()['total_words']
        cursor.execute('''SELECT COUNT(*) as cnt FROM annotations a
                          JOIN sections s ON a.section_id = s.id WHERE s.book_id=%s''', (bid,))
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

@api_bp.route('/books/<int:book_id>/sections', methods=['GET'])
def list_book_sections(book_id):
    """获取书籍的所有小节（简化列表，用于下拉选择）"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404

    sections = get_sections_by_book(book_id)
    # 返回精简字段，前端只需要 id / section_number / title
    result = []
    for sec in sections:
        result.append({
            'id': sec['id'],
            'section_number': sec['section_number'],
            'title': sec.get('title', '') or ''
        })
    return jsonify(result)

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
    
    # 解析文件（提取章节 + 节）
    try:
        # 优先使用 Word 结构解析器
        if filepath.endswith('.docx'):
            from backend.word_parser import parse_file as parse_word
            result = parse_word(filepath)
        else:
            result = parse_file(filepath)
        
        chapters = result.get('chapters', [])
        sections = result.get('sections', [])
        
        # 支持传入 book_id，直接导入到指定书籍
        book_id = request.form.get('book_id', type=int)
        is_update = False
        
        if book_id:
            # 导入到已有书籍
            book = get_book(book_id)
            if not book:
                return jsonify({'error': '指定的书籍不存在'}), 404
            is_update = True
            # 更新文件路径
            from backend.database import get_db
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE books SET file_path = %s WHERE id = %s', (filepath, book_id))
            conn.commit()
            conn.close()
            # 删除旧的章节、节、点评，重新导入
            from backend.database import get_db as _get_db
            _conn = _get_db()
            _c = _conn.cursor()
            _c.execute('DELETE FROM annotations WHERE section_id IN (SELECT id FROM sections WHERE book_id=%s)', (book_id,))
            _c.execute('DELETE FROM sections WHERE book_id=%s', (book_id,))
            _c.execute('DELETE FROM chapters WHERE book_id=%s', (book_id,))
            _conn.commit()
            _conn.close()
        else:
            # 旧逻辑：从文件解析元信息并自动创建/更新书籍
            title = result.get('title', get_book_title(filepath))
            author = result.get('author', '')
            author_nationality = result.get('author_nationality', '')
            version = result.get('version', '')
            
            print(f"[UPLOAD] 解析结果: 标题={title}, 作者={author}, 国籍={author_nationality}, 版本={version}")
            
            existing_book = get_book_by_title_author_version(title, author, version)
            
            if existing_book:
                book_id = existing_book['id']
                is_update = True
                from backend.database import get_db
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('UPDATE books SET file_path = %s WHERE id = %s', (filepath, book_id))
                conn.commit()
                conn.close()
                old_chapters = get_chapters_by_book(book_id)
                for ch in old_chapters:
                    delete_chapter(ch['id'])
                from backend.database import get_db as _get_db
                _conn = _get_db()
                _c = _conn.cursor()
                _c.execute('DELETE FROM annotations WHERE section_id IN (SELECT id FROM sections WHERE book_id=%s)', (book_id,))
                _c.execute('DELETE FROM sections WHERE book_id=%s', (book_id,))
                _c.execute('DELETE FROM chapters WHERE book_id=%s', (book_id,))
                _conn.commit()
                _conn.close()
            else:
                book_id = add_book(title=title, author=author, file_path=filepath)
                if author_nationality or version:
                    update_book(book_id, title=title, author=author,
                               author_nationality=author_nationality, version=version)
        
        # 设置导入状态
        _set_import_status(book_id, 'importing', '原文导入开始')
        
        # 保存章节到数据库
        chapter_id_map = {}  # chapter_number -> chapter_id
        for ch in chapters:
            ch_id = add_chapter(
                book_id=book_id,
                chapter_number=ch['chapter_number'],
                title=ch.get('title', '')
            )
            chapter_id_map[ch['chapter_number']] = ch_id
        
        # 保存小节到数据库（将 sec_id 写入每个 sec 字典，避免用 section_number 做 key 被覆盖）
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
            sec['id'] = sec_id  # 直接写入，供异步音频生成使用

            # 保存小结（从批注解析）
            if sec.get('summary'):
                from backend.database import get_db
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('UPDATE sections SET summary = %s WHERE id = %s', (sec['summary'], sec_id))
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

        # 原文导入完成，音频生成改为后台异步处理
        def generate_audio_async(book_id, sections):
            """后台异步生成音频"""
            try:
                _set_import_status(book_id, 'generating', '音频生成开始')
                failed_count = 0
                total_count = len(sections)
                
                for i, sec in enumerate(sections):
                    sec_id = sec.get('id')
                    if not sec_id:
                        continue
                    result = reimport_section_core(
                        section_id=sec_id,
                        content=sec.get('content', ''),
                        annotations=sec.get('annotations', []),
                        title=sec.get('title', ''),
                        summary=sec.get('summary', '')
                    )
                    if not result['success']:
                        failed_count += 1
                        print(f"[upload] 节 {sec_id} 音频生成失败: {result['error']}")
                    _set_import_status(book_id, 'generating', f'音频生成中 {i+1}/{total_count}')
                
                if failed_count == 0:
                    _set_import_status(book_id, 'done', f'音频生成完成 {total_count}/{total_count}')
                else:
                    _set_import_status(book_id, 'tts_error', f'音频生成完成，{failed_count}个节失败')
            except Exception as e:
                print(f"[upload] 音频生成异常: {e}")
                _set_import_status(book_id, 'error', f'音频生成异常: {str(e)}')
        
        # 启动后台线程生成音频
        import threading
        audio_thread = threading.Thread(
            target=generate_audio_async,
            args=(book_id, sections),
            daemon=True
        )
        audio_thread.start()

        return jsonify({
            'message': '更新成功' if is_update else '上传成功',
            'book_id': book_id,
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
    """为节生成音频（新版v2，统一入口）"""
    from backend.database import get_section
    from backend.baidu_tts import generate_section_audio_v2

    section = get_section(section_id)
    if not section:
        return jsonify({'error': '节不存在'}), 404

    book_id = section.get('book_id')
    success = generate_section_audio_v2(book_id, section_id, speed=5, person=3)

    if success:
        return jsonify({
            'success': True,
            'message': '音频生成完成'
        })
    else:
        return jsonify({'error': '音频生成失败'}), 500

@api_bp.route('/sections/<int:section_id>/generate-segmented-audio', methods=['POST'])
def generate_segmented_audio_api(section_id):
    """为节生成分段音频（新版v2，统一入口）"""
    try:
        from backend.database import get_section
        from backend.baidu_tts import generate_section_audio_v2

        section = get_section(section_id)
        if not section:
            return jsonify({'error': '节不存在'}), 404

        book_id = section.get('book_id')
        print(f"[TTS] 开始为节 {section_id} 生成分段音频 (book={book_id})...")

        success = generate_section_audio_v2(book_id, section_id, speed=5, person=3)

        if success:
            return jsonify({
                'success': True,
                'message': '分段音频生成完成'
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
    cursor.execute('SELECT tts_status, tts_progress, total_sections FROM books WHERE id = %s', (book_id,))
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

@api_bp.route('/sections/<int:section_id>/fix-audio', methods=['POST'])
def fix_section_audio(section_id):
    """检查并修复某节缺失的音频文件（只生成缺失的段）"""
    import threading
    from backend.database import get_section, get_annotations_by_section
    from backend.baidu_tts import text_to_speech_long

    section = get_section(section_id)
    if not section:
        return jsonify({'error': '节不存在'}), 404

    # 收集缺失的段信息
    conn = get_db()
    cursor = conn.cursor()
    # 缺失的 text_segments
    cursor.execute("SELECT id, start_char, end_char FROM text_segments WHERE section_id = %s AND (audio_path IS NULL OR audio_path = '') ORDER BY start_char", (section_id,))
    missing_segs = [dict(row) for row in cursor.fetchall()]
    # 缺失的 insert_points
    cursor.execute("SELECT id, point_type, comment FROM insert_points WHERE section_id = %s AND (audio_path IS NULL OR audio_path = '')", (section_id,))
    missing_ips = [dict(row) for row in cursor.fetchall()]
    conn.close()

    total_missing = len(missing_segs) + len(missing_ips)
    if total_missing == 0:
        return jsonify({'message': '音频完整，无需修复', 'missing': 0})

    # 异步逐个修复缺失的音频
    def do_fix():
        fixed = 0
        failed = 0
        try:
            # 修复缺失的 text_segments
            for seg in missing_segs:
                try:
                    text = section['content'][seg['start_char']:seg['end_char']]
                    if not text.strip():
                        print(f'[fix-audio] 段{seg["id"]} 文本为空，跳过')
                        continue
                    audio_paths = text_to_speech_long(text, section_id=section_id)
                    if audio_paths and len(audio_paths) > 0:
                        # 转换路径格式：audio_files/xxx.mp3 -> /api/audio/xxx.mp3
                        raw_path = audio_paths[0]
                        if raw_path.startswith('audio_files/'):
                            audio_path = '/api/audio/' + raw_path.replace('audio_files/', '')
                        else:
                            audio_path = raw_path
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE text_segments SET audio_path = %s WHERE id = %s", (audio_path, seg['id']))
                        conn.commit()
                        conn.close()
                        fixed += 1
                        print(f'[fix-audio] 段{seg["id"]} 音频修复成功: {audio_path}')
                    else:
                        failed += 1
                        print(f'[fix-audio] 段{seg["id"]} 音频生成失败')
                except Exception as e:
                    failed += 1
                    print(f'[fix-audio] 段{seg["id"]} 修复异常: {e}')

            # 修复缺失的 insert_points（点评/小结）
            for ip in missing_ips:
                try:
                    text = ip.get('comment', '') or ''
                    if ip.get('point_type') == 'summary':
                        # 小结需要从 section.summary 获取
                        from backend.database import get_section
                        sec = get_section(section_id)
                        text = sec.get('summary', '') or ''
                    if not text.strip():
                        print(f'[fix-audio] 插入点{ip["id"]} 文本为空，跳过')
                        continue
                    audio_paths = text_to_speech_long(text, section_id=section_id)
                    if audio_paths and len(audio_paths) > 0:
                        # 转换路径格式
                        raw_path = audio_paths[0]
                        if raw_path.startswith('audio_files/'):
                            audio_path = '/api/audio/' + raw_path.replace('audio_files/', '')
                        else:
                            audio_path = raw_path
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE insert_points SET audio_path = %s WHERE id = %s", (audio_path, ip['id']))
                        conn.commit()
                        conn.close()
                        fixed += 1
                        print(f'[fix-audio] 插入点{ip["id"]} 音频修复成功: {audio_path}')
                    else:
                        failed += 1
                        print(f'[fix-audio] 插入点{ip["id"]} 音频生成失败')
                except Exception as e:
                    failed += 1
                    print(f'[fix-audio] 插入点{ip["id"]} 修复异常: {e}')

            print(f'[fix-audio] 节{section_id} 修复完成: 成功{fixed}, 失败{failed}, 共{total_missing}')
        except Exception as e:
            print(f'[fix-audio] 节{section_id} 修复异常: {e}')
            import traceback
            traceback.print_exc()

    thread = threading.Thread(target=do_fix, daemon=True)
    thread.start()

    return jsonify({'message': f'正在修复音频，缺失{total_missing}个文件', 'missing': total_missing})

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

    if not user_id:
        return jsonify({'error': '缺少用户ID'}), 400
    if not book_id or not section_id:
        return jsonify({'error': '缺少书籍或节ID'}), 400

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
        version=data.get('version', book.get('version')),
        voice_type=data.get('voice_type', book.get('voice_type', 'male'))
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
    # 获取用户军衔信息
    military_rank = get_user_military_rank(user['id'])
    return jsonify({'user': user, 'military_rank': military_rank})

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
    # 获取用户军衔信息
    military_rank = get_user_military_rank(user['id'])
    return jsonify({'user': user, 'military_rank': military_rank})

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
    # 获取用户军衔信息（新用户为初始等级）
    military_rank = get_user_military_rank(user_id)
    return jsonify({'user': user, 'military_rank': military_rank, 'message': '注册成功'})

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
    # 获取用户军衔信息
    military_rank = get_user_military_rank(user_id)
    return jsonify({'user': user, 'military_rank': military_rank, 'message': '绑定成功'})

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
    # 获取用户军衔信息
    military_rank = get_user_military_rank(int(user_id))
    return jsonify({'user': user, 'military_rank': military_rank})

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

# ===== 军功勋章 API =====

@api_bp.route('/users/<int:user_id>/merits', methods=['GET'])
def get_merits(user_id):
    """获取用户军功章统计"""
    # 先检查并颁发新军功
    new_merits = check_and_award_merits(user_id)
    merits = get_user_merits(user_id)
    return jsonify({'merits': merits, 'new_merits': new_merits})

@api_bp.route('/users/<int:user_id>/medals', methods=['GET'])
def get_medals(user_id):
    """获取用户勋章"""
    # 先检查并颁发新勋章
    new_medals = check_and_award_medals(user_id)
    medals = get_user_medals(user_id)
    return jsonify({'medals': medals, 'new_medals': new_medals})

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

@api_bp.route('/admin/books', methods=['POST'])
def admin_create_book():
    """创建新书籍（空白，仅基本信息）"""
    data = request.json
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': '书名不能为空'}), 400
    book_id = add_book(
        title=title,
        author=data.get('author', ''),
        author_nationality=data.get('author_nationality', ''),
        version=data.get('version', '')
    )
    return jsonify({'book_id': book_id, 'message': '创建成功'})

@api_bp.route('/admin/books/<int:book_id>/import-status', methods=['GET'])
def admin_get_import_status(book_id):
    """查询书籍导入状态"""
    status = _get_import_status(book_id)
    if status:
        return jsonify(status)
    return jsonify({'status': 'none', 'message': ''})

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
    cursor.execute('UPDATE books SET is_public=%s WHERE id=%s', (is_public, book_id))
    conn.commit()
    conn.close()
    return jsonify({'message': '公版设置更新成功', 'is_public': is_public})

@api_bp.route('/admin/books/<int:book_id>/fix-char-timeline', methods=['POST'])
def admin_fix_char_timeline(book_id):
    """修复书籍的 char_timeline（不重新生成音频）"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404

    from backend.fix_char_timeline import fix_book_char_timeline

    data = request.json or {}
    force = data.get('force', False)

    try:
        fix_book_char_timeline(book_id, force=force)
        return jsonify({'success': True, 'message': '修复完成'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/books/<int:book_id>/sections/<int:section_id>/fix-char-timeline', methods=['POST'])
def admin_fix_section_char_timeline(book_id, section_id):
    """修复单个节的 char_timeline（不重新生成音频）"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404

    from backend.fix_char_timeline import fix_section_char_timeline

    data = request.json or {}
    force = data.get('force', False)

    try:
        fix_section_char_timeline(section_id, force=force)
        return jsonify({'success': True, 'message': '修复完成'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/books/<int:book_id>/icon', methods=['POST'])
def admin_upload_book_icon(book_id):
    """上传书籍图标（自动压缩）"""
    book = get_book(book_id)
    if not book:
        return jsonify({'error': '书籍不存在'}), 404
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    import os
    
    # 从环境变量获取书籍图标存储路径
    # 优先使用环境变量配置，支持 Docker 挂载目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_path_env = os.environ.get('BOOK_ICONS_PATH', '')
    
    if icons_path_env and os.path.isabs(icons_path_env):
        # 使用绝对路径配置（适用于 Docker 挂载场景）
        icons_dir = icons_path_env
        # 数据库中存储相对路径，便于前端访问
        icon_path = f'book_icons/book_{book_id}.png'
    else:
        # 默认路径：frontend/book_icons
        icons_dir = os.path.join(project_root, 'frontend', 'book_icons')
        icon_path = f'book_icons/book_{book_id}.png'
    
    try:
        # 确保目录存在
        os.makedirs(icons_dir, exist_ok=True)
        
        # 检查目录是否可写
        if not os.access(icons_dir, os.W_OK):
            return jsonify({'error': f'图标目录不可写: {icons_dir}'}), 500
        
        # 构建完整的保存路径
        full_path = os.path.join(icons_dir, f'book_{book_id}.png')
        
        # 图片压缩配置
        TARGET_WIDTH = 64
        TARGET_HEIGHT = 80
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 最大5MB
        
        # 检查文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'文件大小超过限制（最大5MB）'}), 400
        
        # 使用 Pillow 处理图片（内存中直接处理，不保存原图）
        from PIL import Image
        import io
        
        # 从文件流读取图片
        img = Image.open(file.stream)
        
        # 处理透明通道
        if img.mode not in ('RGBA', 'RGB'):
            img = img.convert('RGBA')
        
        # 保持宽高比缩放
        original_width, original_height = img.size
        ratio = min(TARGET_WIDTH / original_width, TARGET_HEIGHT / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        # 高质量缩放
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 创建新画布，居中放置缩放后的图片
        if img.mode == 'RGBA':
            new_img = Image.new('RGBA', (TARGET_WIDTH, TARGET_HEIGHT), (255, 255, 255, 0))
        else:
            new_img = Image.new('RGB', (TARGET_WIDTH, TARGET_HEIGHT), (255, 255, 255))
        
        offset_x = (TARGET_WIDTH - new_width) // 2
        offset_y = (TARGET_HEIGHT - new_height) // 2
        new_img.paste(img_resized, (offset_x, offset_y))
        
        # 保存压缩后的图片
        new_img.save(full_path, 'PNG', optimize=True, quality=85)
        
        # 获取压缩前后大小信息
        compressed_size = os.path.getsize(full_path)
        print(f"[ICON UPLOAD] 图标压缩完成: {file_size} bytes -> {compressed_size} bytes ({(compressed_size/file_size*100):.1f}%)")
        
        # 更新数据库
        from backend.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE books SET icon_path=%s WHERE id=%s', (icon_path, book_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': '图标上传成功', 
            'icon_path': icon_path,
            'original_size': file_size,
            'compressed_size': compressed_size
        })
    
    except Exception as e:
        print(f"[ICON UPLOAD] 上传失败: {e}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@api_bp.route('/book_icons/<path:filename>', methods=['GET'])
def serve_book_icon(filename):
    """提供书籍图标（支持环境变量配置路径）"""
    from flask import send_from_directory
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_path_env = os.environ.get('BOOK_ICONS_PATH', '')
    
    if icons_path_env and os.path.isabs(icons_path_env):
        # 使用环境变量配置的绝对路径
        icons_dir = icons_path_env
    else:
        # 默认路径
        icons_dir = os.path.join(project_root, 'frontend', 'book_icons')
    
    # 确保目录存在
    os.makedirs(icons_dir, exist_ok=True)
    
    icon_path = os.path.join(icons_dir, filename)
    if os.path.exists(icon_path):
        return send_from_directory(icons_dir, filename)
    else:
        # 返回默认图标
        default_icons_dir = os.path.join(project_root, 'frontend', 'book_icons')
        default_icon_path = os.path.join(default_icons_dir, 'default.png')
        if os.path.exists(default_icon_path):
            return send_from_directory(default_icons_dir, 'default.png')
        return '', 404

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
        'id': q['id'], 'content': q['content'], 'author': q['author'], 'source': q['source'], 'created_at': str(q['created_at'])
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
    cursor.execute('INSERT INTO quotes (content, author, source) VALUES (%s, %s, %s)',
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
    cursor.execute('UPDATE quotes SET content=%s, author=%s, source=%s WHERE id=%s',
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
    cursor.execute('DELETE FROM quotes WHERE id=%s', (quote_id,))
    cursor.execute('DELETE FROM quote_usage WHERE quote_id=%s', (quote_id,))
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
            cursor.execute('INSERT INTO quotes (content, author, source) VALUES (%s, %s, %s)',
                           (content, q.get('author', ''), q.get('source', '')))
            count += 1
    conn.commit()
    conn.close()
    return jsonify({'message': f'成功导入 {count} 条名言', 'count': count})

@api_bp.route('/quote/random', methods=['GET'])
def get_random_quote():
    """获取随机名言（用于阅读页面）"""
    try:
        book_id = request.args.get('book_id', type=int)
        section_id = request.args.get('section_id', type=int)
        user_id = request.args.get('user_id', type=int)
        
        from backend.database import get_db
        conn = get_db()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute('SELECT COUNT(*) as total FROM quotes')
        result = cursor.fetchone()
        total = result['total'] if result else 0
        if total == 0:
            conn.close()
            return jsonify({'quotes': []})
        
        count = min(2, total)
        if book_id and user_id:
            cursor.execute('''
                SELECT id, content, author, source FROM quotes 
                WHERE id NOT IN (
                    SELECT quote_id FROM quote_usage 
                    WHERE book_id=%s AND user_id=%s
                )
                ORDER BY RAND() LIMIT %s
            ''', (book_id, user_id, count))
            rows = cursor.fetchall()
            if len(rows) < count:
                cursor.execute('SELECT id, content, author, source FROM quotes ORDER BY RAND() LIMIT %s', (count,))
                rows = cursor.fetchall()
        else:
            cursor.execute('SELECT id, content, author, source FROM quotes ORDER BY RAND() LIMIT %s', (count,))
            rows = cursor.fetchall()

        results = []
        for row in rows:
            quote_id = row['id']
            content = row['content']
            author = row.get('author', '')
            source = row.get('source', '')
            results.append({'id': quote_id, 'content': content, 'author': author, 'source': source})
            if book_id and section_id and user_id:
                try:
                    cursor.execute('''
                        INSERT INTO quote_usage (quote_id, book_id, section_id, user_id)
                        VALUES (%s, %s, %s, %s)
                    ''', (quote_id, book_id, section_id, user_id))
                except Exception as insert_err:
                    print(f'[WARN] quote_usage insert skipped: {insert_err}')
        
        if book_id and section_id and user_id:
            conn.commit()
        conn.close()
        return jsonify({'quotes': results})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f'[ERROR] get_random_quote: {e}')
        print(error_detail)
        return jsonify({'error': str(e), 'detail': error_detail}), 500

@api_bp.route('/health/db', methods=['GET'])
def health_db():
    """数据库健康检查"""
    try:
        from backend.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查 quotes 表
        cursor.execute("SELECT COUNT(*) FROM quotes")
        quotes_count = cursor.fetchone()[0]
        
        # 检查 quote_usage 表
        cursor.execute("SELECT COUNT(*) FROM quote_usage")
        usage_count = cursor.fetchone()[0]
        
        conn.close()
        return jsonify({
            'status': 'ok',
            'quotes_count': quotes_count,
            'quote_usage_count': usage_count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ===== 微信公众号菜单管理 =====

@api_bp.route('/admin/wechat/create-menu', methods=['POST'])
def admin_create_wechat_menu():
    """创建微信公众号自定义菜单"""
    import requests as req
    appid = request.json.get('appid', WECHAT_APPID) if request.is_json else WECHAT_APPID
    appsecret = request.json.get('appsecret', WECHAT_APPSECRET) if request.is_json else WECHAT_APPSECRET
    
    if not appsecret:
        return jsonify({'error': '请提供AppSecret'}), 400
    
    # 1. 获取access_token
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={appsecret}"
    try:
        token_resp = req.get(token_url, timeout=10)
        token_data = token_resp.json()
        if 'access_token' not in token_data:
            return jsonify({'error': f'获取token失败: {token_data.get("errmsg", "未知错误")}'})
        access_token = token_data['access_token']
    except Exception as e:
        return jsonify({'error': f'获取token异常: {str(e)}'}), 500
    
    # 2. 删除旧菜单
    try:
        req.get(f"https://api.weixin.qq.com/cgi-bin/menu/delete?access_token={access_token}", timeout=10)
    except:
        pass
    
    # 3. 创建新菜单
    menu_config = {
        "button": [
            {
                "type": "click",
                "name": "开始阅读",
                "key": "start_reading"
            },
            {
                "type": "click",
                "name": "使用帮助",
                "key": "help"
            }
        ]
    }
    
    menu_url = f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}"
    try:
        menu_resp = req.post(menu_url, json=menu_config, headers={'Content-Type': 'application/json'}, timeout=10)
        menu_data = menu_resp.json()
        if menu_data.get('errcode') == 0:
            return jsonify({'message': '菜单创建成功', 'menu': menu_config})
        else:
            return jsonify({'error': f'菜单创建失败: {menu_data.get("errmsg", "未知错误")}'}), 500
    except Exception as e:
        return jsonify({'error': f'菜单创建异常: {str(e)}'}), 500

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
                import tempfile
                import os
                from docx import Document
                # 将上传文件保存到临时文件（SpooledTemporaryFile不支持seekable）
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                    file.save(tmp.name)
                    tmp_path = tmp.name
                try:
                    doc = Document(tmp_path)
                    paragraphs = []
                    for para in doc.paragraphs:
                        if para.text.strip():
                            paragraphs.append(para.text.strip())
                    text = '\n'.join(paragraphs)
                finally:
                    os.unlink(tmp_path)
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
        cursor.execute('SELECT id, section_number FROM sections WHERE chapter_id=%s', (chapter_id,))
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
                cursor.execute('DELETE FROM annotations WHERE section_id = %s', (sec_id,))
                # 删除旧的 text_segments 和 insert_points（级联删除）
                cursor.execute('DELETE FROM text_segments WHERE section_id = %s', (sec_id,))
                cursor.execute('DELETE FROM insert_points WHERE section_id = %s', (sec_id,))
                # 清除音频相关字段
                cursor.execute('UPDATE sections SET audio_path = NULL, audio_duration = NULL, char_timeline = NULL, summary_audio_path = NULL WHERE id = %s', (sec_id,))
                # 更新小节内容
                cursor.execute('UPDATE sections SET title = %s, content = %s, summary = %s, word_count = %s WHERE id = %s',
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
                    cursor.execute('UPDATE sections SET summary = %s WHERE id = %s', (summary, sec_id))
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
                           VALUES (%s, %s, %s, %s, %s, %s)''',
                        (sec_id, idx + 1, anno.get('start_char', 0), anno.get('end_char', 0),
                         anno.get('original_text', ''), anno.get('comment', ''))
                    )
                conn.commit()
                conn.close()

        # 更新章节统计
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt, COALESCE(SUM(word_count), 0) as total_words FROM sections WHERE chapter_id=%s', (chapter_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            update_chapter_info(chapter_id, row['cnt'], row['total_words'])

        # 更新书籍总小节数
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM sections WHERE book_id=%s', (book_id,))
        row = cursor.fetchone()
        conn.close()
        total_sections = row['cnt'] if row else 0
        update_book_sections_count(book_id, total_sections)

        # 为更新的节重新创建分段数据并生成分段TTS音频（使用统一核心函数）
        failed_sections = []
        for sec in matched_sections:
            sec_number = sec['section_number']
            if sec_number in existing_sections:
                sec_id = existing_sections[sec_number]
                result = reimport_section_core(
                    section_id=sec_id,
                    content=sec.get('content', ''),
                    annotations=sec.get('annotations', []),
                    title=sec.get('title', ''),
                    summary=sec.get('summary', '')
                )
                if not result['success']:
                    failed_sections.append(sec_id)
                    print(f"[reimport_chapter] 节 {sec_id} 处理失败: {result['error']}")

        section_ids = [existing_sections[s['section_number']] for s in matched_sections if s['section_number'] in existing_sections]
        return jsonify({
            'message': '章节导入成功' + ('（部分音频生成失败）' if failed_sections else ''),
            'section_count': len(matched_sections),
            'section_ids': section_ids,
            'failed_sections': failed_sections
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

        # 删除旧数据并更新内容（同一事务）
        from backend.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM annotations WHERE section_id = %s', (section_id,))
        # 删除旧的 text_segments 和 insert_points
        cursor.execute('DELETE FROM text_segments WHERE section_id = %s', (section_id,))
        cursor.execute('DELETE FROM insert_points WHERE section_id = %s', (section_id,))
        # 清除音频相关字段
        cursor.execute('UPDATE sections SET audio_path = NULL, audio_duration = NULL, char_timeline = NULL, summary_audio_path = NULL WHERE id = %s', (section_id,))
        cursor.execute('UPDATE sections SET title = %s, content = %s, summary = %s, word_count = %s WHERE id = %s',
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
                       VALUES (%s, %s, %s, %s, %s, %s)''',
                    (section_id, idx + 1, anno.get('start_char', 0), anno.get('end_char', 0),
                     anno.get('original_text', ''), anno.get('comment', ''))
                )
            conn.commit()
            conn.close()

        # 更新章节统计
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt, COALESCE(SUM(word_count), 0) as total_words FROM sections WHERE chapter_id=%s', (chapter_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            update_chapter_info(chapter_id, row['cnt'], row['total_words'])

        # 更新书籍总小节数
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM sections WHERE book_id=%s', (book_id,))
        row = cursor.fetchone()
        conn.close()
        total_sections = row['cnt'] if row else 0
        update_book_sections_count(book_id, total_sections)

        # 为更新的节重新创建分段数据并生成分段TTS音频（使用统一核心函数）
        result = reimport_section_core(
            section_id=section_id,
            content=content,
            annotations=matched_section.get('annotations', []),
            title=title,
            summary=summary
        )
        audio_success = result['success']
        if not audio_success:
            print(f"[reimport_section] 节 {section_id} 处理失败: {result['error']}")

        return jsonify({
            'message': '小节导入成功' + ('' if audio_success else '（音频生成失败）'),
            'section_ids': [section_id],
            'audio_success': audio_success
        })

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
    
    # 获取完整上下文信息用于 AI 评分
    section = get_section(section_id)
    book_name = ''
    author = ''
    chapter_title = ''
    section_title = ''
    section_content = ''
    if section:
        section_content = section.get('content', '')
        section_title = section.get('title', '')
        # 获取书籍信息
        book_id = section.get('book_id')
        if book_id:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT title, author FROM books WHERE id = %s', (book_id,))
            book_row = cursor.fetchone()
            conn.close()
            if book_row:
                book_name = book_row['title'] or ''
                author = book_row['author'] or ''
        # 获取章节标题
        if section.get('chapter_id'):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT title FROM chapters WHERE id = %s', (section['chapter_id'],))
            ch_row = cursor.fetchone()
            conn.close()
            if ch_row:
                chapter_title = ch_row['title'] or ''
    
    # AI 评分（传入完整上下文）
    ai_score, score_reason = rate_thought(
        original_text, thought_content, section_content,
        book_name=book_name, author=author,
        chapter_title=chapter_title, section_title=section_title
    )
    print(f"[思考评分] 用户 {user_id} 的思考评分: {ai_score} - {score_reason}")
    
    thought_id = add_thought(
        user_id=int(user_id),
        section_id=section_id,
        start_char=data.get('start_char', 0),
        end_char=data.get('end_char', 0),
        original_text=original_text,
        content=thought_content,
        ai_score=ai_score,
        score_reason=score_reason
    )
    # 检查军功和勋章
    new_merits = check_and_award_merits(int(user_id))
    new_medals = check_and_award_medals(int(user_id))
    return jsonify({
        'thought_id': thought_id,
        'ai_score': ai_score,
        'score_reason': score_reason,
        'message': '思考已保存',
        'new_merits': new_merits,
        'new_medals': new_medals,
    })

@api_bp.route('/sections/<int:section_id>/thoughts/repair', methods=['POST'])
def repair_unscored_thoughts(section_id):
    """修复未评分的思考（异步，用户进入节时调用）"""
    data = request.json or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    
    # 获取未评分的思考
    from backend.database import get_unscored_thoughts_by_section, update_thought_ai_score, get_thought_by_id
    from backend.ai_score import rate_thought
    
    unscored = get_unscored_thoughts_by_section(section_id, int(user_id))
    if not unscored:
        return jsonify({'repaired': 0, 'message': '无待修复思考'})
    
    # 获取上下文信息
    section = get_section(section_id)
    book_name = ''
    author = ''
    chapter_title = ''
    section_title = ''
    section_content = ''
    if section:
        section_content = section.get('content', '')
        section_title = section.get('title', '')
        book_id = section.get('book_id')
        if book_id:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT title, author FROM books WHERE id = %s', (book_id,))
            book_row = cursor.fetchone()
            conn.close()
            if book_row:
                book_name = book_row['title'] or ''
                author = book_row['author'] or ''
        if section.get('chapter_id'):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT title FROM chapters WHERE id = %s', (section['chapter_id'],))
            ch_row = cursor.fetchone()
            conn.close()
            if ch_row:
                chapter_title = ch_row['title'] or ''
    
    # 异步修复（这里用同步，因为请求数量通常很少）
    repaired_count = 0
    for thought in unscored:
        try:
            ai_score, score_reason = rate_thought(
                thought['original_text'], thought['content'], section_content,
                book_name=book_name, author=author,
                chapter_title=chapter_title, section_title=section_title
            )
            update_thought_ai_score(thought['id'], ai_score, score_reason)
            repaired_count += 1
            print(f"[修复思考] thought_id={thought['id']}, score={ai_score}, reason={score_reason}")
        except Exception as e:
            print(f"[修复思考] thought_id={thought['id']} 失败: {e}")
    
    return jsonify({'repaired': repaired_count, 'message': f'已修复{repaired_count}条思考'})

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
