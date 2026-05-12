"""
检查实际音频文件是否存在
用法：python3 check_files.py
"""
import os

print("=" * 50)
print("检查实际音频文件")
print("=" * 50)

# 检查这些文件是否存在
files_to_check = [
    'audio_files/section_335.mp3',
    'audio_files/section_336.mp3',
    'audio_files/section_337.mp3',
]

for f in files_to_check:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"✅ {f}: {size} bytes")
    else:
        print(f"❌ {f}: 不存在")

# 列出 audio_files 目录中的相关文件
print("\n" + "-" * 50)
print("audio_files 目录中的 section_335* 文件:")
if os.path.exists('audio_files'):
    files = os.listdir('audio_files')
    for f in sorted(files):
        if '335' in f or '336' in f or '337' in f:
            path = os.path.join('audio_files', f)
            size = os.path.getsize(path)
            print(f"  {f}: {size} bytes")

print("\n" + "=" * 50)
