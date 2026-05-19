# -*- coding: utf-8 -*-
"""
数据迁移脚本：将现有数据迁移到 text_segments + insert_points 架构
用法：cd /opt/bandushutong && python3 backend/migrate_to_segments.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import get_db, create_text_segments, create_insert_points, update_text_segment_audio, update_insert_point_audio, get_text_segments

def migrate():
    conn = get_db()
    cursor = conn.cursor()

    # 获取所有有内容的节
    cursor.execute('SELECT id, content FROM sections WHERE content IS NOT NULL AND content != ""')
    sections = cursor.fetchall()

    print(f"共 {len(sections)} 个节需要迁移")

    migrated = 0
    skipped = 0

    for sec in sections:
        section_id = sec['id']
        content = sec['content']

        if not content or len(content.strip()) == 0:
            skipped += 1
            continue

        try:
            # 1. 创建 text_segments
            seg_count = create_text_segments(section_id)

            # 2. 创建 insert_points
            create_insert_points(section_id)

            # 3. 迁移现有音频文件
            segments = get_text_segments(section_id)

            # 检查是否有旧的 audio_segments JSON
            cursor.execute('SELECT audio_segments FROM sections WHERE id = ?', (section_id,))
            sec_row = cursor.fetchone()
            old_segments_json = sec_row['audio_segments'] if sec_row else None

            if old_segments_json:
                import json
                try:
                    old_segments = json.loads(old_segments_json)
                    # 旧的 audio_segments 是混合了 original 和 annotation 的数组
                    original_idx = 0
                    for old_seg in old_segments:
                        if old_seg.get('type') == 'original' and original_idx < len(segments):
                            seg = segments[original_idx]
                            if old_seg.get('audio_path') and old_seg.get('audio_duration'):
                                update_text_segment_audio(
                                    seg['id'],
                                    old_seg['audio_path'],
                                    old_seg['audio_duration'],
                                    json.dumps(old_seg['char_timeline']) if old_seg.get('char_timeline') else None
                                )
                            original_idx += 1
                except (json.JSONDecodeError, Exception) as e:
                    print(f"  节 {section_id}: 解析旧音频段失败: {e}")

            # 4. 迁移点评音频
            cursor.execute('''
                SELECT ip.id, a.audio_path, a.audio_duration
                FROM insert_points ip
                JOIN annotations a ON ip.annotation_id = a.id
                WHERE ip.section_id = ? AND ip.point_type = 'annotation'
            ''', (section_id,))
            ann_audio_rows = cursor.fetchall()
            for row in ann_audio_rows:
                if row['audio_path'] and row['audio_duration']:
                    update_insert_point_audio(row['id'], row['audio_path'], row['audio_duration'])

            # 5. 迁移小结音频
            cursor.execute('''
                SELECT ip.id, s.summary_audio_path, s.summary_audio_duration
                FROM insert_points ip
                JOIN sections s ON ip.section_id = s.id
                WHERE ip.section_id = ? AND ip.point_type = 'summary'
            ''', (section_id,))
            summary_audio_rows = cursor.fetchall()
            for row in summary_audio_rows:
                if row['summary_audio_path'] and row['summary_audio_duration']:
                    update_insert_point_audio(row['id'], row['summary_audio_path'], row['summary_audio_duration'])

            migrated += 1
            print(f"节 {section_id}: 迁移完成 ({seg_count} 个文本段)")

        except Exception as e:
            print(f"节 {section_id}: 迁移失败: {e}")
            import traceback
            traceback.print_exc()

    conn.close()
    print(f"\n迁移完成: {migrated} 成功, {skipped} 跳过")

if __name__ == '__main__':
    migrate()
