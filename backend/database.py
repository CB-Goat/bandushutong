# -*- coding: utf-8 -*-
"""
悦读小将 - 数据库模块
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

    # 添加 audio_position 字段到 reading_progress（如果不存在）
    try:
        cursor.execute('ALTER TABLE reading_progress ADD COLUMN audio_position REAL DEFAULT 0')
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
            phone TEXT UNIQUE,
            password TEXT,
            wechat_openid TEXT UNIQUE,
            wechat_nickname TEXT,
            wechat_avatar TEXT,
            device_id TEXT,
            device_info TEXT,
            gender TEXT,
            age INTEGER,
            grade TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 用户留言表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            admin_reply TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            replied_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 换机校验码表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_transfer_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transfer_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
            ai_score INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (section_id) REFERENCES sections(id)
        )
    ''')

    # 名言表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            author TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 名言使用记录表（记录某节已用过哪些名言）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quote_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quote_id) REFERENCES quotes(id),
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (section_id) REFERENCES sections(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
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
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN subscription_price REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN is_public INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE books ADD COLUMN icon_path TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE thoughts ADD COLUMN ai_score INTEGER DEFAULT NULL')
    except:
        pass

    # ===== 新架构：text_segments 和 insert_points 表 =====
    
    # 文本段表：一节文字按点评边界切割成 n+1 段
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS text_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            segment_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            word_count INTEGER DEFAULT 0,
            audio_path TEXT,
            audio_duration REAL DEFAULT 0,
            char_timeline TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
            UNIQUE(section_id, segment_number)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_text_segments_section ON text_segments(section_id)')

    # 插入点表：点评/小结绑定到对应段
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insert_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            point_order INTEGER NOT NULL,
            point_type TEXT NOT NULL,
            annotation_id INTEGER,
            annotation_index INTEGER,
            quote_text TEXT,
            quote_start_char INTEGER,
            quote_end_char INTEGER,
            comment TEXT NOT NULL,
            audio_path TEXT,
            audio_duration REAL DEFAULT 0,
            char_timeline TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES text_segments(id) ON DELETE CASCADE,
            FOREIGN KEY (annotation_id) REFERENCES annotations(id) ON DELETE SET NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_insert_points_section ON insert_points(section_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_insert_points_segment ON insert_points(segment_id)')

    # reading_progress 新增 current_segment_id 字段
    try:
        cursor.execute('ALTER TABLE reading_progress ADD COLUMN current_segment_id INTEGER')
    except:
        pass
    
    # insert_points 新增引用音频字段（独立音频文件，不从主线截取）
    try:
        cursor.execute('ALTER TABLE insert_points ADD COLUMN quote_audio_path TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE insert_points ADD COLUMN quote_audio_duration REAL DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE insert_points ADD COLUMN annotation_index INTEGER')
    except:
        pass
    
    # 重建所有 insert_points 以填充 annotation_index
    try:
        cursor.execute('SELECT DISTINCT section_id FROM insert_points WHERE annotation_index IS NULL AND point_type = ? AND annotation_id IS NOT NULL', ('annotation',))
        sections_to_rebuild = [r[0] for r in cursor.fetchall()]
        for sec_id in sections_to_rebuild:
            try:
                create_insert_points(sec_id)
            except:
                pass
    except:
        pass

    # 兼容旧数据库：确保users表有所有字段
    user_columns = [
        ('password', 'TEXT'),
        ('wechat_openid', 'TEXT'),
        ('wechat_nickname', 'TEXT'),
        ('wechat_avatar', 'TEXT'),
        ('device_id', 'TEXT'),
        ('device_info', 'TEXT'),
        ('gender', 'TEXT'),
        ('age', 'INTEGER'),
        ('grade', 'TEXT'),
        ('role', "TEXT DEFAULT 'user'")
    ]
    for col_name, col_type in user_columns:
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN ' + col_name + ' ' + col_type)
        except:
            pass

    # ===== 军衔等级配置表 =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS military_ranks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rank_name TEXT NOT NULL,
            rank_level INTEGER NOT NULL,
            min_words INTEGER NOT NULL,
            title TEXT NOT NULL,
            icon TEXT NOT NULL
        )
    ''')

    # 插入20个军衔等级数据（仅在表为空时插入）
    cursor.execute('SELECT COUNT(*) FROM military_ranks')
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO military_ranks (rank_name, rank_level, min_words, title, icon)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            ('列兵', 1, 0, '阅读新兵', 'private'),
            ('上等兵', 2, 5000, '阅读学徒', 'private_first'),
            ('下士', 3, 15000, '阅读战士', 'sergeant_1'),
            ('中士', 4, 30000, '阅读骨干', 'sergeant_2'),
            ('上士', 5, 50000, '阅读精兵', 'sergeant_3'),
            ('四级军士长', 6, 80000, '阅读能手', 'sergeant_4'),
            ('三级军士长', 7, 120000, '阅读达人', 'sergeant_5'),
            ('二级军士长', 8, 180000, '阅读专家', 'sergeant_6'),
            ('一级军士长', 9, 250000, '阅读大师', 'sergeant_7'),
            ('少尉', 10, 350000, '阅读军官', '2lt'),
            ('中尉', 11, 500000, '阅读校官', '1lt'),
            ('上尉', 12, 700000, '阅读将官', 'cpt'),
            ('少校', 13, 950000, '阅读统帅', 'maj'),
            ('中校', 14, 1250000, '阅读传奇', 'ltc'),
            ('上校', 15, 1600000, '阅读神话', 'col'),
            ('大校', 16, 2000000, '阅读至尊', 'sen_col'),
            ('少将', 17, 2500000, '阅读战神', 'bg'),
            ('中将', 18, 3200000, '阅读王者', 'mg'),
            ('上将', 19, 4000000, '阅读帝皇', 'lg'),
            ('元帅', 20, 5000000, '阅读之神', 'marshal'),
        ])
        print("军衔等级数据初始化完成")

    conn.commit()
    conn.close()
    print("数据库初始化完成")

# ===== 用户系统 =====

def create_user(phone=None, password=None, wechat_openid=None, wechat_nickname=None, wechat_avatar=None, device_id=None, device_info=None, role='user'):
    """创建用户（支持手机号或微信登录）"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''INSERT INTO users (phone, password, wechat_openid, wechat_nickname, wechat_avatar, device_id, device_info, role) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (phone, password, wechat_openid, wechat_nickname, wechat_avatar, device_id, device_info, role)
        )
    except Exception as e:
        # 兼容旧数据库有auth_code NOT NULL约束
        if 'auth_code' in str(e):
            cursor.execute(
                '''INSERT INTO users (phone, password, wechat_openid, wechat_nickname, wechat_avatar, device_id, device_info, role, auth_code) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')''',
                (phone, password, wechat_openid, wechat_nickname, wechat_avatar, device_id, device_info, role)
            )
        else:
            raise e
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

def get_user_by_wechat_openid(wechat_openid):
    """通过微信openid获取用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE wechat_openid = ?', (wechat_openid,))
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

def update_user_profile(user_id, gender=None, age=None, grade=None):
    """更新用户个人信息"""
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    params = []
    if gender is not None:
        updates.append('gender = ?')
        params.append(gender)
    if age is not None:
        updates.append('age = ?')
        params.append(age)
    if grade is not None:
        updates.append('grade = ?')
        params.append(grade)
    if updates:
        params.append(user_id)
        cursor.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()
    conn.close()

def update_user_phone(user_id, phone, password=None):
    """绑定/更新用户手机号和密码"""
    conn = get_db()
    cursor = conn.cursor()
    if password:
        cursor.execute('UPDATE users SET phone = ?, password = ? WHERE id = ?', (phone, password, user_id))
    else:
        cursor.execute('UPDATE users SET phone = ? WHERE id = ?', (phone, user_id))
    conn.commit()
    conn.close()

def update_user_password(user_id, password):
    """更新用户密码"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password = ? WHERE id = ?', (password, user_id))
    conn.commit()
    conn.close()

def update_user_wechat(user_id, wechat_openid, wechat_nickname=None, wechat_avatar=None):
    """更新用户微信信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET wechat_openid = ?, wechat_nickname = ?, wechat_avatar = ? WHERE id = ?',
        (wechat_openid, wechat_nickname, wechat_avatar, user_id)
    )
    conn.commit()
    conn.close()

def delete_user(user_id):
    """删除用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def verify_user_phone_password(phone, password):
    """验证手机号密码登录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = ? AND password = ?', (phone, password))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# ===== 留言系统 =====

def add_message(user_id, content):
    """添加用户留言"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO messages (user_id, content) VALUES (?, ?)',
        (user_id, content)
    )
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return message_id

def get_messages_by_user(user_id):
    """获取用户的留言"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    )
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def get_all_messages():
    """获取所有留言（管理员用）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, u.wechat_nickname, u.phone 
        FROM messages m 
        LEFT JOIN users u ON m.user_id = u.id 
        ORDER BY m.created_at DESC
    ''')
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def reply_message(message_id, admin_reply):
    """管理员回复留言"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE messages SET admin_reply = ?, replied_at = CURRENT_TIMESTAMP WHERE id = ?',
        (admin_reply, message_id)
    )
    conn.commit()
    conn.close()

# ===== 设备管理 =====

def update_user_device(user_id, device_id, device_info=None):
    """更新用户绑定的设备ID和设备信息"""
    conn = get_db()
    cursor = conn.cursor()
    if device_info:
        cursor.execute('UPDATE users SET device_id = ?, device_info = ? WHERE id = ?', (device_id, device_info, user_id))
    else:
        cursor.execute('UPDATE users SET device_id = ? WHERE id = ?', (device_id, user_id))
    conn.commit()
    conn.close()

def create_transfer_code(user_id):
    """生成换机校验码（6位数字）"""
    import random
    conn = get_db()
    cursor = conn.cursor()
    # 生成6位随机数字
    transfer_code = ''.join(random.choices('0123456789', k=6))
    # 删除该用户旧的校验码
    cursor.execute('DELETE FROM device_transfer_codes WHERE user_id = ?', (user_id,))
    # 插入新校验码
    cursor.execute(
        'INSERT INTO device_transfer_codes (user_id, transfer_code) VALUES (?, ?)',
        (user_id, transfer_code)
    )
    conn.commit()
    conn.close()
    return transfer_code

def verify_transfer_code(user_id, transfer_code):
    """验证换机校验码（1分钟有效）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM device_transfer_codes WHERE user_id = ? AND transfer_code = ?',
        (user_id, transfer_code)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, '校验码错误'
    
    # 检查是否超过1分钟 - 使用UTC时间避免时区问题
    from datetime import datetime, timedelta, timezone
    created_at_str = row['created_at']
    # 解析数据库时间（SQLite存储的是UTC时间）
    created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    # 获取当前UTC时间
    now = datetime.now(timezone.utc)
    # 计算时间差
    diff = now - created_at
    print(f"[DEBUG] Transfer code check: created_at={created_at}, now={now}, diff={diff.total_seconds()}s")
    if diff > timedelta(minutes=1):
        conn.close()
        return False, f'校验码已过期（1分钟有效），已过去{int(diff.total_seconds())}秒'
    
    # 验证成功，删除校验码
    cursor.execute('DELETE FROM device_transfer_codes WHERE id = ?', (row['id'],))
    conn.commit()
    conn.close()
    return True, '验证成功'

# ===== 订阅系统 =====

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

def add_thought(user_id, section_id, start_char, end_char, original_text, content, ai_score=None):
    """添加思考"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO thoughts (user_id, section_id, start_char, end_char, original_text, content, ai_score) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, section_id, start_char, end_char, original_text, content, ai_score)
    )
    thought_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return thought_id

def update_thought_ai_score(thought_id, ai_score):
    """更新思考的AI评分"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE thoughts SET ai_score = ? WHERE id = ?', (ai_score, thought_id))
    conn.commit()
    conn.close()

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

def add_book(title, author=None, file_path=None, author_nationality=None, version=None):
    """添加书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO books (title, author, file_path, author_nationality, version) VALUES (?, ?, ?, ?, ?)',
        (title, author, file_path, author_nationality, version)
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
    # 更新书籍的总章节数
    cursor.execute('UPDATE books SET total_chapters = total_chapters + 1 WHERE id = ?', (book_id,))
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
    # 先获取book_id
    cursor.execute('SELECT book_id FROM chapters WHERE id = ?', (chapter_id,))
    row = cursor.fetchone()
    book_id = row[0] if row else None
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
    # 级联删除 text_segments 和 insert_points
    cursor.execute('DELETE FROM insert_points WHERE section_id IN (SELECT id FROM sections WHERE chapter_id = ?)', (chapter_id,))
    cursor.execute('DELETE FROM text_segments WHERE section_id IN (SELECT id FROM sections WHERE chapter_id = ?)', (chapter_id,))
    # 删除关联的小节
    cursor.execute('DELETE FROM sections WHERE chapter_id = ?', (chapter_id,))
    # 删除章节
    cursor.execute('DELETE FROM chapters WHERE id = ?', (chapter_id,))
    # 更新书籍统计
    if book_id:
        cursor.execute('SELECT COUNT(*) FROM chapters WHERE book_id = ?', (book_id,))
        ch_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM sections WHERE book_id = ?', (book_id,))
        sec_count = cursor.fetchone()[0]
        cursor.execute('UPDATE books SET total_chapters = ?, total_sections = ? WHERE id = ?', (ch_count, sec_count, book_id))
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
    # 级联删除 text_segments 和 insert_points
    cursor.execute('DELETE FROM insert_points WHERE section_id = ?', (section_id,))
    cursor.execute('DELETE FROM text_segments WHERE section_id = ?', (section_id,))
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

def update_progress(user_id, book_id, section_id, position=0, audio_position=0):
    """更新阅读进度（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT OR REPLACE INTO reading_progress
           (user_id, book_id, current_section_id, current_position, audio_position, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, book_id, section_id, position, audio_position, datetime.now())
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

# ===== 管理员统计查询 =====

def get_users_with_stats(phone=None, role=None, gender=None, age_above=None, age_below=None):
    """获取用户列表及其阅读统计"""
    conn = get_db()
    cursor = conn.cursor()

    query = '''
        SELECT u.id, u.phone, u.role, u.gender, u.age, u.grade, u.created_at, u.device_id, u.device_info,
               COALESCE(read_stats.read_sections_count, 0) as read_sections_count,
               COALESCE(read_stats.read_words_count, 0) as read_words_count,
               COALESCE(thought_stats.thoughts_count, 0) as thoughts_count
        FROM users u
        LEFT JOIN (
            SELECT srs.user_id,
                   COUNT(*) as read_sections_count,
                   COALESCE(SUM(sec.word_count), 0) as read_words_count
            FROM section_reading_status srs
            JOIN sections sec ON srs.section_id = sec.id
            WHERE srs.status = 'read'
            GROUP BY srs.user_id
        ) read_stats ON u.id = read_stats.user_id
        LEFT JOIN (
            SELECT t.user_id, COUNT(*) as thoughts_count
            FROM thoughts t
            GROUP BY t.user_id
        ) thought_stats ON u.id = thought_stats.user_id
        WHERE 1=1
    '''
    params = []

    if phone:
        query += ' AND u.phone LIKE ?'
        params.append(f'%{phone}%')
    if role:
        query += ' AND u.role = ?'
        params.append(role)
    if gender:
        query += ' AND u.gender = ?'
        params.append(gender)
    if age_above is not None:
        query += ' AND u.age >= ?'
        params.append(int(age_above))
    if age_below is not None:
        query += ' AND u.age <= ?'
        params.append(int(age_below))

    query += ' ORDER BY u.created_at DESC'

    cursor.execute(query, params)
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def get_books_with_stats():
    """获取书籍列表及其统计信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*,
               COALESCE(sec_stats.total_words, 0) as total_words,
               COALESCE(anno_stats.total_annotations, 0) as total_annotations,
               COALESCE(sub_stats.subscription_count, 0) as subscription_count
        FROM books b
        LEFT JOIN (
            SELECT book_id, COALESCE(SUM(word_count), 0) as total_words
            FROM sections
            GROUP BY book_id
        ) sec_stats ON b.id = sec_stats.book_id
        LEFT JOIN (
            SELECT s.book_id, COUNT(*) as total_annotations
            FROM annotations a
            JOIN sections s ON a.section_id = s.id
            GROUP BY s.book_id
        ) anno_stats ON b.id = anno_stats.book_id
        LEFT JOIN (
            SELECT book_id, COUNT(*) as subscription_count
            FROM subscriptions
            GROUP BY book_id
        ) sub_stats ON b.id = sub_stats.book_id
        ORDER BY b.created_at DESC
    ''')
    books = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return books


def update_book_price(book_id, price):
    """更新书籍订阅价格"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE books SET subscription_price = ? WHERE id = ?', (price, book_id))
    conn.commit()
    conn.close()


def get_book_catalog_stats(book_id):
    """获取书籍的目录结构及统计信息"""
    conn = get_db()
    cursor = conn.cursor()

    # 获取所有章节
    cursor.execute('''
        SELECT c.*,
               COALESCE(sec_agg.section_count, 0) as section_count,
               COALESCE(sec_agg.total_words, 0) as total_words,
               COALESCE(sec_agg.total_annotations, 0) as total_annotations
        FROM chapters c
        LEFT JOIN (
            SELECT s.chapter_id,
                   COUNT(*) as section_count,
                   COALESCE(SUM(s.word_count), 0) as total_words,
                   COALESCE(SUM(anno.cnt), 0) as total_annotations
            FROM sections s
            LEFT JOIN (
                SELECT section_id, COUNT(*) as cnt
                FROM annotations
                GROUP BY section_id
            ) anno ON s.id = anno.section_id
            WHERE s.book_id = ?
            GROUP BY s.chapter_id
        ) sec_agg ON c.id = sec_agg.chapter_id
        WHERE c.book_id = ?
        ORDER BY c.chapter_number
    ''', (book_id, book_id))
    chapters = [dict(row) for row in cursor.fetchall()]

    # 获取每个章节的sections及统计
    for ch in chapters:
        cursor.execute('''
            SELECT s.*,
                   COALESCE(anno.cnt, 0) as annotation_count
            FROM sections s
            LEFT JOIN (
                SELECT section_id, COUNT(*) as cnt
                FROM annotations
                GROUP BY section_id
            ) anno ON s.id = anno.section_id
            WHERE s.chapter_id = ?
            ORDER BY s.section_number
        ''', (ch['id'],))
        sections = [dict(row) for row in cursor.fetchall()]
        ch['sections'] = sections

    # 获取不属于任何章节的sections
    cursor.execute('''
        SELECT s.*,
               COALESCE(anno.cnt, 0) as annotation_count
        FROM sections s
        LEFT JOIN (
            SELECT section_id, COUNT(*) as cnt
            FROM annotations
            GROUP BY section_id
        ) anno ON s.id = anno.section_id
        WHERE s.book_id = ? AND s.chapter_id IS NULL
        ORDER BY s.section_number
    ''', (book_id,))
    orphan_sections = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        'chapters': chapters,
        'orphan_sections': orphan_sections
    }


def get_user_subscription_stats(user_id):
    """获取用户订阅的书籍及每本书的阅读统计"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.id as book_id, b.title, b.author_nationality, b.version,
               sub.created_at as subscribed_at,
               COALESCE(read_stats.read_sections_count, 0) as read_sections_count,
               COALESCE(read_stats.read_words_count, 0) as read_words_count,
               COALESCE(thought_stats.thoughts_count, 0) as thoughts_count
        FROM subscriptions sub
        JOIN books b ON sub.book_id = b.id
        LEFT JOIN (
            SELECT srs.book_id,
                   COUNT(*) as read_sections_count,
                   COALESCE(SUM(sec.word_count), 0) as read_words_count
            FROM section_reading_status srs
            JOIN sections sec ON srs.section_id = sec.id
            WHERE srs.status = 'read' AND srs.user_id = ?
            GROUP BY srs.book_id
        ) read_stats ON b.id = read_stats.book_id
        LEFT JOIN (
            SELECT t.user_id, sec.book_id, COUNT(*) as thoughts_count
            FROM thoughts t
            JOIN sections sec ON t.section_id = sec.id
            WHERE t.user_id = ?
            GROUP BY sec.book_id
        ) thought_stats ON b.id = thought_stats.book_id
        WHERE sub.user_id = ?
        ORDER BY sub.created_at DESC
    ''', (user_id, user_id, user_id))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def admin_add_subscription(user_id, book_id):
    """管理员添加订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO subscriptions (user_id, book_id) VALUES (?, ?)',
        (user_id, book_id)
    )
    conn.commit()
    conn.close()


def admin_remove_subscription(user_id, book_id):
    """管理员移除订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM subscriptions WHERE user_id = ? AND book_id = ?',
        (user_id, book_id)
    )
    conn.commit()
    conn.close()

# ==================== text_segments 相关操作 ====================

def create_text_segments(section_id):
    """根据节的 annotations 按边界切割 content 为 n+1 段，写入 text_segments 表"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取节内容和点评
    cursor.execute('SELECT content FROM sections WHERE id = ?', (section_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return 0
    content = row['content']
    
    # 去掉换行符，得到纯文本
    text = content.replace('\n', '')
    text_len = len(text)
    
    # 获取点评（按 start_char 排序）
    cursor.execute('SELECT id, start_char, end_char FROM annotations WHERE section_id = ? ORDER BY start_char', (section_id,))
    annotations = [dict(r) for r in cursor.fetchall()]
    
    # 确定分割点：在点评的 end_char 处切割
    # end_char 是不包含的边界（Python切片风格 [start, end)）
    split_points = sorted(set([0] + [ann['end_char'] for ann in annotations] + [text_len]))
    
    # 删除旧的 text_segments
    cursor.execute('DELETE FROM text_segments WHERE section_id = ?', (section_id,))
    
    # 创建新的 text_segments
    for i in range(len(split_points) - 1):
        start = split_points[i]
        end = split_points[i + 1]  # end 是下一个分割点（点评的 end_char 或下一个 start_char）
        if end <= start:
            continue
        seg_content = text[start:end]  # 内容从 start 到 end-1
        word_count = len(seg_content)
        # end_char 存储为 end（不包含的边界，与 annotation end_char 语义一致）
        cursor.execute(
            'INSERT INTO text_segments (section_id, segment_number, content, start_char, end_char, word_count) VALUES (?, ?, ?, ?, ?, ?)',
            (section_id, i, seg_content, start, end, word_count)
        )
    
    conn.commit()
    conn.close()
    return len(split_points) - 1

def get_text_segments(section_id):
    """获取一节的所有 text_segments，按 segment_number 排序"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM text_segments WHERE section_id = ? ORDER BY segment_number', (section_id,))
    segments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return segments

def get_text_segment(segment_id):
    """获取单个 text_segment"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM text_segments WHERE id = ?', (segment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_text_segment_audio(segment_id, audio_path, audio_duration, char_timeline):
    """更新段的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE text_segments SET audio_path = ?, audio_duration = ?, char_timeline = ? WHERE id = ?',
        (audio_path, audio_duration, char_timeline, segment_id)
    )
    conn.commit()
    conn.close()

def delete_text_segments_by_section(section_id):
    """删除一节的所有 text_segments"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM text_segments WHERE section_id = ?', (section_id,))
    conn.commit()
    conn.close()

# ==================== insert_points 相关操作 ====================

def create_insert_points(section_id):
    """根据 annotations 和 summary 创建 insert_points 记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取点评（包含 annotation_index）
    cursor.execute('SELECT id, annotation_index, start_char, end_char, original_text, comment, audio_path, audio_duration FROM annotations WHERE section_id = ? ORDER BY start_char', (section_id,))
    annotations = [dict(r) for r in cursor.fetchall()]
    
    # 获取小结
    cursor.execute('SELECT summary, summary_audio_path, summary_audio_duration FROM sections WHERE id = ?', (section_id,))
    sec_row = cursor.fetchone()
    summary = sec_row['summary'] if sec_row else None
    summary_audio_path = sec_row['summary_audio_path'] if sec_row else None
    summary_audio_duration = sec_row['summary_audio_duration'] if sec_row else 0
    
    # 获取 text_segments
    cursor.execute('SELECT id, end_char FROM text_segments WHERE section_id = ? ORDER BY segment_number', (section_id,))
    segments = [dict(r) for r in cursor.fetchall()]
    
    # 删除旧的 insert_points
    cursor.execute('DELETE FROM insert_points WHERE section_id = ?', (section_id,))
    
    # 为每个 annotation 创建 insert_point
    for ann in annotations:
        # 找到 end_char 等于哪个 text_segment 的 end_char
        target_segment_id = None
        for seg in segments:
            if seg['end_char'] == ann['end_char']:
                target_segment_id = seg['id']
                break
        if not target_segment_id:
            print(f"[create_insert_points] 警告: 点评 {ann['id']} end_char={ann['end_char']} 找不到匹配的段")
            continue
        
        cursor.execute(
            '''INSERT INTO insert_points (section_id, segment_id, point_order, point_type, annotation_id, annotation_index, quote_text, quote_start_char, quote_end_char, comment, audio_path, audio_duration)
               VALUES (?, ?, ?, 'annotation', ?, ?, ?, ?, ?, ?, ?, ?)''',
            (section_id, target_segment_id, ann['start_char'], ann['id'], ann.get('annotation_index'), ann['original_text'], ann['start_char'], ann['end_char'], ann['comment'], ann.get('audio_path'), ann.get('audio_duration', 0))
        )
    
    # 为 summary 创建 insert_point（绑定到最后一个段）
    if summary and segments:
        last_segment = segments[-1]
        cursor.execute(
            '''INSERT INTO insert_points (section_id, segment_id, point_order, point_type, comment, audio_path, audio_duration)
               VALUES (?, ?, 999999, 'summary', ?, ?, ?)''',
            (section_id, last_segment['id'], summary, summary_audio_path, summary_audio_duration)
        )
    
    conn.commit()
    conn.close()

def get_insert_points_by_section(section_id):
    """获取一节的所有 insert_points，按 segment 关联排序"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ip.*, ts.segment_number
        FROM insert_points ip
        JOIN text_segments ts ON ip.segment_id = ts.id
        WHERE ip.section_id = ?
        ORDER BY ts.segment_number, ip.point_order
    ''', (section_id,))
    points = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return points

def get_insert_points_by_segment(segment_id):
    """获取一个 text_segment 后的所有插入点"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM insert_points WHERE segment_id = ? ORDER BY point_order', (segment_id,))
    points = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return points

def update_insert_point_audio(insert_point_id, audio_path, audio_duration):
    """更新插入点的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE insert_points SET audio_path = ?, audio_duration = ? WHERE id = ?',
        (audio_path, audio_duration, insert_point_id)
    )
    conn.commit()
    conn.close()

def update_insert_point_quote_audio(insert_point_id, quote_audio_path, quote_audio_duration):
    """更新插入点的引用音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE insert_points SET quote_audio_path = ?, quote_audio_duration = ? WHERE id = ?',
        (quote_audio_path, quote_audio_duration, insert_point_id)
    )
    conn.commit()
    conn.close()

def delete_insert_points_by_section(section_id):
    """删除一节的所有 insert_points"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM insert_points WHERE section_id = ?', (section_id,))
    conn.commit()
    conn.close()

# ==================== 播放计划 ====================

def get_section_playback_plan(section_id):
    """获取一节的完整播放计划：text_segments + insert_points 交错排列"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取所有 text_segments
    cursor.execute('SELECT * FROM text_segments WHERE section_id = ? ORDER BY segment_number', (section_id,))
    segments = [dict(row) for row in cursor.fetchall()]
    
    # 获取所有 insert_points
    cursor.execute('SELECT * FROM insert_points WHERE section_id = ? ORDER BY point_order', (section_id,))
    all_points = [dict(row) for row in cursor.fetchall()]
    
    # 按 segment_id 分组
    points_by_segment = {}
    for p in all_points:
        sid = p['segment_id']
        if sid not in points_by_segment:
            points_by_segment[sid] = []
        points_by_segment[sid].append(p)
    
    # 构建播放计划
    playlist = []
    total_duration = 0
    
    for seg in segments:
        # 添加文本段
        seg_item = {
            'type': 'text_segment',
            'id': seg['id'],
            'segment_number': seg['segment_number'],
            'content': seg['content'],
            'start_char': seg['start_char'],
            'end_char': seg['end_char'],
            'word_count': seg['word_count'],
            'audio_path': seg['audio_path'],
            'audio_duration': seg['audio_duration'] or 0,
            'char_timeline': seg['char_timeline']
        }
        playlist.append(seg_item)
        total_duration += seg['audio_duration'] or 0
        
        # 添加该段后的插入点
        if seg['id'] in points_by_segment:
            for ip in points_by_segment[seg['id']]:
                ip_item = {
                    'type': 'insert_point',
                    'id': ip['id'],
                    'point_type': ip['point_type'],
                    'segment_id': ip['segment_id'],
                    'annotation_id': ip.get('annotation_id'),
                    'annotation_index': ip.get('annotation_index'),
                    'quote_text': ip.get('quote_text'),
                    'quote_start_char': ip.get('quote_start_char'),
                    'quote_end_char': ip.get('quote_end_char'),
                    'quote_audio_path': ip.get('quote_audio_path'),
                    'quote_audio_duration': ip.get('quote_audio_duration') or 0,
                    'comment': ip['comment'],
                    'audio_path': ip['audio_path'],
                    'audio_duration': ip['audio_duration'] or 0,
                    'char_timeline': ip.get('char_timeline')
                }
                playlist.append(ip_item)
                total_duration += ip['audio_duration'] or 0
    
    conn.close()
    
    return {
        'section_id': section_id,
        'total_duration': total_duration,
        'playlist': playlist
    }

# ==================== 新版断点 ====================

def update_progress_v2(user_id, book_id, section_id, segment_id, text_position, audio_position):
    """新版断点保存：包含 segment_id"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT OR REPLACE INTO reading_progress
           (user_id, book_id, current_section_id, current_segment_id, current_position, audio_position, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, book_id, section_id, segment_id, text_position, audio_position, datetime.now())
    )
    conn.commit()
    conn.close()

def get_progress_v2(user_id, book_id):
    """新版断点读取"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM reading_progress WHERE user_id = ? AND book_id = ? ORDER BY updated_at DESC LIMIT 1',
        (user_id, book_id)
    )
    progress = cursor.fetchone()
    conn.close()
    return dict(progress) if progress else None

def check_section_audio_complete(section_id):
    """检查一节的所有 text_segments 和 insert_points 是否都有音频"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM text_segments WHERE section_id = ? AND audio_path IS NOT NULL AND audio_path != ""', (section_id,))
    seg_with_audio = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM text_segments WHERE section_id = ?', (section_id,))
    seg_total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM insert_points WHERE section_id = ? AND audio_path IS NOT NULL AND audio_path != ""', (section_id,))
    ip_with_audio = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM insert_points WHERE section_id = ?', (section_id,))
    ip_total = cursor.fetchone()[0]
    
    conn.close()
    return seg_with_audio == seg_total and ip_with_audio == ip_total


# ==================== 军衔等级系统 ====================

def get_user_total_read_words(user_id):
    """计算用户累计阅读字数（从 reading_status 中 status='read' 的 sections 统计 word_count）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COALESCE(SUM(sec.word_count), 0) as total_words
        FROM section_reading_status srs
        JOIN sections sec ON srs.section_id = sec.id
        WHERE srs.user_id = ? AND srs.status = 'read'
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['total_words'] if row else 0

def calculate_military_rank(total_words):
    """根据累计阅读字数返回对应的军衔等级信息"""
    conn = get_db()
    cursor = conn.cursor()
    # 查找满足条件的最高等级（min_words <= total_words 的最大 rank_level）
    cursor.execute('''
        SELECT * FROM military_ranks
        WHERE min_words <= ?
        ORDER BY rank_level DESC
        LIMIT 1
    ''', (total_words,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    # 如果没有匹配（理论上不会，因为等级1的min_words=0），返回最低等级
    return {'id': 1, 'rank_name': '列兵', 'rank_level': 1, 'min_words': 0, 'title': '阅读新兵', 'icon': '🪖'}

def get_user_military_rank(user_id):
    """返回用户当前军衔信息，包含进度详情"""
    total_words = get_user_total_read_words(user_id)
    current_rank = calculate_military_rank(total_words)

    # 查找下一级军衔信息
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM military_ranks
        WHERE rank_level = ?
    ''', (current_rank['rank_level'] + 1,))
    next_rank = cursor.fetchone()
    conn.close()

    # 计算进度百分比
    if next_rank:
        next_min_words = next_rank['min_words']
        current_min_words = current_rank['min_words']
        # 当前等级内的进度 = (当前字数 - 当前等级最低字数) / (下一等级最低字数 - 当前等级最低字数)
        progress_range = next_min_words - current_min_words
        if progress_range > 0:
            progress = (total_words - current_min_words) / progress_range * 100
        else:
            progress = 100
        progress = min(max(progress, 0), 100)  # 限制在0-100之间
    else:
        # 已是最高等级
        next_min_words = None
        progress = 100

    return {
        'user_id': user_id,
        'total_words': total_words,
        'current_rank': {
            'rank_name': current_rank['rank_name'],
            'rank_level': current_rank['rank_level'],
            'title': current_rank['title'],
            'icon': current_rank['icon'],
            'min_words': current_rank['min_words'],
        },
        'next_rank': {
            'rank_name': next_rank['rank_name'],
            'rank_level': next_rank['rank_level'],
            'title': next_rank['title'],
            'icon': next_rank['icon'],
            'min_words': next_rank['min_words'],
        } if next_rank else None,
        'next_rank_min_words': next_min_words,
        'progress': round(progress, 1),
    }


if __name__ == '__main__':
    init_db()
