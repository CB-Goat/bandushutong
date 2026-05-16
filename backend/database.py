# -*- coding: utf-8 -*-
"""
伴读书童 - 数据库模块
使用 SQLite 快速开发
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'reading_companion.db')

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 书籍表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            author_nationality TEXT,
            version TEXT,
            file_path TEXT,
            total_sections INTEGER DEFAULT 0,
            total_chapters INTEGER DEFAULT 0,
            tts_status TEXT DEFAULT 'none',  -- none/pending/generating/done/error
            tts_progress TEXT DEFAULT '',     -- 如 "5/30"
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 章节表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chapter_number INTEGER NOT NULL,
            title TEXT,
            section_count INTEGER DEFAULT 0,
            total_words INTEGER DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # 小节表（阅读的最小单位）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chapter_id INTEGER,
            section_number INTEGER NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            audio_path TEXT,
            has_audio BOOLEAN DEFAULT 0,
            audio_duration REAL DEFAULT 0,  -- 音频时长（秒）
            char_timeline TEXT,  -- 每个字符显示时间点的JSON数组
            word_count INTEGER DEFAULT 0,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (chapter_id) REFERENCES chapters(id)
        )
    ''')

    # 阅读进度表（按用户隔离）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_id INTEGER NOT NULL,
            current_section_id INTEGER,
            current_position INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (current_section_id) REFERENCES sections(id)
        )
    ''')

    # 点评点表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            annotation_index INTEGER NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            original_text TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections(id)
        )
    ''')

    # 节阅读状态表（按用户隔离）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS section_reading_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            status TEXT DEFAULT 'unread',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (section_id) REFERENCES sections(id),
            UNIQUE(user_id, book_id, section_id)
        )
    ''')

    # 添加点评音频字段（如果不存在）
    try:
        cursor.execute('ALTER TABLE annotations ADD COLUMN audio_path TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE annotations ADD COLUMN audio_duration REAL DEFAULT 0')
    except:
        pass

    # 添加 user_id 字段到 reading_progress（如果不存在）
    try:
        cursor.execute('ALTER TABLE reading_progress ADD COLUMN user_id INTEGER')
    except:
        pass

    # 添加 user_id 字段到 section_reading_status（如果不存在）
    try:
        cursor.execute('ALTER TABLE section_reading_status ADD COLUMN user_id INTEGER')
    except:
        pass

    # 添加小结音频字段（如果不存在）
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN summary_audio_path TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN summary_audio_duration REAL DEFAULT 0')
    except:
        pass

    # 添加分段音频信息字段（如果不存在）
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN audio_segments TEXT')
    except:
        pass

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL UNIQUE,
            auth_code TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 订阅表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES books(id),
            UNIQUE(user_id, book_id)
        )
    ''')

    # 订阅申请表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscription_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # 思考表（用户个人点评）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            original_text TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (section_id) REFERENCES sections(id)
        )
    ''')

    # 为已有表添加新字段
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN author_nationality TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN version TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN total_chapters INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE chapters ADD COLUMN section_count INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE chapters ADD COLUMN total_words INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN title TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN word_count INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN summary TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN audio_duration REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE sections ADD COLUMN char_timeline TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN tts_status TEXT DEFAULT "none"')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN tts_progress TEXT DEFAULT ""')
    except:
        pass

    conn.commit()
    conn.close()
    print("数据库初始化完成")

# ===== 用户系统 =====

def create_user(phone, auth_code, role='user'):
    """创建用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (phone, auth_code, role) VALUES (?, ?, ?)',
        (phone, auth_code, role)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def get_user_by_phone(phone):
    """通过手机号获取用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user(user_id):
    """获取用户信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    """获取所有用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def update_user_role(user_id, role):
    """更新用户角色"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """删除用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def verify_user(phone, auth_code):
    """验证用户登录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = ? AND auth_code = ?', (phone, auth_code))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def generate_auth_code():
    """生成6位随机授权码"""
    import random, string
    return ''.join(random.choices(string.digits, k=6))

# ===== 订阅系统 =====

def subscribe_book(user_id, book_id):
    """用户订阅书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO subscriptions (user_id, book_id) VALUES (?, ?)',
        (user_id, book_id)
    )
    conn.commit()
    conn.close()

def unsubscribe_book(user_id, book_id):
    """取消订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscriptions WHERE user_id = ? AND book_id = ?', (user_id, book_id))
    conn.commit()
    conn.close()

def get_user_subscriptions(user_id):
    """获取用户的所有订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT book_id FROM subscriptions WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [r['book_id'] for r in rows]

def check_book_access(user_id, book_id, user_role):
    """检查用户对某本书的访问权限"""
    if user_role == 'admin':
        return {'has_access': True, 'access_type': 'full'}
    sub = get_user_subscriptions(user_id)
    if book_id in sub:
        return {'has_access': True, 'access_type': 'full'}
    return {'has_access': True, 'access_type': 'free', 'free_sections': 3}

def get_subscription_requests():
    """获取所有订阅申请"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM subscription_requests ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_subscription_request(user_id, book_id):
    """添加订阅申请"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO subscription_requests (user_id, book_id) VALUES (?, ?)',
        (user_id, book_id)
    )
    conn.commit()
    conn.close()

def approve_subscription_request(request_id):
    """审批订阅申请"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM subscription_requests WHERE id = ?', (request_id,))
    req = cursor.fetchone()
    if req:
        cursor.execute(
            'INSERT OR IGNORE INTO subscriptions (user_id, book_id) VALUES (?, ?)',
            (req['user_id'], req['book_id'])
        )
        cursor.execute('DELETE FROM subscription_requests WHERE id = ?', (request_id,))
    conn.commit()
    conn.close()

def reject_subscription_request(request_id):
    """拒绝订阅申请"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscription_requests WHERE id = ?', (request_id,))
    conn.commit()
    conn.close()

# ===== 思考（用户个人点评）=====

def add_thought(user_id, section_id, start_char, end_char, original_text, content):
    """添加思考"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO thoughts (user_id, section_id, start_char, end_char, original_text, content) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, section_id, start_char, end_char, original_text, content)
    )
    thought_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return thought_id

def get_thoughts_by_section(section_id, user_id=None):
    """获取某节的思考（可按用户过滤）"""
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute('SELECT * FROM thoughts WHERE section_id = ? AND user_id = ? ORDER BY start_char', (section_id, user_id))
    else:
        cursor.execute('SELECT * FROM thoughts WHERE section_id = ? ORDER BY start_char', (section_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_thoughts_by_section(section_id):
    """获取某节所有用户的思考（系统用户用）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT t.*, u.phone FROM thoughts t 
           LEFT JOIN users u ON t.user_id = u.id 
           WHERE t.section_id = ? ORDER BY t.start_char''', (section_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_thought(thought_id, user_id):
    """删除思考"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM thoughts WHERE id = ? AND user_id = ?', (thought_id, user_id))
    conn.commit()
    conn.close()

def update_thought(thought_id, user_id, content):
    """更新思考内容"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE thoughts SET content = ? WHERE id = ? AND user_id = ?', (content, thought_id, user_id))
    conn.commit()
    conn.close()

# ==================== 书籍相关操作 ====================

def add_book(title, author=None, file_path=None):
    """添加书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO books (title, author, file_path) VALUES (?, ?, ?)',
        (title, author, file_path)
    )
    book_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return book_id

def get_book(book_id):
    """获取书籍信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    conn.close()
    return dict(book) if book else None

def get_all_books():
    """获取所有书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books ORDER BY created_at DESC')
    books = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return books

def update_book(book_id, title, author, author_nationality, version):
    """更新书籍信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE books SET title = ?, author = ?, author_nationality = ?, version = ? WHERE id = ?',
        (title, author, author_nationality, version, book_id)
    )
    conn.commit()
    conn.close()

def get_book_by_title_author_version(title, author, version):
    """根据书名+作者+版本查找书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM books WHERE title = ? AND author = ? AND version = ?',
        (title, author, version)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_book(book_id):
    """删除书籍（同时删除关联的章、节、点评、进度等）"""
    conn = get_db()
    cursor = conn.cursor()
    # 删除关联的点评
    cursor.execute('''
        DELETE FROM annotations WHERE section_id IN
        (SELECT id FROM sections WHERE book_id = ?)
    ''', (book_id,))
    # 删除关联的节阅读状态
    cursor.execute('DELETE FROM section_reading_status WHERE book_id = ?', (book_id,))
    # 删除关联的小节
    cursor.execute('DELETE FROM sections WHERE book_id = ?', (book_id,))
    # 删除关联的章节
    cursor.execute('DELETE FROM chapters WHERE book_id = ?', (book_id,))
    # 删除关联的阅读进度
    cursor.execute('DELETE FROM reading_progress WHERE book_id = ?', (book_id,))
    # 删除书籍
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()

def update_book_chapters_count(book_id, count):
    """更新书籍章数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE books SET total_chapters = ? WHERE id = ?', (count, book_id))
    conn.commit()
    conn.close()

def update_book_sections_count(book_id, count):
    """更新书籍的小节数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE books SET total_sections = ? WHERE id = ?', (count, book_id))
    conn.commit()
    conn.close()

# ==================== 章节相关操作 ====================

def add_chapter(book_id, chapter_number, title):
    """添加章节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO chapters (book_id, chapter_number, title) VALUES (?, ?, ?)',
        (book_id, chapter_number, title)
    )
    chapter_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chapter_id

def get_chapters_by_book(book_id):
    """获取书籍的所有章节（按chapter_number排序）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM chapters WHERE book_id = ? ORDER BY chapter_number',
        (book_id,)
    )
    chapters = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return chapters

def get_chapter(chapter_id):
    """获取单个章节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chapters WHERE id = ?', (chapter_id,))
    chapter = cursor.fetchone()
    conn.close()
    return dict(chapter) if chapter else None

def update_chapter(chapter_id, title):
    """更新章节标题"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE chapters SET title = ? WHERE id = ?',
        (title, chapter_id)
    )
    conn.commit()
    conn.close()

def delete_chapter(chapter_id):
    """删除章节（同时删除关联的节和点评）"""
    conn = get_db()
    cursor = conn.cursor()
    # 删除关联的点评
    cursor.execute('''
        DELETE FROM annotations WHERE section_id IN
        (SELECT id FROM sections WHERE chapter_id = ?)
    ''', (chapter_id,))
    # 删除关联的节阅读状态
    cursor.execute('''
        DELETE FROM section_reading_status WHERE section_id IN
        (SELECT id FROM sections WHERE chapter_id = ?)
    ''', (chapter_id,))
    # 删除关联的小节
    cursor.execute('DELETE FROM sections WHERE chapter_id = ?', (chapter_id,))
    # 删除章节
    cursor.execute('DELETE FROM chapters WHERE id = ?', (chapter_id,))
    conn.commit()
    conn.close()

def update_chapter_info(chapter_id, section_count, total_words):
    """更新章节统计信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE chapters SET section_count = ?, total_words = ? WHERE id = ?',
        (section_count, total_words, chapter_id)
    )
    conn.commit()
    conn.close()

# ==================== 小节相关操作 ====================

def add_section(book_id, chapter_id, section_number, content, title=''):
    """添加小节"""
    conn = get_db()
    cursor = conn.cursor()
    word_count = len(content) if content else 0
    cursor.execute(
        'INSERT INTO sections (book_id, chapter_id, section_number, content, title, word_count) VALUES (?, ?, ?, ?, ?, ?)',
        (book_id, chapter_id, section_number, content, title, word_count)
    )
    section_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return section_id

def get_sections_by_book(book_id):
    """获取书籍的所有小节，包含章节编号和标题"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, c.chapter_number, c.title as chapter_title 
        FROM sections s 
        LEFT JOIN chapters c ON s.chapter_id = c.id 
        WHERE s.book_id = ? 
        ORDER BY s.section_number
    ''', (book_id,))
    sections = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sections

def get_sections_by_chapter(chapter_id):
    """获取章节的所有小节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM sections WHERE chapter_id = ? ORDER BY section_number',
        (chapter_id,)
    )
    sections = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sections

def get_section(section_id):
    """获取单个小节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sections WHERE id = ?', (section_id,))
    section = cursor.fetchone()
    conn.close()
    return dict(section) if section else None

def update_section(section_id, title, content, summary):
    """更新小节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET title = ?, content = ?, summary = ? WHERE id = ?',
        (title, content, summary, section_id)
    )
    conn.commit()
    conn.close()

def delete_section(section_id):
    """删除小节（同时删除关联的点评）"""
    conn = get_db()
    cursor = conn.cursor()
    # 删除关联的点评
    cursor.execute('DELETE FROM annotations WHERE section_id = ?', (section_id,))
    # 删除关联的节阅读状态
    cursor.execute('DELETE FROM section_reading_status WHERE section_id = ?', (section_id,))
    # 删除小节
    cursor.execute('DELETE FROM sections WHERE id = ?', (section_id,))
    conn.commit()
    conn.close()

def update_section_audio(section_id, audio_path):
    """更新小节的音频路径"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET audio_path = ?, has_audio = 1 WHERE id = ?',
        (audio_path, section_id)
    )
    conn.commit()
    conn.close()

def update_section_audio_timeline(section_id, audio_duration, char_timeline, audio_path=None):
    """更新小节的音频时长和字符时间轴"""
    conn = get_db()
    cursor = conn.cursor()
    import json
    if audio_path:
        cursor.execute(
            'UPDATE sections SET audio_path = ?, has_audio = 1, audio_duration = ?, char_timeline = ? WHERE id = ?',
            (audio_path, audio_duration, json.dumps(char_timeline), section_id)
        )
    else:
        cursor.execute(
            'UPDATE sections SET audio_duration = ?, char_timeline = ? WHERE id = ?',
            (audio_duration, json.dumps(char_timeline), section_id)
        )
    conn.commit()
    conn.close()

def get_section_audio_timeline(section_id):
    """获取小节的音频时间轴信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT audio_path, audio_duration, char_timeline FROM sections WHERE id = ?',
        (section_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        import json
        return {
            'audio_path': row['audio_path'],
            'audio_duration': row['audio_duration'],
            'char_timeline': json.loads(row['char_timeline']) if row['char_timeline'] else []
        }
    return None

def update_section_audio_segments(section_id, audio_segments):
    """更新小节的分段音频信息"""
    import json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET audio_segments = ? WHERE id = ?',
        (json.dumps(audio_segments), section_id)
    )
    conn.commit()
    conn.close()

def get_section_audio_segments(section_id):
    """获取小节的分段音频信息"""
    import json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT audio_segments FROM sections WHERE id = ?',
        (section_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row and row['audio_segments']:
        return json.loads(row['audio_segments'])
    return None

def update_book_tts_status(book_id, status, progress=''):
    """更新书籍的TTS生成状态"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE books SET tts_status = ?, tts_progress = ? WHERE id = ?',
        (status, progress, book_id)
    )
    conn.commit()
    conn.close()

def update_annotation_audio(annotation_id, audio_path, audio_duration):
    """更新点评的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE annotations SET audio_path = ?, audio_duration = ? WHERE id = ?',
        (audio_path, audio_duration, annotation_id)
    )
    conn.commit()
    conn.close()

def update_section_summary_audio(section_id, audio_path, audio_duration):
    """更新小节小结的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET summary_audio_path = ?, summary_audio_duration = ? WHERE id = ?',
        (audio_path, audio_duration, section_id)
    )
    conn.commit()
    conn.close()

def update_section_word_count(section_id, word_count):
    """更新小节字数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET word_count = ? WHERE id = ?',
        (word_count, section_id)
    )
    conn.commit()
    conn.close()

# ==================== 阅读进度相关操作 ====================

def update_progress(user_id, book_id, section_id, position=0):
    """更新阅读进度（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT OR REPLACE INTO reading_progress
           (user_id, book_id, current_section_id, current_position, updated_at)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, book_id, section_id, position, datetime.now())
    )
    conn.commit()
    conn.close()

def get_progress(user_id, book_id):
    """获取阅读进度（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM reading_progress WHERE user_id = ? AND book_id = ? ORDER BY updated_at DESC LIMIT 1',
        (user_id, book_id)
    )
    progress = cursor.fetchone()
    conn.close()
    return dict(progress) if progress else None

# ==================== 点评点相关操作 ====================

def add_annotation(section_id, annotation_index, start_char, end_char, original_text, comment):
    """添加点评点"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO annotations (section_id, annotation_index, start_char, end_char, original_text, comment)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (section_id, annotation_index, start_char, end_char, original_text, comment)
    )
    annotation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return annotation_id

def get_annotations_by_section(section_id):
    """获取小节的所有点评点，按位置排序"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM annotations WHERE section_id = ? ORDER BY start_char',
        (section_id,)
    )
    annotations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return annotations

def delete_annotation(annotation_id):
    """删除点评点"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM annotations WHERE id = ?', (annotation_id,))
    conn.commit()
    conn.close()

# ==================== 节阅读状态相关操作 ====================

def set_section_status(user_id, book_id, section_id, status):
    """设置节阅读状态（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT OR REPLACE INTO section_reading_status
           (user_id, book_id, section_id, status, updated_at)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, book_id, section_id, status, datetime.now())
    )
    conn.commit()
    conn.close()

def get_section_status(user_id, book_id, section_id):
    """获取节阅读状态（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM section_reading_status WHERE user_id = ? AND book_id = ? AND section_id = ?',
        (user_id, book_id, section_id)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_section_status(user_id, book_id):
    """获取一本书所有节的阅读状态（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM section_reading_status WHERE user_id = ? AND book_id = ?',
        (user_id, book_id)
    )
    statuses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return statuses

def get_book_reading_stats(user_id, book_id):
    """获取一本书的阅读统计（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    # 获取总节数
    cursor.execute('SELECT COUNT(*) as total FROM sections WHERE book_id = ?', (book_id,))
    total = cursor.fetchone()['total']
    # 获取各状态数量
    cursor.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN status = 'unread' THEN 1 ELSE 0 END), 0) as unread,
            COALESCE(SUM(CASE WHEN status = 'reading' THEN 1 ELSE 0 END), 0) as reading,
            COALESCE(SUM(CASE WHEN status = 'read' THEN 1 ELSE 0 END), 0) as read_count
        FROM section_reading_status WHERE user_id = ? AND book_id = ?
    ''', (user_id, book_id))
    row = cursor.fetchone()
    conn.close()
    return {
        'total_sections': total,
        'unread': row['unread'],
        'reading': row['reading'],
        'read': row['read_count']
    }

if __name__ == '__main__':
    init_db()
