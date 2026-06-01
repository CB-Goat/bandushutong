# -*- coding: utf-8 -*-
"""
悦读小将 - 数据库模块 (MySQL版本)
使用 PyMySQL 连接 MySQL 数据库
"""

import pymysql
import os
from datetime import datetime

# 尝试加载 .env 文件
def _load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

_load_env_file()

# 从环境变量读取 MySQL 连接信息
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'reading_companion')

def get_db():
    """获取数据库连接"""
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 书籍表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INT PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(255),
            author_nationality VARCHAR(100),
            version VARCHAR(100),
            file_path VARCHAR(500),
            total_sections INT DEFAULT 0,
            total_chapters INT DEFAULT 0,
            voice_type VARCHAR(20) DEFAULT 'male',
            tts_status VARCHAR(20) DEFAULT 'none',
            tts_progress VARCHAR(50) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subscription_price DECIMAL(10,2) DEFAULT 0,
            is_public TINYINT DEFAULT 0,
            icon_path VARCHAR(500)
        )
    ''')

    # 章节表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chapters (
            id INT PRIMARY KEY AUTO_INCREMENT,
            book_id INT NOT NULL,
            chapter_number INT NOT NULL,
            title VARCHAR(255),
            section_count INT DEFAULT 0,
            total_words INT DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # 小节表（阅读的最小单位）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sections (
            id INT PRIMARY KEY AUTO_INCREMENT,
            book_id INT NOT NULL,
            chapter_id INT,
            section_number INT NOT NULL,
            title VARCHAR(255),
            content TEXT NOT NULL,
            audio_path VARCHAR(500),
            has_audio TINYINT DEFAULT 0,
            audio_duration FLOAT DEFAULT 0,
            char_timeline TEXT,
            word_count INT DEFAULT 0,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary_audio_path VARCHAR(500),
            summary_audio_duration FLOAT DEFAULT 0,
            audio_segments TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (chapter_id) REFERENCES chapters(id)
        )
    ''')

    # 阅读进度表（按用户隔离）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_progress (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            book_id INT NOT NULL,
            current_section_id INT,
            current_segment_id INT,
            current_position INT DEFAULT 0,
            audio_position FLOAT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (current_section_id) REFERENCES sections(id),
            UNIQUE KEY unique_user_book (user_id, book_id)
        )
    ''')

    # 点评点表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            id INT PRIMARY KEY AUTO_INCREMENT,
            section_id INT NOT NULL,
            annotation_index INT NOT NULL,
            start_char INT NOT NULL,
            end_char INT NOT NULL,
            original_text TEXT NOT NULL,
            comment TEXT NOT NULL,
            audio_path VARCHAR(500),
            audio_duration FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections(id)
        )
    ''')

    # 节阅读状态表（按用户隔离）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS section_reading_status (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            book_id INT NOT NULL,
            section_id INT NOT NULL,
            status VARCHAR(20) DEFAULT 'unread',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (section_id) REFERENCES sections(id),
            UNIQUE KEY unique_user_book_section (user_id, book_id, section_id)
        )
    ''')

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            phone VARCHAR(20) UNIQUE,
            password VARCHAR(255),
            wechat_openid VARCHAR(100) UNIQUE,
            wechat_nickname VARCHAR(100),
            wechat_avatar VARCHAR(500),
            device_id VARCHAR(100),
            device_info TEXT,
            gender VARCHAR(10),
            age INT,
            grade VARCHAR(50),
            role VARCHAR(20) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 用户留言表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            content TEXT NOT NULL,
            admin_reply TEXT,
            is_read TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            replied_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 换机校验码表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_transfer_codes (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            transfer_code VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 订阅表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            book_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES books(id),
            UNIQUE KEY unique_user_book_sub (user_id, book_id)
        )
    ''')

    # 订阅申请表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscription_requests (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            book_id INT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # 思考表（用户个人点评）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thoughts (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            section_id INT NOT NULL,
            start_char INT NOT NULL,
            end_char INT NOT NULL,
            original_text TEXT NOT NULL,
            content TEXT NOT NULL,
            ai_score INT DEFAULT NULL,
            score_reason TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (section_id) REFERENCES sections(id)
        )
    ''')

    # 名言表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INT PRIMARY KEY AUTO_INCREMENT,
            content TEXT NOT NULL,
            author VARCHAR(255),
            source VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 名言使用记录表（记录某节已用过哪些名言）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quote_usage (
            id INT PRIMARY KEY AUTO_INCREMENT,
            quote_id INT NOT NULL,
            book_id INT NOT NULL,
            section_id INT NOT NULL,
            user_id INT NOT NULL,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quote_id) REFERENCES quotes(id),
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (section_id) REFERENCES sections(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 文本段表：一节文字按点评边界切割成 n+1 段
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS text_segments (
            id INT PRIMARY KEY AUTO_INCREMENT,
            section_id INT NOT NULL,
            segment_number INT NOT NULL,
            content TEXT NOT NULL,
            start_char INT NOT NULL,
            end_char INT NOT NULL,
            word_count INT DEFAULT 0,
            audio_path VARCHAR(500),
            audio_duration FLOAT DEFAULT 0,
            char_timeline TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
            UNIQUE KEY unique_section_segment (section_id, segment_number)
        )
    ''')
    try:
        cursor.execute('CREATE INDEX idx_text_segments_section ON text_segments(section_id)')
    except:
        pass

    # 插入点表：点评/小结绑定到对应段
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insert_points (
            id INT PRIMARY KEY AUTO_INCREMENT,
            section_id INT NOT NULL,
            segment_id INT NOT NULL,
            point_order INT NOT NULL,
            point_type VARCHAR(20) NOT NULL,
            annotation_id INT,
            annotation_index INT,
            quote_text TEXT,
            quote_start_char INT,
            quote_end_char INT,
            comment TEXT NOT NULL,
            audio_path VARCHAR(500),
            audio_duration FLOAT DEFAULT 0,
            quote_audio_path VARCHAR(500),
            quote_audio_duration FLOAT DEFAULT 0,
            char_timeline TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES text_segments(id) ON DELETE CASCADE,
            FOREIGN KEY (annotation_id) REFERENCES annotations(id) ON DELETE SET NULL
        )
    ''')
    try:
        cursor.execute('CREATE INDEX idx_insert_points_section ON insert_points(section_id)')
    except:
        pass
    try:
        cursor.execute('CREATE INDEX idx_insert_points_segment ON insert_points(segment_id)')
    except:
        pass

    # 军衔等级配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS military_ranks (
            id INT PRIMARY KEY AUTO_INCREMENT,
            rank_name VARCHAR(50) NOT NULL,
            rank_level INT NOT NULL,
            min_words INT NOT NULL,
            title VARCHAR(100) NOT NULL,
            icon VARCHAR(50) NOT NULL
        )
    ''')

    # 插入20个军衔等级数据（仅在表为空时插入）
    cursor.execute('SELECT COUNT(*) as cnt FROM military_ranks')
    if cursor.fetchone()['cnt'] == 0:
        cursor.executemany('''
            INSERT INTO military_ranks (rank_name, rank_level, min_words, title, icon)
            VALUES (%s, %s, %s, %s, %s)
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

    # 军功章表：记录用户获得的军功
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_merits (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            merit_type VARCHAR(20) NOT NULL,
            batch INT NOT NULL DEFAULT 1,
            thought_count INT NOT NULL,
            three_star_rate FLOAT,
            two_star_rate FLOAT,
            one_star_rate FLOAT,
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_type_batch (user_id, merit_type, batch)
        )
    ''')

    # 勋章表：记录用户获得的勋章
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_medals (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            medal_type VARCHAR(20) NOT NULL,
            total_three_stars INT NOT NULL,
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_medal (user_id, medal_type)
        )
    ''')

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
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (phone, password, wechat_openid, wechat_nickname, wechat_avatar, device_id, device_info, role)
        )
    except Exception as e:
        # 兼容旧数据库有auth_code NOT NULL约束
        if 'auth_code' in str(e):
            cursor.execute(
                '''INSERT INTO users (phone, password, wechat_openid, wechat_nickname, wechat_avatar, device_id, device_info, role, auth_code) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '')''',
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
    cursor.execute('SELECT * FROM users WHERE phone = %s', (phone,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_wechat_openid(wechat_openid):
    """通过微信openid获取用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE wechat_openid = %s', (wechat_openid,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user(user_id):
    """获取用户信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
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
    cursor.execute('UPDATE users SET role = %s WHERE id = %s', (role, user_id))
    conn.commit()
    conn.close()

def update_user_profile(user_id, gender=None, age=None, grade=None):
    """更新用户个人信息"""
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    params = []
    if gender is not None:
        updates.append('gender = %s')
        params.append(gender)
    if age is not None:
        updates.append('age = %s')
        params.append(age)
    if grade is not None:
        updates.append('grade = %s')
        params.append(grade)
    if updates:
        params.append(user_id)
        cursor.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = %s', params)
        conn.commit()
    conn.close()

def update_user_phone(user_id, phone, password=None):
    """绑定/更新用户手机号和密码"""
    conn = get_db()
    cursor = conn.cursor()
    if password:
        cursor.execute('UPDATE users SET phone = %s, password = %s WHERE id = %s', (phone, password, user_id))
    else:
        cursor.execute('UPDATE users SET phone = %s WHERE id = %s', (phone, user_id))
    conn.commit()
    conn.close()

def update_user_password(user_id, password):
    """更新用户密码"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password = %s WHERE id = %s', (password, user_id))
    conn.commit()
    conn.close()

def update_user_wechat(user_id, wechat_openid, wechat_nickname=None, wechat_avatar=None):
    """更新用户微信信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET wechat_openid = %s, wechat_nickname = %s, wechat_avatar = %s WHERE id = %s',
        (wechat_openid, wechat_nickname, wechat_avatar, user_id)
    )
    conn.commit()
    conn.close()

def delete_user(user_id):
    """删除用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    conn.close()

def verify_user_phone_password(phone, password):
    """验证手机号密码登录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = %s AND password = %s', (phone, password))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# ===== 留言系统 =====

def add_message(user_id, content):
    """添加用户留言"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO messages (user_id, content) VALUES (%s, %s)',
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
        'SELECT * FROM messages WHERE user_id = %s ORDER BY created_at DESC',
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
        'UPDATE messages SET admin_reply = %s, replied_at = CURRENT_TIMESTAMP WHERE id = %s',
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
        cursor.execute('UPDATE users SET device_id = %s, device_info = %s WHERE id = %s', (device_id, device_info, user_id))
    else:
        cursor.execute('UPDATE users SET device_id = %s WHERE id = %s', (device_id, user_id))
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
    cursor.execute('DELETE FROM device_transfer_codes WHERE user_id = %s', (user_id,))
    # 插入新校验码
    cursor.execute(
        'INSERT INTO device_transfer_codes (user_id, transfer_code) VALUES (%s, %s)',
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
        'SELECT * FROM device_transfer_codes WHERE user_id = %s AND transfer_code = %s',
        (user_id, transfer_code)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, '校验码错误'
    
    # 检查是否超过1分钟 - 使用UTC时间避免时区问题
    from datetime import datetime, timedelta, timezone
    created_at = row['created_at']
    # 确保 created_at 是带时区的
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    # 获取当前UTC时间
    now = datetime.now(timezone.utc)
    # 计算时间差
    diff = now - created_at
    print(f"[DEBUG] Transfer code check: created_at={created_at}, now={now}, diff={diff.total_seconds()}s")
    if diff > timedelta(minutes=1):
        conn.close()
        return False, f'校验码已过期（1分钟有效），已过去{int(diff.total_seconds())}秒'
    
    # 验证成功，删除校验码
    cursor.execute('DELETE FROM device_transfer_codes WHERE id = %s', (row['id'],))
    conn.commit()
    conn.close()
    return True, '验证成功'

# ===== 订阅系统 =====

def subscribe_book(user_id, book_id):
    """用户订阅书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT IGNORE INTO subscriptions (user_id, book_id) VALUES (%s, %s)',
        (user_id, book_id)
    )
    conn.commit()
    conn.close()

def unsubscribe_book(user_id, book_id):
    """取消订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscriptions WHERE user_id = %s AND book_id = %s', (user_id, book_id))
    conn.commit()
    conn.close()

def get_user_subscriptions(user_id):
    """获取用户的所有订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT book_id FROM subscriptions WHERE user_id = %s', (user_id,))
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
        'INSERT IGNORE INTO subscription_requests (user_id, book_id) VALUES (%s, %s)',
        (user_id, book_id)
    )
    conn.commit()
    conn.close()

def approve_subscription_request(request_id):
    """审批订阅申请"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM subscription_requests WHERE id = %s', (request_id,))
    req = cursor.fetchone()
    if req:
        cursor.execute(
            'INSERT IGNORE INTO subscriptions (user_id, book_id) VALUES (%s, %s)',
            (req['user_id'], req['book_id'])
        )
        cursor.execute('DELETE FROM subscription_requests WHERE id = %s', (request_id,))
    conn.commit()
    conn.close()

def reject_subscription_request(request_id):
    """拒绝订阅申请"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscription_requests WHERE id = %s', (request_id,))
    conn.commit()
    conn.close()

# ===== 思考（用户个人点评）=====

def add_thought(user_id, section_id, start_char, end_char, original_text, content, ai_score=None, score_reason=None):
    """添加思考"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO thoughts (user_id, section_id, start_char, end_char, original_text, content, ai_score, score_reason) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (user_id, section_id, start_char, end_char, original_text, content, ai_score, score_reason)
    )
    thought_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return thought_id

def update_thought_ai_score(thought_id, ai_score, score_reason=None):
    """更新思考的AI评分"""
    conn = get_db()
    cursor = conn.cursor()
    if score_reason:
        cursor.execute('UPDATE thoughts SET ai_score = %s, score_reason = %s WHERE id = %s', (ai_score, score_reason, thought_id))
    else:
        cursor.execute('UPDATE thoughts SET ai_score = %s WHERE id = %s', (ai_score, thought_id))
    conn.commit()
    conn.close()

def get_thoughts_by_section(section_id, user_id=None):
    """获取某节的思考（可按用户过滤）"""
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute('SELECT * FROM thoughts WHERE section_id = %s AND user_id = %s ORDER BY start_char', (section_id, user_id))
    else:
        cursor.execute('SELECT * FROM thoughts WHERE section_id = %s ORDER BY start_char', (section_id,))
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
           WHERE t.section_id = %s ORDER BY t.start_char''', (section_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_thought(thought_id, user_id):
    """删除思考"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM thoughts WHERE id = %s AND user_id = %s', (thought_id, user_id))
    conn.commit()
    conn.close()

def update_thought(thought_id, user_id, content):
    """更新思考内容"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE thoughts SET content = %s WHERE id = %s AND user_id = %s', (content, thought_id, user_id))
    conn.commit()
    conn.close()

def get_unscored_thoughts_by_section(section_id, user_id):
    """获取某节未评分的思考（ai_score为NULL）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM thoughts WHERE section_id = %s AND user_id = %s AND ai_score IS NULL', (section_id, user_id))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_thought_by_id(thought_id):
    """根据ID获取思考"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM thoughts WHERE id = %s', (thought_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# ==================== 书籍相关操作 ====================

def add_book(title, author=None, file_path=None, author_nationality=None, version=None):
    """添加书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO books (title, author, file_path, author_nationality, version) VALUES (%s, %s, %s, %s, %s)',
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
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
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

def update_book(book_id, title, author, author_nationality, version, voice_type=None):
    """更新书籍信息"""
    conn = get_db()
    cursor = conn.cursor()
    if voice_type is not None:
        cursor.execute(
            'UPDATE books SET title = %s, author = %s, author_nationality = %s, version = %s, voice_type = %s WHERE id = %s',
            (title, author, author_nationality, version, voice_type, book_id)
        )
    else:
        cursor.execute(
            'UPDATE books SET title = %s, author = %s, author_nationality = %s, version = %s WHERE id = %s',
            (title, author, author_nationality, version, book_id)
        )
    conn.commit()
    conn.close()

def get_book_by_title_author_version(title, author, version):
    """根据书名+作者+版本查找书籍"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM books WHERE title = %s AND author = %s AND version = %s',
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
        (SELECT id FROM sections WHERE book_id = %s)
    ''', (book_id,))
    # 删除关联的节阅读状态
    cursor.execute('DELETE FROM section_reading_status WHERE book_id = %s', (book_id,))
    # 删除关联的小节
    cursor.execute('DELETE FROM sections WHERE book_id = %s', (book_id,))
    # 删除关联的章节
    cursor.execute('DELETE FROM chapters WHERE book_id = %s', (book_id,))
    # 删除关联的阅读进度
    cursor.execute('DELETE FROM reading_progress WHERE book_id = %s', (book_id,))
    # 删除书籍
    cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
    conn.commit()
    conn.close()

def update_book_chapters_count(book_id, count):
    """更新书籍章数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE books SET total_chapters = %s WHERE id = %s', (count, book_id))
    conn.commit()
    conn.close()

def update_book_sections_count(book_id, count):
    """更新书籍的小节数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE books SET total_sections = %s WHERE id = %s', (count, book_id))
    conn.commit()
    conn.close()

# ==================== 章节相关操作 ====================

def add_chapter(book_id, chapter_number, title):
    """添加章节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO chapters (book_id, chapter_number, title) VALUES (%s, %s, %s)',
        (book_id, chapter_number, title)
    )
    chapter_id = cursor.lastrowid
    # 更新书籍的总章节数
    cursor.execute('UPDATE books SET total_chapters = total_chapters + 1 WHERE id = %s', (book_id,))
    conn.commit()
    conn.close()
    return chapter_id

def get_chapters_by_book(book_id):
    """获取书籍的所有章节（按chapter_number排序）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM chapters WHERE book_id = %s ORDER BY chapter_number',
        (book_id,)
    )
    chapters = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return chapters

def get_chapter(chapter_id):
    """获取单个章节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chapters WHERE id = %s', (chapter_id,))
    chapter = cursor.fetchone()
    conn.close()
    return dict(chapter) if chapter else None

def update_chapter(chapter_id, title):
    """更新章节标题"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE chapters SET title = %s WHERE id = %s',
        (title, chapter_id)
    )
    conn.commit()
    conn.close()

def delete_chapter(chapter_id):
    """删除章节（同时删除关联的节和点评）"""
    conn = get_db()
    cursor = conn.cursor()
    # 先获取book_id
    cursor.execute('SELECT book_id FROM chapters WHERE id = %s', (chapter_id,))
    row = cursor.fetchone()
    book_id = row['book_id'] if row else None
    # 删除关联的点评
    cursor.execute('''
        DELETE FROM annotations WHERE section_id IN
        (SELECT id FROM sections WHERE chapter_id = %s)
    ''', (chapter_id,))
    # 删除关联的节阅读状态
    cursor.execute('''
        DELETE FROM section_reading_status WHERE section_id IN
        (SELECT id FROM sections WHERE chapter_id = %s)
    ''', (chapter_id,))
    # 级联删除 text_segments 和 insert_points
    cursor.execute('DELETE FROM insert_points WHERE section_id IN (SELECT id FROM sections WHERE chapter_id = %s)', (chapter_id,))
    cursor.execute('DELETE FROM text_segments WHERE section_id IN (SELECT id FROM sections WHERE chapter_id = %s)', (chapter_id,))
    # 删除关联的小节
    cursor.execute('DELETE FROM sections WHERE chapter_id = %s', (chapter_id,))
    # 删除章节
    cursor.execute('DELETE FROM chapters WHERE id = %s', (chapter_id,))
    # 更新书籍统计
    if book_id:
        cursor.execute('SELECT COUNT(*) as cnt FROM chapters WHERE book_id = %s', (book_id,))
        ch_count = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) as cnt FROM sections WHERE book_id = %s', (book_id,))
        sec_count = cursor.fetchone()['cnt']
        cursor.execute('UPDATE books SET total_chapters = %s, total_sections = %s WHERE id = %s', (ch_count, sec_count, book_id))
    conn.commit()
    conn.close()

def update_chapter_info(chapter_id, section_count, total_words):
    """更新章节统计信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE chapters SET section_count = %s, total_words = %s WHERE id = %s',
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
        'INSERT INTO sections (book_id, chapter_id, section_number, content, title, word_count) VALUES (%s, %s, %s, %s, %s, %s)',
        (book_id, chapter_id, section_number, content, title, word_count)
    )
    section_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return section_id

def get_sections_by_book(book_id):
    """获取书籍的所有小节，包含章节编号和标题，以及 start_char/end_char"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, c.chapter_number, c.title as chapter_title 
        FROM sections s 
        LEFT JOIN chapters c ON s.chapter_id = c.id 
        WHERE s.book_id = %s 
        ORDER BY s.section_number
    ''', (book_id,))
    sections = [dict(row) for row in cursor.fetchall()]
    
    # 计算每节的 start_char 和 end_char（基于内容的累积长度）
    offset = 0
    for sec in sections:
        sec['start_char'] = offset
        sec['end_char'] = offset + len(sec['content']) if sec.get('content') else offset
        offset = sec['end_char']
    
    # 调试日志
    for sec in sections[:3]:
        print(f"[DB] Section {sec['id']}: start_char={sec['start_char']}, end_char={sec['end_char']}, content_len={len(sec.get('content',''))}")
    
    conn.close()
    return sections

def get_sections_by_chapter(chapter_id):
    """获取章节的所有小节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM sections WHERE chapter_id = %s ORDER BY section_number',
        (chapter_id,)
    )
    sections = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sections

def get_section(section_id):
    """获取单个小节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sections WHERE id = %s', (section_id,))
    section = cursor.fetchone()
    conn.close()
    return dict(section) if section else None

def update_section(section_id, title, content, summary):
    """更新小节"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET title = %s, content = %s, summary = %s WHERE id = %s',
        (title, content, summary, section_id)
    )
    conn.commit()
    conn.close()

def delete_section(section_id):
    """删除小节（同时删除关联的点评）"""
    conn = get_db()
    cursor = conn.cursor()
    # 删除关联的点评
    cursor.execute('DELETE FROM annotations WHERE section_id = %s', (section_id,))
    # 删除关联的节阅读状态
    cursor.execute('DELETE FROM section_reading_status WHERE section_id = %s', (section_id,))
    # 级联删除 text_segments 和 insert_points
    cursor.execute('DELETE FROM insert_points WHERE section_id = %s', (section_id,))
    cursor.execute('DELETE FROM text_segments WHERE section_id = %s', (section_id,))
    # 删除小节
    cursor.execute('DELETE FROM sections WHERE id = %s', (section_id,))
    conn.commit()
    conn.close()

def update_section_audio(section_id, audio_path):
    """更新小节的音频路径"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET audio_path = %s, has_audio = 1 WHERE id = %s',
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
            'UPDATE sections SET audio_path = %s, has_audio = 1, audio_duration = %s, char_timeline = %s WHERE id = %s',
            (audio_path, audio_duration, json.dumps(char_timeline), section_id)
        )
    else:
        cursor.execute(
            'UPDATE sections SET audio_duration = %s, char_timeline = %s WHERE id = %s',
            (audio_duration, json.dumps(char_timeline), section_id)
        )
    conn.commit()
    conn.close()

def get_section_audio_timeline(section_id):
    """获取小节的音频时间轴信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT audio_path, audio_duration, char_timeline FROM sections WHERE id = %s',
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
        'UPDATE sections SET audio_segments = %s WHERE id = %s',
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
        'SELECT audio_segments FROM sections WHERE id = %s',
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
        'UPDATE books SET tts_status = %s, tts_progress = %s WHERE id = %s',
        (status, progress, book_id)
    )
    conn.commit()
    conn.close()

def update_annotation_audio(annotation_id, audio_path, audio_duration):
    """更新点评的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE annotations SET audio_path = %s, audio_duration = %s WHERE id = %s',
        (audio_path, audio_duration, annotation_id)
    )
    conn.commit()
    conn.close()

def update_section_summary_audio(section_id, audio_path, audio_duration):
    """更新小节小结的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET summary_audio_path = %s, summary_audio_duration = %s WHERE id = %s',
        (audio_path, audio_duration, section_id)
    )
    conn.commit()
    conn.close()

def update_section_word_count(section_id, word_count):
    """更新小节字数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sections SET word_count = %s WHERE id = %s',
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
        '''REPLACE INTO reading_progress
           (user_id, book_id, current_section_id, current_position, audio_position, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s)''',
        (user_id, book_id, section_id, position, audio_position, datetime.now())
    )
    conn.commit()
    conn.close()

def get_progress(user_id, book_id):
    """获取阅读进度（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM reading_progress WHERE user_id = %s AND book_id = %s ORDER BY updated_at DESC LIMIT 1',
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
           VALUES (%s, %s, %s, %s, %s, %s)''',
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
        'SELECT * FROM annotations WHERE section_id = %s ORDER BY start_char',
        (section_id,)
    )
    annotations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return annotations

def delete_annotation(annotation_id):
    """删除点评点"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM annotations WHERE id = %s', (annotation_id,))
    conn.commit()
    conn.close()

# ==================== 节阅读状态相关操作 ====================

def set_section_status(user_id, book_id, section_id, status):
    """设置节阅读状态（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''REPLACE INTO section_reading_status
           (user_id, book_id, section_id, status, updated_at)
           VALUES (%s, %s, %s, %s, %s)''',
        (user_id, book_id, section_id, status, datetime.now())
    )
    conn.commit()
    conn.close()

def get_section_status(user_id, book_id, section_id):
    """获取节阅读状态（按用户隔离）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM section_reading_status WHERE user_id = %s AND book_id = %s AND section_id = %s',
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
        'SELECT * FROM section_reading_status WHERE user_id = %s AND book_id = %s',
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
    cursor.execute('SELECT COUNT(*) as total FROM sections WHERE book_id = %s', (book_id,))
    total = cursor.fetchone()['total']
    # 获取各状态数量
    cursor.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN status = 'unread' THEN 1 ELSE 0 END), 0) as unread,
            COALESCE(SUM(CASE WHEN status = 'reading' THEN 1 ELSE 0 END), 0) as reading,
            COALESCE(SUM(CASE WHEN status = 'read' THEN 1 ELSE 0 END), 0) as read_count
        FROM section_reading_status WHERE user_id = %s AND book_id = %s
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
        query += ' AND u.phone LIKE %s'
        params.append(f'%{phone}%')
    if role:
        query += ' AND u.role = %s'
        params.append(role)
    if gender:
        query += ' AND u.gender = %s'
        params.append(gender)
    if age_above is not None:
        query += ' AND u.age >= %s'
        params.append(int(age_above))
    if age_below is not None:
        query += ' AND u.age <= %s'
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
    cursor.execute('UPDATE books SET subscription_price = %s WHERE id = %s', (price, book_id))
    conn.commit()
    conn.close()


def _get_section_audio_stats(cursor, section_id):
    """获取某节的音频完成统计 (done, total)"""
    # text_segments
    cursor.execute('SELECT COUNT(*) as cnt FROM text_segments WHERE section_id = %s', (section_id,))
    seg_total = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM text_segments WHERE section_id = %s AND audio_path IS NOT NULL AND audio_path != ''", (section_id,))
    seg_done = cursor.fetchone()['cnt']
    # insert_points
    cursor.execute('SELECT COUNT(*) as cnt FROM insert_points WHERE section_id = %s', (section_id,))
    ip_total = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM insert_points WHERE section_id = %s AND audio_path IS NOT NULL AND audio_path != ''", (section_id,))
    ip_done = cursor.fetchone()['cnt']
    return seg_done + ip_done, seg_total + ip_total


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
            WHERE s.book_id = %s
            GROUP BY s.chapter_id
        ) sec_agg ON c.id = sec_agg.chapter_id
        WHERE c.book_id = %s
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
            WHERE s.chapter_id = %s
            ORDER BY s.section_number
        ''', (ch['id'],))
        sections = [dict(row) for row in cursor.fetchall()]
        # 为每个section添加音频统计
        for sec in sections:
            sec['audio_done'], sec['audio_total'] = _get_section_audio_stats(cursor, sec['id'])
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
        WHERE s.book_id = %s AND s.chapter_id IS NULL
        ORDER BY s.section_number
    ''', (book_id,))
    orphan_sections = [dict(row) for row in cursor.fetchall()]
    for sec in orphan_sections:
        sec['audio_done'], sec['audio_total'] = _get_section_audio_stats(cursor, sec['id'])

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
            WHERE srs.status = 'read' AND srs.user_id = %s
            GROUP BY srs.book_id
        ) read_stats ON b.id = read_stats.book_id
        LEFT JOIN (
            SELECT t.user_id, sec.book_id, COUNT(*) as thoughts_count
            FROM thoughts t
            JOIN sections sec ON t.section_id = sec.id
            WHERE t.user_id = %s
            GROUP BY sec.book_id
        ) thought_stats ON b.id = thought_stats.book_id
        WHERE sub.user_id = %s
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
        'INSERT IGNORE INTO subscriptions (user_id, book_id) VALUES (%s, %s)',
        (user_id, book_id)
    )
    conn.commit()
    conn.close()


def admin_remove_subscription(user_id, book_id):
    """管理员移除订阅"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM subscriptions WHERE user_id = %s AND book_id = %s',
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
    cursor.execute('SELECT content FROM sections WHERE id = %s', (section_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return 0
    content = row['content']
    
    # 去掉换行符，得到纯文本
    text = content.replace('\n', '')
    text_len = len(text)
    
    # 获取点评（按 start_char 排序）
    cursor.execute('SELECT id, start_char, end_char FROM annotations WHERE section_id = %s ORDER BY start_char', (section_id,))
    annotations = [dict(r) for r in cursor.fetchall()]
    
    # 确定分割点：在点评的 start_char 和 end_char 处切割（与 generate_segmented_audio 保持一致）
    # end_char 是不包含的边界（Python切片风格 [start, end)）
    split_points = sorted(set([0] + [ann['start_char'] for ann in annotations if ann.get('start_char') is not None] + [ann['end_char'] for ann in annotations if ann.get('end_char') is not None] + [text_len]))
    
    # 删除旧的 text_segments
    cursor.execute('DELETE FROM text_segments WHERE section_id = %s', (section_id,))
    
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
            'INSERT INTO text_segments (section_id, segment_number, content, start_char, end_char, word_count) VALUES (%s, %s, %s, %s, %s, %s)',
            (section_id, i, seg_content, start, end, word_count)
        )
    
    conn.commit()
    conn.close()
    return len(split_points) - 1

def get_text_segments(section_id):
    """获取一节的所有 text_segments，按 segment_number 排序"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM text_segments WHERE section_id = %s ORDER BY segment_number', (section_id,))
    segments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return segments

def get_text_segment(segment_id):
    """获取单个 text_segment"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM text_segments WHERE id = %s', (segment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_text_segment_audio(segment_id, audio_path, audio_duration, char_timeline):
    """更新段的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE text_segments SET audio_path = %s, audio_duration = %s, char_timeline = %s WHERE id = %s',
        (audio_path, audio_duration, char_timeline, segment_id)
    )
    conn.commit()
    conn.close()

def delete_text_segments_by_section(section_id):
    """删除一节的所有 text_segments"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM text_segments WHERE section_id = %s', (section_id,))
    conn.commit()
    conn.close()

# ==================== insert_points 相关操作 ====================

def create_insert_points(section_id):
    """根据 annotations 和 summary 创建 insert_points 记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取点评（包含 annotation_index）
    cursor.execute('SELECT id, annotation_index, start_char, end_char, original_text, comment, audio_path, audio_duration FROM annotations WHERE section_id = %s ORDER BY start_char', (section_id,))
    annotations = [dict(r) for r in cursor.fetchall()]
    
    # 获取小结
    cursor.execute('SELECT summary, summary_audio_path, summary_audio_duration FROM sections WHERE id = %s', (section_id,))
    sec_row = cursor.fetchone()
    summary = sec_row['summary'] if sec_row else None
    summary_audio_path = sec_row['summary_audio_path'] if sec_row else None
    summary_audio_duration = sec_row['summary_audio_duration'] if sec_row else 0
    
    # 获取 text_segments
    cursor.execute('SELECT id, end_char FROM text_segments WHERE section_id = %s ORDER BY segment_number', (section_id,))
    segments = [dict(r) for r in cursor.fetchall()]
    
    # 删除旧的 insert_points
    cursor.execute('DELETE FROM insert_points WHERE section_id = %s', (section_id,))
    
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
               VALUES (%s, %s, %s, 'annotation', %s, %s, %s, %s, %s, %s, %s, %s)''',
            (section_id, target_segment_id, ann['start_char'], ann['id'], ann.get('annotation_index'), ann['original_text'], ann['start_char'], ann['end_char'], ann['comment'], ann.get('audio_path'), ann.get('audio_duration', 0))
        )
    
    # 为 summary 创建 insert_point（绑定到最后一个段）
    if summary and segments:
        last_segment = segments[-1]
        cursor.execute(
            '''INSERT INTO insert_points (section_id, segment_id, point_order, point_type, comment, audio_path, audio_duration)
               VALUES (%s, %s, 999999, 'summary', %s, %s, %s)''',
            (section_id, last_segment['id'], summary, summary_audio_path, summary_audio_duration)
        )
    
    conn.commit()
    # 统计创建的 insert_points 数量
    cursor.execute('SELECT COUNT(*) as cnt FROM insert_points WHERE section_id = %s', (section_id,))
    count = cursor.fetchone()['cnt']
    conn.close()
    return count

def get_insert_points_by_section(section_id):
    """获取一节的所有 insert_points，按 segment 关联排序"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ip.*, ts.segment_number
        FROM insert_points ip
        JOIN text_segments ts ON ip.segment_id = ts.id
        WHERE ip.section_id = %s
        ORDER BY ts.segment_number, ip.point_order
    ''', (section_id,))
    points = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return points

def get_insert_points_by_segment(segment_id):
    """获取一个 text_segment 后的所有插入点"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM insert_points WHERE segment_id = %s ORDER BY point_order', (segment_id,))
    points = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return points

def update_insert_point_audio(insert_point_id, audio_path, audio_duration):
    """更新插入点的音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE insert_points SET audio_path = %s, audio_duration = %s WHERE id = %s',
        (audio_path, audio_duration, insert_point_id)
    )
    conn.commit()
    conn.close()

def update_insert_point_quote_audio(insert_point_id, quote_audio_path, quote_audio_duration):
    """更新插入点的引用音频信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE insert_points SET quote_audio_path = %s, quote_audio_duration = %s WHERE id = %s',
        (quote_audio_path, quote_audio_duration, insert_point_id)
    )
    conn.commit()
    conn.close()

def delete_insert_points_by_section(section_id):
    """删除一节的所有 insert_points"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM insert_points WHERE section_id = %s', (section_id,))
    conn.commit()
    conn.close()

# ==================== 播放计划 ====================

def get_section_playback_plan(section_id):
    """获取一节的完整播放计划：text_segments + insert_points 交错排列"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取所有 text_segments
    cursor.execute('SELECT * FROM text_segments WHERE section_id = %s ORDER BY segment_number', (section_id,))
    segments = [dict(row) for row in cursor.fetchall()]
    
    # 获取所有 insert_points
    cursor.execute('SELECT * FROM insert_points WHERE section_id = %s ORDER BY point_order', (section_id,))
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

def cleanup_duplicate_progress():
    """清理重复的断点记录，每个用户每本书只保留最新的一条"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 删除重复记录，只保留每个 user_id+book_id 组合的最新记录
        cursor.execute('''
            DELETE rp1 FROM reading_progress rp1
            INNER JOIN reading_progress rp2 
            WHERE rp1.user_id = rp2.user_id 
            AND rp1.book_id = rp2.book_id 
            AND rp1.id < rp2.id
        ''')
        deleted = cursor.rowcount
        conn.commit()
        print(f'[清理] 删除重复断点记录: {deleted} 条')
    except Exception as e:
        print(f'[清理] 清理重复断点记录失败: {e}')
    finally:
        conn.close()

def update_progress_v2(user_id, book_id, section_id, segment_id, text_position, audio_position):
    """新版断点保存：包含 segment_id，断点移动时将旧节标记为已读"""
    if not user_id:
        return  # 必须有用户ID
    conn = get_db()
    cursor = conn.cursor()
    # 查询之前的断点节
    cursor.execute(
        'SELECT current_section_id FROM reading_progress WHERE user_id = %s AND book_id = %s',
        (user_id, book_id)
    )
    old_row = cursor.fetchone()
    if old_row and old_row['current_section_id'] and old_row['current_section_id'] != section_id:
        # 断点移动到了新节，将旧节标记为已读
        old_section_id = old_row['current_section_id']
        cursor.execute(
            '''REPLACE INTO section_reading_status
               (user_id, book_id, section_id, status, updated_at)
               VALUES (%s, %s, %s, 'read', %s)''',
            (user_id, book_id, old_section_id, datetime.now())
        )
        # 同时将新节标记为在读
        cursor.execute(
            '''REPLACE INTO section_reading_status
               (user_id, book_id, section_id, status, updated_at)
               VALUES (%s, %s, %s, 'reading', %s)''',
            (user_id, book_id, section_id, datetime.now())
        )
    # 更新断点
    cursor.execute(
        '''REPLACE INTO reading_progress
           (user_id, book_id, current_section_id, current_segment_id, current_position, audio_position, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)''',
        (user_id, book_id, section_id, segment_id, text_position, audio_position, datetime.now())
    )
    conn.commit()
    conn.close()

def get_progress_v2(user_id, book_id):
    """新版断点读取"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM reading_progress WHERE user_id = %s AND book_id = %s ORDER BY updated_at DESC LIMIT 1',
        (user_id, book_id)
    )
    progress = cursor.fetchone()
    conn.close()
    return dict(progress) if progress else None

def check_section_audio_complete(section_id):
    """检查一节的所有 text_segments 和 insert_points 是否都有音频"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as cnt FROM text_segments WHERE section_id = %s AND audio_path IS NOT NULL AND audio_path != ""', (section_id,))
    seg_with_audio = cursor.fetchone()['cnt']
    
    cursor.execute('SELECT COUNT(*) as cnt FROM text_segments WHERE section_id = %s', (section_id,))
    seg_total = cursor.fetchone()['cnt']
    
    cursor.execute('SELECT COUNT(*) as cnt FROM insert_points WHERE section_id = %s AND audio_path IS NOT NULL AND audio_path != ""', (section_id,))
    ip_with_audio = cursor.fetchone()['cnt']
    
    cursor.execute('SELECT COUNT(*) as cnt FROM insert_points WHERE section_id = %s', (section_id,))
    ip_total = cursor.fetchone()['cnt']
    
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
        WHERE srs.user_id = %s AND srs.status = 'read'
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
        WHERE min_words <= %s
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
        WHERE rank_level = %s
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


# ===== 军功系统 =====

# 军功类型及阈值
MERIT_TYPES = ['一等功', '二等功', '三等功', '嘉奖']
MERIT_PRIORITY = {'一等功': 4, '二等功': 3, '三等功': 2, '嘉奖': 1}

def _determine_merit(thought_count, three_star_rate, two_star_rate, one_star_rate):
    """根据思考量和星级率判定军功类型"""
    # 一等功：3星率 >= 50%，思考量 >= 350
    if thought_count >= 350 and three_star_rate >= 0.5:
        return '一等功'
    # 二等功：2星率 >= 30%，思考量 >= 250
    if thought_count >= 250 and two_star_rate >= 0.3:
        return '二等功'
    # 三等功：1星率 >= 50%，思考量 >= 150
    if thought_count >= 150 and one_star_rate >= 0.5:
        return '三等功'
    # 嘉奖：思考量 >= 50
    if thought_count >= 50:
        return '嘉奖'
    return None

def check_and_award_merits(user_id):
    """
    检查并颁发军功章。
    每满50个已评分思考进行一次统计，按星级率判定军功类型。
    返回新颁发的军功列表。
    """
    conn = get_db()
    cursor = conn.cursor()

    # 获取用户所有已评分的思考
    cursor.execute('''
        SELECT ai_score FROM thoughts
        WHERE user_id = %s AND ai_score IS NOT NULL AND ai_score > 0
        ORDER BY id ASC
    ''', (user_id,))
    scored_thoughts = cursor.fetchall()

    if not scored_thoughts:
        conn.close()
        return []

    total_count = len(scored_thoughts)
    # 计算已统计到的最大批次
    max_batch = total_count // 50

    # 获取已颁发的最大批次
    cursor.execute('''
        SELECT merit_type, MAX(batch) as max_batch
        FROM user_merits WHERE user_id = %s
        GROUP BY merit_type
    ''', (user_id,))
    awarded = {}
    for row in cursor.fetchall():
        awarded[row['merit_type']] = row['max_batch']

    new_merits = []

    for batch in range(1, max_batch + 1):
        # 该批次包含第 (batch-1)*50+1 到 batch*50 个思考
        start_idx = (batch - 1) * 50
        end_idx = batch * 50
        batch_thoughts = scored_thoughts[start_idx:end_idx]
        batch_count = len(batch_thoughts)

        # 统计星级率
        three_stars = sum(1 for t in batch_thoughts if t['ai_score'] == 3)
        two_stars = sum(1 for t in batch_thoughts if t['ai_score'] == 2)
        one_stars = sum(1 for t in batch_thoughts if t['ai_score'] == 1)

        three_star_rate = three_stars / batch_count if batch_count > 0 else 0
        two_star_rate = (two_stars + three_stars) / batch_count if batch_count > 0 else 0  # 2星率包含2星和3星
        one_star_rate = (one_stars + two_stars + three_stars) / batch_count if batch_count > 0 else 0  # 1星率包含1、2、3星

        thought_count = batch * 50  # 该批次对应的累计思考量
        merit_type = _determine_merit(thought_count, three_star_rate, two_star_rate, one_star_rate)

        if merit_type and batch > awarded.get(merit_type, 0):
            try:
                cursor.execute('''
                    INSERT INTO user_merits (user_id, merit_type, batch, thought_count, three_star_rate, two_star_rate, one_star_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (user_id, merit_type, batch, thought_count, three_star_rate, two_star_rate, one_star_rate))
                new_merits.append({
                    'merit_type': merit_type,
                    'batch': batch,
                    'thought_count': thought_count,
                    'three_star_rate': round(three_star_rate * 100, 1),
                    'two_star_rate': round(two_star_rate * 100, 1),
                    'one_star_rate': round(one_star_rate * 100, 1),
                })
            except:
                pass  # 已存在则跳过

    conn.commit()
    conn.close()
    return new_merits


# ===== 勋章系统 =====

MEDAL_TYPES = [
    {'type': '红星勋章', 'min_three_stars': 100, 'icon': 'red_star'},
    {'type': '红旗勋章', 'min_three_stars': 200, 'icon': 'red_flag'},
    {'type': '八一勋章', 'min_three_stars': 300, 'icon': 'bayi'},
]

def check_and_award_medals(user_id):
    """
    检查并颁发勋章。
    按累积3星数达标则颁发对应勋章。
    返回新颁发的勋章列表。
    """
    conn = get_db()
    cursor = conn.cursor()

    # 获取用户累积3星数
    cursor.execute('''
        SELECT COUNT(*) as cnt FROM thoughts
        WHERE user_id = %s AND ai_score = 3
    ''', (user_id,))
    total_three_stars = cursor.fetchone()['cnt']

    # 获取已拥有的勋章
    cursor.execute('SELECT medal_type FROM user_medals WHERE user_id = %s', (user_id,))
    owned = set(row['medal_type'] for row in cursor.fetchall())

    new_medals = []

    for medal in MEDAL_TYPES:
        if medal['type'] not in owned and total_three_stars >= medal['min_three_stars']:
            try:
                cursor.execute('''
                    INSERT INTO user_medals (user_id, medal_type, total_three_stars)
                    VALUES (%s, %s, %s)
                ''', (user_id, medal['type'], total_three_stars))
                new_medals.append({
                    'medal_type': medal['type'],
                    'icon': medal['icon'],
                    'total_three_stars': total_three_stars,
                })
            except:
                pass

    conn.commit()
    conn.close()
    return new_medals


def get_user_merits(user_id):
    """获取用户所有军功章统计"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT merit_type, COUNT(*) as count
        FROM user_merits WHERE user_id = %s
        GROUP BY merit_type
    ''', (user_id,))
    result = {}
    for row in cursor.fetchall():
        result[row['merit_type']] = row['count']
    conn.close()
    return result


def get_user_medals(user_id):
    """获取用户所有勋章"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT medal_type, total_three_stars, awarded_at
        FROM user_medals WHERE user_id = %s
        ORDER BY awarded_at ASC
    ''', (user_id,))
    medals = []
    for row in cursor.fetchall():
        medals.append({
            'medal_type': row['medal_type'],
            'total_three_stars': row['total_three_stars'],
            'awarded_at': str(row['awarded_at']),
        })
    conn.close()
    return medals


if __name__ == '__main__':
    init_db()
