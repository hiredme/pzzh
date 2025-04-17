import requests
import json

DEEPSEEK_API = {
    "API_URL": "https://api.deepseek.com/v1/chat/completions",
    "API_KEY": "sk-a2f0e3b8c0d14e929c5de8ad44a8effe",
    "TIMEOUT": 30,  # 请求超时时间
    "RETRIES": 3,  # 失败重试次数
}



def process_submission_task():

    # 获取待处理文本
    raw_text = """
My Pet

I have a lovely pet. It is a white cat. Her name is Snowball. She is two years old.

Snowball has soft fur and bright blue eyes. She likes to play with yarn balls. Every morning, she sits by my bed and meows softly. I give her milk and fish for breakfast. After school, we play together in the garden. Sometimes she climbs trees, but she always comes back to me.

I love Snowball very much. She is like a little sister to me. Taking care of her makes me happy!

"""

    # API调用处理
    api_response = call_deepseek_api(raw_text)
    processed_data = parse_deepseek_response(api_response)
    print(processed_data)
    return True


def call_deepseek_api(text):
    """执行带重试机制的API调用"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API['API_KEY']}",
        "Content-Type": "application/json",
    }
    text1 = """
你是一个经验丰富，态度严苛的英语作文批改机器，接下来你将处理一篇作文，请根据以下规定输出文字。
1.输出格式为json，格式如下：
{
"scores": {
"total_score": 数值,
"spelling": 数值,
"grammar": 数值,
"cohesion": 数值,
"vocabulary": 数值,
"comments": "综合评价文本，请使用中文"
},
"corrections": [
{
"error_type": "拼写错误/spelling | 语法错误/grammar | 搭配错误/collocation | 标点错误/punctuation",
"start_pos": 起始位置数字,
"end_pos": 结束位置数字,
"original_text": "错误文本片段",
"suggestion": "修改建议文本,请使用中文",
"confidence": 置信度浮点数
},
// 更多错误条目...
]
}

2.除了要求输出的json外，什么都不要输出。
3.回答之前请仔细检查：

错误类型必须使用英文键值（spelling/grammar/collocation/punctuation）

位置数字从0开始计数

confidence取值范围0.0-1.0

分数保留1位小数

确保所有字段名称与示例完全一致
4.示例输出结构：
{
"scores": {
"total_score": 85.5,
"spelling": 18.0,
"grammar": 22.5,
"cohesion": 20.0,
"vocabulary": 25.0,
"comments": "文章结构清晰，但需注意动词时态一致性..."
},
"corrections": [
{
"error_type": "grammar",
"start_pos": 45,
"end_pos": 52,
"original_text": "she go",
"suggestion": "修改为she goes",
"confidence": 0.98
},
{
"error_type": "punctuation",
"start_pos": 78,
"end_pos": 79,
"original_text": ",",
"suggestion": "修改为.",
"confidence": 1.0
}
]
}
"""

    payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": text1},
        {"role": "user", "content": text}

    ],
    "temperature": 0.5,
    "response_format": {"type": "json_object"}
    }
    response = requests.post(
        DEEPSEEK_API["API_URL"],
        headers=headers,
        json=payload,
        timeout=DEEPSEEK_API.get("TIMEOUT", 30),
    )
    response.raise_for_status()
    json_response = response.json()
    return json_response



import json
from decimal import Decimal

def parse_deepseek_response(api_data):
    """
    解析Deepseek API响应数据，提取结构化批改结果
    :param api_data: API返回的原始数据（字典格式）
    :return: 包含格式化scores和corrections的字典
    """
    try:
        # 提取JSON响应内容
        content_str = api_data['choices'][0]['message']['content']
        result = json.loads(content_str)
        
        # 初始化返回结构
        parsed_data = {
            'scores': None,
            'corrections': []
        }

        # 解析分数部分
        if 'scores' in result:
            scores = result['scores']
            parsed_data['scores'] = {
                'total_score': Decimal(str(scores['total_score'])).quantize(Decimal('0.0')),
                'spelling': Decimal(str(scores['spelling'])).quantize(Decimal('0.0')),
                'grammar': Decimal(str(scores['grammar'])).quantize(Decimal('0.0')),
                'cohesion': Decimal(str(scores['cohesion'])).quantize(Decimal('0.0')),
                'vocabulary': Decimal(str(scores['vocabulary'])).quantize(Decimal('0.0')),
                'comments': scores['comments']
            }

        # 解析批改详情
        if 'corrections' in result:
            for correction in result['corrections']:
                parsed_data['corrections'].append({
                    'error_type': correction['error_type'],
                    'start_pos': int(correction['start_pos']),
                    'end_pos': int(correction['end_pos']),
                    'original_text': correction['original_text'],
                    'suggestion': correction['suggestion'],
                    'confidence': float(correction['confidence'])
                })

        return parsed_data

    except KeyError as e:
        raise ValueError(f"缺少必要字段: {str(e)}") from e
    except json.JSONDecodeError as e:
        raise ValueError("无效的JSON格式") from e
    except Exception as e:
        raise RuntimeError(f"解析失败: {str(e)}") from e



process_submission_task()
