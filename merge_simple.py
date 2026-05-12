"""
使用更简单的方式合并音频
用法：python3 merge_simple.py
"""
import os
import subprocess
import sys

AUDIO_DIR = 'audio_files'

def merge_with_cat(section_id):
    """使用 cat 命令合并（MP3格式可以直接拼接）"""
    pattern = f'section_{section_id}_'
    files = []
    for f in os.listdir(AUDIO_DIR):
        if f.startswith(pattern) and f.endswith('.mp3'):
            if f == f'section_{section_id}.mp3':
                continue
            try:
                idx = int(f.replace(pattern, '').replace('.mp3', ''))
                files.append((idx, f))
            except:
                pass
    
    if not files:
        print(f"节 {section_id}: 没有找到分段文件")
        return False
    
    files.sort(key=lambda x: x[0])
    print(f"节 {section_id}: 找到 {len(files)} 个分段文件")
    
    # 使用 cat 命令合并 MP3
    final_path = os.path.join(AUDIO_DIR, f'section_{section_id}.mp3')
    
    # 构建文件列表
    file_paths = [os.path.join(AUDIO_DIR, f[1]) for f in files]
    
    try:
        # 使用 cat 合并
        with open(final_path, 'wb') as outfile:
            for fp in file_paths:
                with open(fp, 'rb') as infile:
                    outfile.write(infile.read())
        
        print(f"  ✅ 合并成功 (cat): {final_path}")
        
        # 删除临时文件
        for fp in file_paths:
            os.remove(fp)
        
        # 删除 list 文件（如果存在）
        list_file = os.path.join(AUDIO_DIR, f'section_{section_id}_list.txt')
        if os.path.exists(list_file):
            os.remove(list_file)
        
        return True
    except Exception as e:
        print(f"  ❌ 合并失败: {e}")
        return False

if __name__ == '__main__':
    for sid in [335, 336, 337]:
        merge_with_cat(sid)
        print()
