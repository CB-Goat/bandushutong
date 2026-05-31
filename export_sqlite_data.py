#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
悦读小将 - SQLite 数据导出脚本
从 SQLite 数据库导出数据并生成 MySQL INSERT 语句

使用方法:
    python export_sqlite_data.py [sqlite_db_path] [output_sql_path]

示例:
    python export_sqlite_data.py /path/to/reading_companion.db /path/to/output_data.sql
"""

import sqlite3
import sys
import os
from datetime import datetime


def escape_sql_string(value):
    """转义 SQL 字符串中的特殊字符"""
    if value is None:
        return 'NULL'
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    # 转义单引号
    value = str(value).replace("'", "''")
    # 转义反斜杠
    value = value.replace('\\', '\\\\')
    return f"'{value}'"


def format_value(value):
    """格式化值为 SQL 值"""
    if value is None:
        return 'NULL'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, bool):
        return '1' if value else '0'
    return escape_sql_string(value)


def get_table_columns(cursor, table_name):
    """获取表的列信息"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def export_table(cursor, table_name, output_file, batch_size=1000):
    """导出单个表的数据为 MySQL INSERT 语句"""
    # 获取列信息
    columns_info = get_table_columns(cursor, table_name)
    if not columns_info:
        print(f"  警告: 表 {table_name} 不存在或没有列")
        return 0

    column_names = [col[1] for col in columns_info]
    columns_str = ', '.join([f'`{col}`' for col in column_names])

    # 获取数据行数
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cursor.fetchone()[0]

    if total_rows == 0:
        print(f"  表 {table_name}: 0 行数据，跳过")
        return 0

    print(f"  表 {table_name}: {total_rows} 行数据")

    # 写入表注释
    output_file.write(f"\n-- --------------------------------------------------------\n")
    output_file.write(f"-- 导出表数据: {table_name}\n")
    output_file.write(f"-- --------------------------------------------------------\n")
    output_file.write(f"SET FOREIGN_KEY_CHECKS = 0;\n")

    # 分批获取数据
    cursor.execute(f"SELECT {', '.join(column_names)} FROM {table_name}")

    rows_exported = 0
    batch = []

    for row in cursor:
        values = [format_value(val) for val in row]
        batch.append(f"({', '.join(values)})")
        rows_exported += 1

        if len(batch) >= batch_size:
            # 写入批量 INSERT
            output_file.write(f"INSERT IGNORE INTO `{table_name}` ({columns_str}) VALUES\n")
            output_file.write(',\n'.join(batch))
            output_file.write(';\n')
            batch = []

    # 写入剩余的批次
    if batch:
        output_file.write(f"INSERT IGNORE INTO `{table_name}` ({columns_str}) VALUES\n")
        output_file.write(',\n'.join(batch))
        output_file.write(';\n')

    output_file.write(f"SET FOREIGN_KEY_CHECKS = 1;\n")

    return rows_exported


def export_all_tables(sqlite_db_path, output_sql_path):
    """导出所有表的数据"""
    # 连接 SQLite 数据库
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    # 过滤掉 SQLite 系统表
    tables = [t for t in tables if not t.startswith('sqlite_')]

    print(f"找到 {len(tables)} 个表: {', '.join(tables)}")

    # 定义表的导出顺序（处理外键依赖）
    # 先导出无依赖的表，再导出依赖其他表的表
    table_order = [
        # 无依赖的基础表
        'books',
        'users',
        'quotes',
        'military_ranks',
        # 依赖 books
        'chapters',
        # 依赖 books, chapters
        'sections',
        # 依赖 users, books
        'subscriptions',
        'subscription_requests',
        'reading_progress',
        'section_reading_status',
        'messages',
        'device_transfer_codes',
        # 依赖 sections
        'annotations',
        'thoughts',
        'text_segments',
        # 依赖 text_segments, annotations
        'insert_points',
        # 依赖 quotes, books, sections, users
        'quote_usage',
    ]

    # 按顺序排列表，未在顺序中的表放在最后
    ordered_tables = []
    for t in table_order:
        if t in tables:
            ordered_tables.append(t)
    for t in tables:
        if t not in ordered_tables:
            ordered_tables.append(t)

    # 打开输出文件
    with open(output_sql_path, 'w', encoding='utf-8') as output_file:
        # 写入文件头
        output_file.write("-- ========================================================\n")
        output_file.write("-- 悦读小将 - MySQL 数据导入脚本\n")
        output_file.write(f"-- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output_file.write(f"-- 源数据库: {sqlite_db_path}\n")
        output_file.write("-- ========================================================\n")
        output_file.write("\nSET NAMES utf8mb4;\n")

        total_rows = 0

        for table_name in ordered_tables:
            try:
                rows = export_table(cursor, table_name, output_file)
                total_rows += rows
            except Exception as e:
                print(f"  错误: 导出表 {table_name} 失败: {e}")

    conn.close()

    print(f"\n导出完成！共导出 {total_rows} 行数据到 {output_sql_path}")
    return total_rows


def main():
    # 获取命令行参数或使用默认值
    if len(sys.argv) > 1:
        sqlite_db_path = sys.argv[1]
    else:
        # 默认路径：与 database.py 同级目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sqlite_db_path = os.path.join(script_dir, '..', 'backend', 'reading_companion.db')
        sqlite_db_path = os.path.normpath(sqlite_db_path)

    if len(sys.argv) > 2:
        output_sql_path = sys.argv[2]
    else:
        output_sql_path = 'mysql_data.sql'

    # 检查源数据库是否存在
    if not os.path.exists(sqlite_db_path):
        print(f"错误: 数据库文件不存在: {sqlite_db_path}")
        print(f"用法: python {sys.argv[0]} [sqlite_db_path] [output_sql_path]")
        sys.exit(1)

    print(f"源数据库: {sqlite_db_path}")
    print(f"输出文件: {output_sql_path}")
    print("开始导出数据...\n")

    export_all_tables(sqlite_db_path, output_sql_path)


if __name__ == '__main__':
    main()
