#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新军衔等级数据
"""

import sys
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'reading_companion.db')

def update_ranks():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空旧数据
    cursor.execute('DELETE FROM military_ranks')
    
    # 插入新数据（带正确的 icon 标识）
    ranks = [
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
    ]
    
    cursor.executemany('''
        INSERT INTO military_ranks (rank_name, rank_level, min_words, title, icon)
        VALUES (?, ?, ?, ?, ?)
    ''', ranks)
    
    conn.commit()
    
    # 验证
    cursor.execute('SELECT rank_name, icon FROM military_ranks ORDER BY rank_level')
    print("军衔数据已更新:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()

if __name__ == '__main__':
    update_ranks()
