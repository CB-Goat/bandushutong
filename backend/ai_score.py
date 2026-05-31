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
    对思考进行 AI 评分（规则评分，作为降级方案）
    """
    if not thought_content or not thought_content.strip():
        return 0, "思考内容为空"
    
    if not original_text or not original_text.strip():
        return 1, "缺少引用原文"
    
    score, reason = _rule_based_evaluation(original_text, thought_content, section_content)
    return score, reason


def _rule_based_evaluation(original_text, thought_content, section_content):
    """基于规则的评分逻辑（降级方案）"""
    original_lower = original_text.lower()
    thought_lower = thought_content.lower()
    
    if len(thought_content.strip()) < 5:
        return 1, "思考内容过短"
    
    if len(thought_content.strip()) > 200:
        return 2, "思考内容较长，有一定深度"
    
    thinking_keywords = [
        '觉得', '认为', '想象', '感受', '如果', '可能', '也许',
        '为什么', '怎么', '是否', '可是', '但是', '然而',
        '因为', '所以', '虽然', '于是', '让我', '说明',
        '看出', '想到', '体会到', '发现', '推测'
    ]
    
    thinking_count = sum(1 for kw in thinking_keywords if kw in thought_lower)
    
    overlap_ratio = _calculate_overlap(original_lower, thought_lower)
    if overlap_ratio > 0.7:
        return 1, "思考内容重复原文较多，缺乏独立思考"
    
    depth_keywords = [
        '深刻', '理解', '感悟', '启发', '道理', '意义', '价值',
        '品质', '性格', '心理', '成长', '变化', '关系', '对比',
        '联想', '延伸', '反思', '总结', '概括', '提炼'
    ]
    
    depth_count = sum(1 for kw in depth_keywords if kw in thought_lower)
    
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
    set1 = set(text1)
    set2 = set(text2)
    if not set1 or not set2:
        return 0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    if union == 0:
        return 0
    return intersection / union


def _call_glm_flash(original_text, thought_content, api_key,
                    book_name='', author='', chapter_title='', section_title='', section_content=''):
    """
    调用智谱 GLM-4.7-Flash API 进行评分（免费）
    """
    import requests
    
    # 构建上下文信息
    context_info = f"书名：《{book_name}》"
    if author:
        context_info += f"，作者：{author}"
    if chapter_title:
        context_info += f"，所属章节：{chapter_title}"
    if section_title:
        context_info += f"，当前节：{section_title}"
    
    # 截取节内容（避免过长）
    section_excerpt = ''
    if section_content:
        if len(section_content) > 1500:
            section_excerpt = section_content[:1500] + '...'
        else:
            section_excerpt = section_content
    
    prompt = f"""你是一位资深的文学评论家和阅读指导专家。请对一位读者的阅读思考进行专业评审。

## 背景信息
{context_info}

## 当前节内容
{section_excerpt}

## 读者引用的原文
"{original_text}"

## 读者的思考
"{thought_content}"

## 评审要求
请结合以下维度进行评审：
1. **准确性**：思考是否正确理解了原文的含义
2. **贴合度**：思考是否与书籍的主题思想、作者的创作背景相贴合
3. **思考深度**：思考是否有独到见解，是否展现了深层次的理解和感悟

## 评分标准
- 0分：不正确，和文章内容不符
- 1分：基本正确，符合文章内容
- 2分：正确且有一定深度
- 3分：正确且很有深度，对文章理解深刻

请严格按以下JSON格式返回（不要包含其他文字）：
{{"score": 0-3的整数, "reason": "简短的评审意见（30字以内）"}}"""

    print(f"[AI评分] 调用GLM API: model=glm-4.7-flash, prompt长度={len(prompt)}")
    
    # 添加重试机制（针对429限流）
    max_retries = 3
    retry_delay = 1  # 秒
    
    for attempt in range(max_retries):
        response = requests.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json={
                'model': 'glm-4.7-flash',
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.3
            },
            timeout=30
        )
        
        print(f"[AI评分] GLM API 响应状态: {response.status_code} (尝试 {attempt + 1}/{max_retries})")
        
        if response.status_code != 429:
            break  # 不是限流错误，跳出重试
        
        if attempt < max_retries - 1:
            print(f"[AI评分] 遇到限流(429)，{retry_delay}秒后重试...")
            import time
            time.sleep(retry_delay)
            retry_delay *= 2  # 指数退避
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        print(f"[AI评分] GLM API 返回内容: {content[:200]}...")
        
        # 尝试解析 JSON
        try:
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                data = json.loads(json_match.group())
                score = int(data.get('score', 1))
                reason = data.get('reason', 'AI 评分')
                score = max(0, min(3, score))
                print(f"[AI评分] JSON解析成功: score={score}, reason={reason}")
                return score, reason
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[AI评分] JSON解析失败: {e}")
            pass
        
        # 降级：提取数字
        match = re.search(r'[0123]', content)
        if match:
            score = int(match.group())
            print(f"[AI评分] 提取数字成功: score={score}")
            return score, "AI 评分"
    else:
        print(f"[AI评分] GLM API 错误响应: {response.text[:200]}")
    
    raise Exception(f"GLM API 返回错误: status={response.status_code}")


def _call_doubao(original_text, thought_content, api_key,
                 book_name='', author='', chapter_title='', section_title='', section_content=''):
    """
    调用豆包 Doubao-Seed-2.0-mini API 进行评分（备用，使用requests直接调用）
    """
    import requests
    
    # 构建上下文信息
    context_info = f"书名：《{book_name}》"
    if author:
        context_info += f"，作者：{author}"
    if chapter_title:
        context_info += f"，所属章节：{chapter_title}"
    if section_title:
        context_info += f"，当前节：{section_title}"
    
    # 截取节内容（避免过长）
    section_excerpt = ''
    if section_content:
        if len(section_content) > 1500:
            section_excerpt = section_content[:1500] + '...'
        else:
            section_excerpt = section_content
    
    prompt = f"""你是一位资深的文学评论家和阅读指导专家。请对一位读者的阅读思考进行专业评审。

## 背景信息
{context_info}

## 当前节内容
{section_excerpt}

## 读者引用的原文
"{original_text}"

## 读者的思考
"{thought_content}"

## 评审要求
请结合以下维度进行评审：
1. **准确性**：思考是否正确理解了原文的含义
2. **贴合度**：思考是否与书籍的主题思想、作者的创作背景相贴合
3. **思考深度**：思考是否有独到见解，是否展现了深层次的理解和感悟

## 评分标准
- 0分：不正确，和文章内容不符
- 1分：基本正确，符合文章内容
- 2分：正确且有一定深度
- 3分：正确且很有深度，对文章理解深刻

请严格按以下JSON格式返回（不要包含其他文字）：
{{"score": 0-3的整数, "reason": "简短的评审意见（30字以内）"}}"""

    print(f"[AI评分] 调用豆包 API: model=doubao-seed-2-0-mini-260428")
    
    response = requests.post(
        'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        },
        json={
            'model': 'doubao-seed-2-0-mini-260428',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3
        },
        timeout=30
    )
    
    print(f"[AI评分] 豆包 API 响应状态: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        print(f"[AI评分] 豆包 API 返回内容: {content[:200]}...")
        
        # 尝试解析 JSON
        try:
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                data = json.loads(json_match.group())
                score = int(data.get('score', 1))
                reason = data.get('reason', 'AI 评分')
                score = max(0, min(3, score))
                print(f"[AI评分] 豆包 JSON解析成功: score={score}, reason={reason}")
                return score, reason
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[AI评分] 豆包 JSON解析失败: {e}")
        
        # 降级：提取数字
        match = re.search(r'[0123]', content)
        if match:
            score = int(match.group())
            print(f"[AI评分] 豆包 提取数字成功: score={score}")
            return score, "AI 评分"
    else:
        print(f"[AI评分] 豆包 API 错误响应: {response.text[:200]}")
    
    raise Exception(f"豆包 API 返回错误: status={response.status_code}")


def call_ai_api(original_text, thought_content, section_content=None,
                book_name='', author='', chapter_title='', section_title=''):
    """
    调用 AI API 进行评分（优先GLM，失败则尝试豆包，最后降级规则评分）
    """
    glm_api_key = os.environ.get('GLM_API_KEY', '')
    doubao_api_key = os.environ.get('ARK_API_KEY', '')
    
    # 调试日志：检查 API Key 配置
    print(f"[AI评分] GLM_API_KEY 配置状态: {'已配置' if glm_api_key else '未配置'}")
    print(f"[AI评分] ARK_API_KEY(豆包) 配置状态: {'已配置' if doubao_api_key else '未配置'}")
    
    # 1. 尝试 GLM
    if glm_api_key:
        try:
            print(f"[AI评分] 开始调用 GLM-4.7-Flash API...")
            score, reason = _call_glm_flash(
                original_text, thought_content, glm_api_key,
                book_name=book_name, author=author,
                chapter_title=chapter_title, section_title=section_title,
                section_content=section_content or ''
            )
            print(f"[AI评分] GLM-4.7-Flash 评分成功: {score}分 - {reason}")
            return score, reason
        except Exception as e:
            print(f"[AI评分] GLM API 调用失败: {type(e).__name__}: {e}")
    else:
        print(f"[AI评分] GLM_API_KEY 未配置，跳过 GLM")
    
    # 2. GLM 失败，尝试豆包
    if doubao_api_key:
        try:
            print(f"[AI评分] GLM 失败，尝试调用豆包 API...")
            score, reason = _call_doubao(
                original_text, thought_content, doubao_api_key,
                book_name=book_name, author=author,
                chapter_title=chapter_title, section_title=section_title,
                section_content=section_content or ''
            )
            print(f"[AI评分] 豆包评分成功: {score}分 - {reason}")
            return score, reason
        except Exception as e:
            print(f"[AI评分] 豆包 API 调用失败: {type(e).__name__}: {e}")
    else:
        print(f"[AI评分] ARK_API_KEY 未配置，跳过豆包")
    
    # 3. 所有AI API都失败，返回 None（等待修复机制处理）
    print(f"[AI评分] 所有AI API都失败，返回无结果")
    return None, None


def rate_thought(original_text, thought_content, section_content=None,
                 book_name='', author='', chapter_title='', section_title=''):
    """
    对思考进行评分（主入口）
    尝试使用 AI API，失败则返回 None
    """
    try:
        score, reason = call_ai_api(
            original_text, thought_content, section_content,
            book_name=book_name, author=author,
            chapter_title=chapter_title, section_title=section_title
        )
        return score, reason
    except Exception as e:
        print(f"[AI评分] 评分异常: {e}")
        return None, None
