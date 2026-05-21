# -*- coding: utf-8 -*-
"""
AI 评分服务
用于对用户思考进行 AI 评分
"""

import os
import json
import re

# AI 评分标准：
# 0分：不正确，和文章内容不符
# 1分：基本正确，符合文章内容
# 2分：正确且有一定深度
# 3分：正确且很有深度，对文章理解深刻

def evaluate_thought(original_text, thought_content, section_content=None):
    """
    对思考进行 AI 评分
    
    参数：
    - original_text: 思考引用的原文
    - thought_content: 思考内容
    - section_content: 完整的小节内容（可选，用于更准确的评分）
    
    返回：
    - score: 0-3 的评分
    - reason: 评分理由
    """
    
    # 检查思考内容是否为空
    if not thought_content or not thought_content.strip():
        return 0, "思考内容为空"
    
    # 检查思考是否引用了原文
    if not original_text or not original_text.strip():
        return 1, "缺少引用原文"
    
    # 简单的规则评分
    score, reason = _rule_based_evaluation(original_text, thought_content, section_content)
    
    return score, reason


def _rule_based_evaluation(original_text, thought_content, section_content):
    """
    基于规则的评分逻辑
    """
    original_lower = original_text.lower()
    thought_lower = thought_content.lower()
    
    # 长度检查
    if len(thought_content.strip()) < 5:
        return 1, "思考内容过短"
    
    if len(thought_content.strip()) > 200:
        return 2, "思考内容较长，有一定深度"
    
    # 检查是否包含思考关键词
    thinking_keywords = [
        '觉得', '认为', '想象', '感受', '如果', '可能', '也许',
        '为什么', '怎么', '是否', '可是', '但是', '然而',
        '因为', '所以', '虽然', '于是', '让我', '说明',
        '看出', '想到', '体会到', '发现', '推测'
    ]
    
    thinking_count = sum(1 for kw in thinking_keywords if kw in thought_lower)
    
    # 检查是否重复原文（不好）
    overlap_ratio = _calculate_overlap(original_lower, thought_lower)
    if overlap_ratio > 0.7:
        return 1, "思考内容重复原文较多，缺乏独立思考"
    
    # 深度关键词
    depth_keywords = [
        '深刻', '理解', '感悟', '启发', '道理', '意义', '价值',
        '品质', '性格', '心理', '成长', '变化', '关系', '对比',
        '联想', '延伸', '反思', '总结', '概括', '提炼'
    ]
    
    depth_count = sum(1 for kw in depth_keywords if kw in thought_lower)
    
    # 评分逻辑
    if thinking_count >= 3 and depth_count >= 2:
        return 3, "思考深刻，有独到见解"
    elif thinking_count >= 2 and depth_count >= 1:
        return 2, "思考正确，有一定深度"
    elif thinking_count >= 1:
        return 1, "思考基本正确"
    else:
        return 1, "思考较为简单"


def _calculate_overlap(text1, text2):
    """计算两个文本的重叠度"""
    if not text1 or not text2:
        return 0
    
    # 简单的字符集重叠
    set1 = set(text1)
    set2 = set(text2)
    
    if not set1 or not set2:
        return 0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 0
    
    return intersection / union


def call_ai_api(original_text, thought_content, section_content=None):
    """
    调用外部 AI API 进行评分（预留接口）
    
    目前使用规则评分，后续可扩展为真正的 AI 评分
    """
    # 优先使用规则评分（简单快速）
    score, reason = evaluate_thought(original_text, thought_content, section_content)
    
    # 如果配置了 AI API，可以在这里调用
    # 例如：DeepSeek、OpenAI 等
    deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    
    if deepseek_api_key:
        try:
            score, reason = _call_deepseek(original_text, thought_content, deepseek_api_key)
        except Exception as e:
            print(f"[AI评分] DeepSeek API 调用失败: {e}")
    
    return score, reason


def _call_deepseek(original_text, thought_content, api_key):
    """
    调用 DeepSeek API 进行评分
    """
    import requests
    
    prompt = f"""请对以下阅读思考进行评分（0-3分）：

原文：{original_text}

思考：{thought_content}

评分标准：
- 0分：不正确，和文章内容不符
- 1分：基本正确，符合文章内容
- 2分：正确且有一定深度
- 3分：正确且很有深度，对文章理解深刻

请只返回一个数字（0、1、2 或 3），不要其他文字。"""
    
    response = requests.post(
        'https://api.deepseek.com/chat/completions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        },
        json={
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.1
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # 提取数字
        match = re.search(r'[0123]', content)
        if match:
            score = int(match.group())
            return score, "AI 评分"
    
    raise Exception("API 返回格式错误")


def rate_thought(original_text, thought_content, section_content=None):
    """
    对思考进行评分（主入口）
    尝试使用 AI API，失败则使用规则评分
    """
    try:
        score, reason = call_ai_api(original_text, thought_content, section_content)
        return score, reason
    except Exception as e:
        print(f"[AI评分] 评分失败，使用规则评分: {e}")
        return evaluate_thought(original_text, thought_content, section_content)
