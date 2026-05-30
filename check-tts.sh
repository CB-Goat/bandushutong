#!/bin/bash
# 检查TTS配置

echo "=== 检查百度TTS环境变量 ==="
docker exec reading-companion-backend python3 -c "
import os
app_id = os.environ.get('BAIDU_TTS_APP_ID', '')
api_key = os.environ.get('BAIDU_TTS_API_KEY', '')
secret = os.environ.get('BAIDU_TTS_SECRET_KEY', '')
print(f'APP_ID: {app_id[:10]}...' if app_id else 'APP_ID: 未设置')
print(f'API_KEY: {api_key[:10]}...' if api_key else 'API_KEY: 未设置')
print(f'SECRET_KEY: {secret[:10]}...' if secret else 'SECRET_KEY: 未设置')
print(f'\n配置状态: {\"已配置\" if app_id and api_key and secret else \"未配置\"}')"

echo ""
echo "=== 检查TTS日志 ==="
docker-compose logs --tail=100 backend | grep -iE "tts|baidu|百度|语音|合成"

echo ""
echo "=== 测试TTS API ==="
docker exec reading-companion-backend python3 -c "
import sys
sys.path.insert(0, '/app/backend')
from baidu_tts import is_configured
print(f'百度TTS配置状态: {is_configured()}')"
