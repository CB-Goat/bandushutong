#!/bin/bash
# 更新前端代码脚本

cd /opt/bandushutong 2>/dev/null || cd /root/bandushutong 2>/dev/null || cd /home/bandushutong 2>/dev/null || cd $(dirname $0)

echo "当前目录: $(pwd)"

# 拉取最新代码
echo "拉取最新代码..."
git pull

# 检查 player_new.js 是否存在
if [ ! -f "frontend/player_new.js" ]; then
    echo "错误: frontend/player_new.js 不存在"
    exit 1
fi

# 替换播放器代码
echo "替换播放器代码..."
python3 << 'PYEOF'
import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('frontend/player_new.js', 'r', encoding='utf-8') as f:
    new_player = f.read()

# 替换时间轴播放器部分
pattern = r'// ===== 时间轴播放器.*?(?=\n\s*// ===== 点评编辑器 =====)'
replacement = new_player.rstrip()
html_new = re.sub(pattern, replacement, html, flags=re.DOTALL)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html_new)

print("替换完成")

# 验证
with open('frontend/index.html', 'r') as f:
    content = f.read()
    
if '_contentCharToDisplayChar' in content:
    print("✓ _contentCharToDisplayChar 已添加")
else:
    print("✗ _contentCharToDisplayChar 未找到")
    
if 'console.log' in content and '_highlightAnnotation' in content:
    print("✓ 调试日志已添加")
else:
    print("✗ 调试日志未找到")
PYEOF

# 重启服务
echo "重启服务..."
kill $(ps aux | grep 'python3 -c from backend.main' | grep -v grep | awk '{print $2}') 2>/dev/null
nohup python3 -c "from backend.main import app; app.run(host='0.0.0.0', port=8080)" > server.log 2>&1 &

echo "服务已重启"
echo "等待服务启动..."
sleep 3

# 验证
echo "验证更新..."
curl -s http://localhost:8080/ | grep -c "_contentCharToDisplayChar" && echo "✓ 前端代码已更新" || echo "✗ 前端代码更新失败"
