import os
from flask import Blueprint, request, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from cache_utils import rate_limit_consume
from models import User
from request_utils import request_client_ip

# 创建 AI 专属蓝图
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")
AI_CHAT_RATE_LIMIT_MAX_REQUESTS = 12
AI_CHAT_RATE_LIMIT_WINDOW_SECONDS = 60


def as_int(v):
    """安全地把输入转成整数。"""
    try:
        return int(v)
    except Exception:
        return None


def current_user():
    """按 JWT 身份读取当前有效用户。"""
    uid = as_int(get_jwt_identity())
    if not uid:
        return None
    user = User.query.get(uid)
    if not user or user.status != "active":
        return None
    return user


def ai_chat_rate_limit_key(user_id: int, ip: str):
    """按用户和来源 IP 组合生成 AI 对话限流键。"""
    normalized_ip = (ip or "").strip() or "unknown"
    return f"rate:ai-chat:{user_id}:{normalized_ip}"

# [前端对应]: 左侧 AI 助教抽屉 (AiChatSidebar.vue) -> 发送问题并接收流式回复
# [业务逻辑]: 校验登录和请求频率后，转发到大模型并以 SSE 持续回传分片内容
@ai_bp.post("/chat")
@jwt_required()
def ai_chat():
    """转发 AI 对话请求，并以 SSE 流式返回回复。"""
    user = current_user()
    body = request.get_json(silent=True) or {}
    user_message = body.get("message", "").strip()
    # 动态获取前端选择的模型，默认退回给 Qwen/Qwen2.5-7B-Instruct
    model_name = body.get("model", "Qwen/Qwen2.5-7B-Instruct").strip()

    if not user_message:
        return {"code": 400, "message": "消息不能为空", "data": None}, 400

    def err(message="error", status=400):
        return {"code": status, "message": message, "data": None}, status

    if not user:
        return err("请先登录", status=401)

    limit_state = rate_limit_consume(
        ai_chat_rate_limit_key(user.id, request_client_ip()),
        AI_CHAT_RATE_LIMIT_MAX_REQUESTS,
        AI_CHAT_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not limit_state["allowed"]:
        return err(
            f"AI 请求过于频繁，请{limit_state['retry_after']}秒后再试",
            status=429,
        )


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
        """持续产出模型返回的流式分片。"""
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
