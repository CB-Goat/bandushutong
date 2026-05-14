"""
伴读书童 - API 路由
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
    create_user, verify_user, get_user, get_user_by_phone, get_all_users, update_user_role, delete_user, generate_auth_code,
    # 订阅系统
    subscribe_book, get_user_subscriptions, check_book_access, get_subscription_requests, add_subscription_request, approve_subscription_request, reject_subscription_request,
    # 思考系统
    add_thought, get_thoughts_by_section, get_all_thoughts_by_section, delete_thought, update_thought,
    # 书籍查找
    get_book_by_title_author_version
)
from backend.text_parser import parse_file, get_book_title
from backend.tts_service import generate_audio

api_bp = Blueprint('api', __name__)

# 文件上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'books')
os.makedirs(UPLOAD_DIR, exist_ok=True)

@api_bp.route('/init', methods=['POST'])
def init_database():
    """初始化数据库"""
    init_db()
    return jsonify({'message': '数据库初始化成功'})

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
    
    # 获取每个小节的点评点
    for sec in sections:
        sec['annotations'] = get_annotations_by_section(sec['id'])
    
    return jsonify({
        'book': book,
        'sections': sections,
        'progress': progress
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
    """获取节的音频时间轴信息"""
    from backend.database import get_section_audio_timeline
    timeline = get_section_audio_timeline(section_id)
    if timeline:
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
    
    if not book_id or not section_id:
        return jsonify({'error': '缺少必要参数'}), 400
    
    update_progress(user_id, book_id, section_id, position)
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
    return jsonify({'message': '状态更新成功'})

@api_bp.route('/books/<int:book_id>/reading-status', methods=['GET'])
def get_reading_status(book_id):
    """获取书籍所有节的阅读状态"""
    user_id = request.args.get('user_id', type=int)
    statuses = get_all_section_status(user_id, book_id)
    stats = get_book_reading_stats(user_id, book_id)
    return jsonify({'statuses': statuses, 'stats': stats})

# ===== 用户 API =====

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    phone = data.get('phone', '').strip()
    auth_code = data.get('auth_code', '').strip()
    if not phone or not auth_code:
        return jsonify({'error': '请输入手机号和授权码'}), 400
    user = verify_user(phone, auth_code)
    if not user:
        return jsonify({'error': '手机号或授权码错误'}), 401
    # 不返回auth_code
    user.pop('auth_code', None)
    return jsonify({'user': user})

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """用户注册（需要授权码）"""
    data = request.json
    phone = data.get('phone', '').strip()
    auth_code = data.get('auth_code', '').strip()
    if not phone or not auth_code:
        return jsonify({'error': '请输入手机号和授权码'}), 400
    existing = get_user_by_phone(phone)
    if existing:
        return jsonify({'error': '该手机号已注册'}), 400
    user_id = create_user(phone, auth_code, 'user')
    user = get_user(user_id)
    user.pop('auth_code', None)
    return jsonify({'user': user, 'message': '注册成功'})

@api_bp.route('/auth/check', methods=['GET'])
def check_auth():
    """检查登录状态"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    user = get_user(int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 401
    user.pop('auth_code', None)
    return jsonify({'user': user})

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
    """获取所有用户"""
    users = get_all_users()
    for u in users:
        u.pop('auth_code', None)
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

@api_bp.route('/admin/users/<int:user_id>/auth-code', methods=['POST'])
def admin_reset_auth_code(user_id):
    """重置用户授权码"""
    from backend.database import get_db
    new_code = generate_auth_code()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET auth_code = ? WHERE id = ?', (new_code, user_id))
    conn.commit()
    conn.close()
    return jsonify({'auth_code': new_code})

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
    """获取节的思考"""
    user_id = request.args.get('user_id')
    user = get_user(int(user_id)) if user_id else None
    if user and user['role'] == 'admin':
        thoughts = get_all_thoughts_by_section(section_id)
    elif user_id:
        thoughts = get_thoughts_by_section(section_id, int(user_id))
    else:
        thoughts = []
    return jsonify({'thoughts': thoughts})

@api_bp.route('/sections/<int:section_id>/thoughts', methods=['POST'])
def create_thought(section_id):
    """创建思考"""
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': '未登录'}), 401
    thought_id = add_thought(
        user_id=int(user_id),
        section_id=section_id,
        start_char=data.get('start_char', 0),
        end_char=data.get('end_char', 0),
        original_text=data.get('original_text', ''),
        content=data.get('content', '')
    )
    return jsonify({'thought_id': thought_id, 'message': '思考已保存'})

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
