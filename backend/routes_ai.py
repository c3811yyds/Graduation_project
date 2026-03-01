import os
from flask import Blueprint, request, Response, stream_with_context
from extensions import jwt
from flask_jwt_extended import jwt_required, get_jwt_identity
import json

# 创建 AI 专属蓝图
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

@ai_bp.post("/chat")
@jwt_required()
def ai_chat():
    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}
    user_message = body.get("message", "").strip()
    # 动态获取前端选择的模型，默认退回给 Qwen/Qwen2.5-7B-Instruct
    model_name = body.get("model", "Qwen/Qwen2.5-7B-Instruct").strip()

    if not user_message:
        return {"code": 400, "message": "消息不能为空", "data": None}, 400

    api_key = os.getenv("SILICON_API_KEY")

    if not api_key:
        return {"code": 500, "message": "服务端未配置 AI API Key", "data": None}, 500

    # 引入 OpenAI SDK
    from openai import OpenAI
    
    # 实例化连接硅基流动API客户端
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1"
    )

    # 设定系统 Prompt，规定 AI 的角色身份
    messages = [
        {"role": "system", "content": "你是一个智能学习网站的随堂助教助手。你的名字叫“智学小助”。请用温和、简洁且专业的语气回答学生关于各个学科的问题，也可以偶尔用表情符号。"},
        {"role": "user", "content": user_message}
    ]

    def generate_stream():
        try:
            # 开启流式请求
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                max_tokens=1000,
                temperature=0.7
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # 组装 Server-Sent Events (SSE) 格式的数据
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            # 结束标志
            yield "data: [DONE]\n\n"
        except Exception as e:
            # 返回错误到流中
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    # 以 SSE 流数据格式回应给前台
    return Response(stream_with_context(generate_stream()), content_type='text/event-stream')