"""
合并服务器上已有的分段音频
用法：python3 merge_existing.py
"""
import os
import subprocess
import sys

AUDIO_DIR = 'audio_files'

def merge_section_files(section_id):
    """合并指定节的分段音频"""
    # 查找该节的所有分段文件
    pattern = f'section_{section_id}_'
    files = []
    for f in os.listdir(AUDIO_DIR):
        if f.startswith(pattern) and f.endswith('.mp3'):
            # 排除最终的 section_xxx.mp3
            if f == f'section_{section_id}.mp3':
                continue
            try:
                # 提取序号
                idx = int(f.replace(pattern, '').replace('.mp3', ''))
                files.append((idx, f))
            except:
                pass
    
    if not files:
        print(f"节 {section_id}: 没有找到分段文件")
        return False
    
    # 按序号排序
    files.sort(key=lambda x: x[0])
    print(f"节 {section_id}: 找到 {len(files)} 个分段文件")
    
    # 创建合并列表
    list_file = os.path.join(AUDIO_DIR, f'section_{section_id}_list.txt')
    with open(list_file, 'w') as f:
        for idx, fname in files:
            f.write(f"file '{fname}'\n")
    
    # 合并
    final_path = os.path.join(AUDIO_DIR, f'section_{section_id}.mp3')
    try:
        result = subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', list_file, '-c', 'copy', final_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=AUDIO_DIR)
        print(f"  ✅ 合并成功: {final_path}")
        
        # 删除临时文件
        for idx, fname in files:
            os.remove(os.path.join(AUDIO_DIR, fname))
        os.remove(list_file)
        
        return True
    except Exception as e:
        print(f"  ❌ 合并失败: {e}")
        return False

if __name__ == '__main__':
    # 合并 335, 336, 337
    for sid in [335, 336, 337]:
        merge_section_files(sid)
        print()
