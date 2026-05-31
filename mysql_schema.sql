-- ========================================================
-- 悦读小将 - MySQL 数据库建表脚本
-- 从 SQLite 迁移到 MySQL
-- ========================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- --------------------------------------------------------
-- 表结构：books（书籍表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `books`;
CREATE TABLE `books` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(500) NOT NULL COMMENT '书名',
  `author` VARCHAR(200) DEFAULT NULL COMMENT '作者',
  `author_nationality` VARCHAR(100) DEFAULT NULL COMMENT '作者国籍',
  `version` VARCHAR(100) DEFAULT NULL COMMENT '版本',
  `file_path` VARCHAR(500) DEFAULT NULL COMMENT '文件路径',
  `total_sections` INT DEFAULT 0 COMMENT '总小节数',
  `total_chapters` INT DEFAULT 0 COMMENT '总章节数',
  `voice_type` VARCHAR(20) DEFAULT 'male' COMMENT '语音类型：male/female',
  `tts_status` VARCHAR(50) DEFAULT 'none' COMMENT 'TTS状态：none/pending/generating/done/error',
  `tts_progress` VARCHAR(50) DEFAULT '' COMMENT 'TTS进度，如 "5/30"',
  `subscription_price` DECIMAL(10,2) DEFAULT 0 COMMENT '订阅价格',
  `is_public` TINYINT DEFAULT 0 COMMENT '是否公开：0-否，1-是',
  `icon_path` VARCHAR(500) DEFAULT NULL COMMENT '图标路径',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_books_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='书籍表';

-- --------------------------------------------------------
-- 表结构：chapters（章节表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `chapters`;
CREATE TABLE `chapters` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `book_id` INT NOT NULL COMMENT '所属书籍ID',
  `chapter_number` INT NOT NULL COMMENT '章节编号',
  `title` VARCHAR(500) DEFAULT NULL COMMENT '章节标题',
  `section_count` INT DEFAULT 0 COMMENT '小节数量',
  `total_words` INT DEFAULT 0 COMMENT '总字数',
  PRIMARY KEY (`id`),
  KEY `idx_chapters_book_id` (`book_id`),
  KEY `idx_chapters_number` (`book_id`, `chapter_number`),
  CONSTRAINT `fk_chapters_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='章节表';

-- --------------------------------------------------------
-- 表结构：sections（小节表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `sections`;
CREATE TABLE `sections` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `book_id` INT NOT NULL COMMENT '所属书籍ID',
  `chapter_id` INT DEFAULT NULL COMMENT '所属章节ID',
  `section_number` INT NOT NULL COMMENT '小节编号',
  `title` VARCHAR(500) DEFAULT NULL COMMENT '小节标题',
  `content` LONGTEXT NOT NULL COMMENT '内容',
  `audio_path` VARCHAR(500) DEFAULT NULL COMMENT '音频路径',
  `has_audio` TINYINT DEFAULT 0 COMMENT '是否有音频：0-否，1-是',
  `audio_duration` DECIMAL(10,2) DEFAULT 0 COMMENT '音频时长（秒）',
  `char_timeline` LONGTEXT DEFAULT NULL COMMENT '字符时间轴JSON',
  `word_count` INT DEFAULT 0 COMMENT '字数',
  `summary` LONGTEXT DEFAULT NULL COMMENT '小结',
  `summary_audio_path` VARCHAR(500) DEFAULT NULL COMMENT '小结音频路径',
  `summary_audio_duration` DECIMAL(10,2) DEFAULT 0 COMMENT '小结音频时长',
  `audio_segments` LONGTEXT DEFAULT NULL COMMENT '分段音频信息JSON',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_sections_book_id` (`book_id`),
  KEY `idx_sections_chapter_id` (`chapter_id`),
  KEY `idx_sections_number` (`book_id`, `section_number`),
  CONSTRAINT `fk_sections_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sections_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `chapters` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='小节表';

-- --------------------------------------------------------
-- 表结构：reading_progress（阅读进度表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `reading_progress`;
CREATE TABLE `reading_progress` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '用户ID',
  `book_id` INT NOT NULL COMMENT '书籍ID',
  `current_section_id` INT DEFAULT NULL COMMENT '当前小节ID',
  `current_segment_id` INT DEFAULT NULL COMMENT '当前段落ID',
  `current_position` INT DEFAULT 0 COMMENT '当前位置',
  `audio_position` DECIMAL(10,2) DEFAULT 0 COMMENT '音频位置',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_progress_user_book` (`user_id`, `book_id`),
  KEY `idx_progress_book_id` (`book_id`),
  KEY `idx_progress_section_id` (`current_section_id`),
  CONSTRAINT `fk_progress_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_progress_section` FOREIGN KEY (`current_section_id`) REFERENCES `sections` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='阅读进度表';

-- --------------------------------------------------------
-- 表结构：annotations（点评点表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `annotations`;
CREATE TABLE `annotations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `section_id` INT NOT NULL COMMENT '所属小节ID',
  `annotation_index` INT DEFAULT NULL COMMENT '点评索引',
  `start_char` INT NOT NULL COMMENT '开始字符位置',
  `end_char` INT NOT NULL COMMENT '结束字符位置',
  `original_text` LONGTEXT NOT NULL COMMENT '原文',
  `comment` LONGTEXT NOT NULL COMMENT '点评内容',
  `audio_path` VARCHAR(500) DEFAULT NULL COMMENT '音频路径',
  `audio_duration` DECIMAL(10,2) DEFAULT 0 COMMENT '音频时长',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_annotations_section_id` (`section_id`),
  KEY `idx_annotations_start_char` (`section_id`, `start_char`),
  CONSTRAINT `fk_annotations_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='点评点表';

-- --------------------------------------------------------
-- 表结构：section_reading_status（节阅读状态表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `section_reading_status`;
CREATE TABLE `section_reading_status` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT DEFAULT NULL COMMENT '用户ID',
  `book_id` INT NOT NULL COMMENT '书籍ID',
  `section_id` INT NOT NULL COMMENT '小节ID',
  `status` VARCHAR(50) DEFAULT 'unread' COMMENT '状态：unread/reading/read',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_status_user_book_section` (`user_id`, `book_id`, `section_id`),
  KEY `idx_status_book_id` (`book_id`),
  KEY `idx_status_section_id` (`section_id`),
  CONSTRAINT `fk_status_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_status_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='节阅读状态表';

-- --------------------------------------------------------
-- 表结构：users（用户表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `password` VARCHAR(255) DEFAULT NULL COMMENT '密码',
  `wechat_openid` VARCHAR(100) DEFAULT NULL COMMENT '微信OpenID',
  `wechat_nickname` VARCHAR(200) DEFAULT NULL COMMENT '微信昵称',
  `wechat_avatar` VARCHAR(500) DEFAULT NULL COMMENT '微信头像',
  `device_id` VARCHAR(200) DEFAULT NULL COMMENT '设备ID',
  `device_info` VARCHAR(500) DEFAULT NULL COMMENT '设备信息',
  `gender` VARCHAR(20) DEFAULT NULL COMMENT '性别',
  `age` INT DEFAULT NULL COMMENT '年龄',
  `grade` VARCHAR(50) DEFAULT NULL COMMENT '年级',
  `role` VARCHAR(50) DEFAULT 'user' COMMENT '角色：user/admin',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_users_phone` (`phone`),
  UNIQUE KEY `idx_users_wechat` (`wechat_openid`),
  KEY `idx_users_role` (`role`),
  KEY `idx_users_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- --------------------------------------------------------
-- 表结构：messages（用户留言表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `messages`;
CREATE TABLE `messages` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '用户ID',
  `content` LONGTEXT NOT NULL COMMENT '留言内容',
  `admin_reply` LONGTEXT DEFAULT NULL COMMENT '管理员回复',
  `is_read` TINYINT DEFAULT 0 COMMENT '是否已读：0-否，1-是',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `replied_at` TIMESTAMP NULL DEFAULT NULL COMMENT '回复时间',
  PRIMARY KEY (`id`),
  KEY `idx_messages_user_id` (`user_id`),
  KEY `idx_messages_created_at` (`created_at`),
  CONSTRAINT `fk_messages_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户留言表';

-- --------------------------------------------------------
-- 表结构：device_transfer_codes（换机校验码表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `device_transfer_codes`;
CREATE TABLE `device_transfer_codes` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '用户ID',
  `transfer_code` VARCHAR(20) NOT NULL COMMENT '校验码',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_transfer_user_id` (`user_id`),
  KEY `idx_transfer_code` (`transfer_code`),
  CONSTRAINT `fk_transfer_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='换机校验码表';

-- --------------------------------------------------------
-- 表结构：subscriptions（订阅表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `subscriptions`;
CREATE TABLE `subscriptions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '用户ID',
  `book_id` INT NOT NULL COMMENT '书籍ID',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_subscription_user_book` (`user_id`, `book_id`),
  KEY `idx_subscription_book_id` (`book_id`),
  CONSTRAINT `fk_subscription_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_subscription_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订阅表';

-- --------------------------------------------------------
-- 表结构：subscription_requests（订阅申请表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `subscription_requests`;
CREATE TABLE `subscription_requests` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '用户ID',
  `book_id` INT NOT NULL COMMENT '书籍ID',
  `status` VARCHAR(50) DEFAULT 'pending' COMMENT '状态：pending/approved/rejected',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_subreq_user_id` (`user_id`),
  KEY `idx_subreq_book_id` (`book_id`),
  KEY `idx_subreq_status` (`status`),
  CONSTRAINT `fk_subreq_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_subreq_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订阅申请表';

-- --------------------------------------------------------
-- 表结构：thoughts（思考表 - 用户个人点评）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `thoughts`;
CREATE TABLE `thoughts` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '用户ID',
  `section_id` INT NOT NULL COMMENT '小节ID',
  `start_char` INT NOT NULL COMMENT '开始字符位置',
  `end_char` INT NOT NULL COMMENT '结束字符位置',
  `original_text` LONGTEXT NOT NULL COMMENT '原文',
  `content` LONGTEXT NOT NULL COMMENT '思考内容',
  `ai_score` INT DEFAULT NULL COMMENT 'AI评分',
  `score_reason` LONGTEXT DEFAULT NULL COMMENT '评分理由',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_thoughts_user_id` (`user_id`),
  KEY `idx_thoughts_section_id` (`section_id`),
  KEY `idx_thoughts_user_section` (`user_id`, `section_id`),
  CONSTRAINT `fk_thoughts_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_thoughts_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='思考表';

-- --------------------------------------------------------
-- 表结构：quotes（名言表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `quotes`;
CREATE TABLE `quotes` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `content` LONGTEXT NOT NULL COMMENT '名言内容',
  `author` VARCHAR(200) DEFAULT NULL COMMENT '作者',
  `source` VARCHAR(500) DEFAULT NULL COMMENT '出处',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_quotes_author` (`author`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='名言表';

-- --------------------------------------------------------
-- 表结构：quote_usage（名言使用记录表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `quote_usage`;
CREATE TABLE `quote_usage` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `quote_id` INT NOT NULL COMMENT '名言ID',
  `book_id` INT NOT NULL COMMENT '书籍ID',
  `section_id` INT NOT NULL COMMENT '小节ID',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `used_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '使用时间',
  PRIMARY KEY (`id`),
  KEY `idx_quote_usage_quote_id` (`quote_id`),
  KEY `idx_quote_usage_book_id` (`book_id`),
  KEY `idx_quote_usage_section_id` (`section_id`),
  KEY `idx_quote_usage_user_id` (`user_id`),
  CONSTRAINT `fk_quote_usage_quote` FOREIGN KEY (`quote_id`) REFERENCES `quotes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_quote_usage_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_quote_usage_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_quote_usage_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='名言使用记录表';

-- --------------------------------------------------------
-- 表结构：text_segments（文本段表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `text_segments`;
CREATE TABLE `text_segments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `section_id` INT NOT NULL COMMENT '所属小节ID',
  `segment_number` INT NOT NULL COMMENT '段落编号',
  `content` LONGTEXT NOT NULL COMMENT '内容',
  `start_char` INT NOT NULL COMMENT '开始字符位置',
  `end_char` INT NOT NULL COMMENT '结束字符位置',
  `word_count` INT DEFAULT 0 COMMENT '字数',
  `audio_path` VARCHAR(500) DEFAULT NULL COMMENT '音频路径',
  `audio_duration` DECIMAL(10,2) DEFAULT 0 COMMENT '音频时长',
  `char_timeline` LONGTEXT DEFAULT NULL COMMENT '字符时间轴JSON',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_text_segments_section_number` (`section_id`, `segment_number`),
  KEY `idx_text_segments_section_id` (`section_id`),
  CONSTRAINT `fk_text_segments_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文本段表';

-- --------------------------------------------------------
-- 表结构：insert_points（插入点表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `insert_points`;
CREATE TABLE `insert_points` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `section_id` INT NOT NULL COMMENT '所属小节ID',
  `segment_id` INT NOT NULL COMMENT '所属段落ID',
  `point_order` INT NOT NULL COMMENT '插入顺序',
  `point_type` VARCHAR(50) NOT NULL COMMENT '类型：annotation/summary',
  `annotation_id` INT DEFAULT NULL COMMENT '点评ID',
  `annotation_index` INT DEFAULT NULL COMMENT '点评索引',
  `quote_text` LONGTEXT DEFAULT NULL COMMENT '引用文本',
  `quote_start_char` INT DEFAULT NULL COMMENT '引用开始位置',
  `quote_end_char` INT DEFAULT NULL COMMENT '引用结束位置',
  `comment` LONGTEXT NOT NULL COMMENT '点评/小结内容',
  `audio_path` VARCHAR(500) DEFAULT NULL COMMENT '音频路径',
  `audio_duration` DECIMAL(10,2) DEFAULT 0 COMMENT '音频时长',
  `quote_audio_path` VARCHAR(500) DEFAULT NULL COMMENT '引用音频路径',
  `quote_audio_duration` DECIMAL(10,2) DEFAULT 0 COMMENT '引用音频时长',
  `char_timeline` LONGTEXT DEFAULT NULL COMMENT '字符时间轴JSON',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_insert_points_section_id` (`section_id`),
  KEY `idx_insert_points_segment_id` (`segment_id`),
  KEY `idx_insert_points_annotation_id` (`annotation_id`),
  CONSTRAINT `fk_insert_points_section` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_insert_points_segment` FOREIGN KEY (`segment_id`) REFERENCES `text_segments` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_insert_points_annotation` FOREIGN KEY (`annotation_id`) REFERENCES `annotations` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='插入点表';

-- --------------------------------------------------------
-- 表结构：military_ranks（军衔等级配置表）
-- --------------------------------------------------------
DROP TABLE IF EXISTS `military_ranks`;
CREATE TABLE `military_ranks` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `rank_name` VARCHAR(100) NOT NULL COMMENT '军衔名称',
  `rank_level` INT NOT NULL COMMENT '等级',
  `min_words` INT NOT NULL COMMENT '所需最少字数',
  `title` VARCHAR(200) NOT NULL COMMENT '称号',
  `icon` VARCHAR(100) NOT NULL COMMENT '图标',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_military_ranks_level` (`rank_level`),
  KEY `idx_military_ranks_min_words` (`min_words`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='军衔等级配置表';

-- --------------------------------------------------------
-- 初始化军衔等级数据
-- --------------------------------------------------------
INSERT INTO `military_ranks` (`rank_name`, `rank_level`, `min_words`, `title`, `icon`) VALUES
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
('元帅', 20, 5000000, '阅读之神', 'marshal');

SET FOREIGN_KEY_CHECKS = 1;
