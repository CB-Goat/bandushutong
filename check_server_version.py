"""
检查服务器上的代码版本
用法：python3 check_server_version.py
"""
import os

# 检查 text_parser.py 的关键修复是否应用
parser_path = 'backend/text_parser.py'
with open(parser_path, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('使用 doc.paragraphs 构建批注映射', 'for para_idx, para in enumerate(doc.paragraphs):'),
    ('para._element 访问 XML', 'para_element = para._element'),
    ('para_start_in_content 在拼接前计算', 'para_start_in_content = len(current_section[\'content\'])'),
]

print("=" * 60)
print("检查服务器代码版本")
print("=" * 60)

all_ok = True
for name, pattern in checks:
    if pattern in content:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} - 缺失!")
        all_ok = False

if all_ok:
    print("\n✅ 服务器代码是最新版本")
else:
    print("\n❌ 服务器代码不是最新版本，需要 git pull 并重启服务")

# 显示 git 状态
print("\n" + "-" * 60)
print("Git 状态:")
os.system('git log --oneline -3')
print()
os.system('git status --short')
