import json
import os

from flask import Blueprint, Response, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from cache_utils import rate_limit_consume
from models import User
from request_utils import request_client_ip

# AI 聊天接口蓝图
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")
AI_CHAT_RATE_LIMIT_MAX_REQUESTS = 12
AI_CHAT_RATE_LIMIT_WINDOW_SECONDS = 60

DEFAULT_AI_SYSTEM_PROMPT = (
    "你是在线学习平台的 AI 学习助手。请使用简洁、自然、专业的中文回答，"
    "优先给出可执行建议，不要编造系统中不存在的数据。"
)

ANALYSIS_AI_SYSTEM_PROMPT = (
    "你是在线学习平台的 AI 分析助手。后端会提供一份精简分析上下文 JSON，"
    "请严格基于这份 JSON 做分析，不要虚构数据库中不存在的数据。"
    "请按以下结构组织回答："
    "1. 当前状态判断；"
    "2. 最值得优先处理的问题或机会；"
    "3. 3 条可执行建议。"
    "语气保持自然、清晰，像站内智能助手。"
)


def as_int(value):
    """安全转换整数，失败时返回 None。"""
    try:
        return int(value)
    except Exception:
        return None


def current_user():
    """根据 JWT 中的用户 ID 读取当前用户。"""
    uid = as_int(get_jwt_identity())
    if not uid:
        return None
    user = User.query.get(uid)
    if not user or user.status != "active":
        return None
    return user


def ai_chat_rate_limit_key(user_id: int, ip: str):
    """按用户和真实客户端 IP 生成 AI 聊天限流键。"""
    normalized_ip = (ip or "").strip() or "unknown"
    return f"rate:ai-chat:{user_id}:{normalized_ip}"


def err(message="error", status=400):
    return {"code": status, "message": message, "data": None}, status


def build_analysis_context_messages(analysis_context, analysis_scene: str):
    """将后端整理好的精简分析上下文拼成模型可读消息。"""
    if not isinstance(analysis_context, dict) or not analysis_context:
        return []

    role = str(analysis_context.get("role") or "").strip()
    role_label = {
        "student": "学生学习分析",
        "teacher": "教师教学分析",
        "admin": "管理员运营分析",
    }.get(role, "站内智能分析")

    messages = [{"role": "system", "content": ANALYSIS_AI_SYSTEM_PROMPT}]

    if analysis_scene:
        messages.append(
            {
                "role": "system",
                "content": f"当前触发场景：{analysis_scene}",
            }
        )

    messages.append(
        {
            "role": "system",
            "content": (
                f"{role_label}上下文 JSON："
                f"{json.dumps(analysis_context, ensure_ascii=False)}"
            ),
        }
    )

    page_context = analysis_context.get("page_context") or {}
    if page_context.get("scope") == "course-detail" and page_context.get("course_title"):
        messages.append(
            {
                "role": "system",
                "content": (
                    f"本次分析请优先围绕当前课程《{page_context['course_title']}》展开，"
                    "先判断这门课当前最值得处理的问题，再给出面向当前角色的建议。"
                ),
            }
        )
    return messages


@ai_bp.post("/chat")
@jwt_required()
def ai_chat():
    """AI 聊天接口，支持普通问答和基于上下文的深度分析。"""
    user = current_user()
    body = request.get_json(silent=True) or {}
    user_message = str(body.get("message") or "").strip()
    model_name = str(body.get("model") or "Qwen/Qwen2.5-7B-Instruct").strip()
    analysis_context = body.get("analysis_context")
    analysis_scene = str(body.get("analysis_scene") or "").strip()

    if not user_message:
        return err("请输入消息内容", status=400)

    if not user:
        return err("登录状态无效", status=401)

    limit_state = rate_limit_consume(
        ai_chat_rate_limit_key(user.id, request_client_ip()),
        AI_CHAT_RATE_LIMIT_MAX_REQUESTS,
        AI_CHAT_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not limit_state["allowed"]:
        return err(
            f"AI 请求过于频繁，请在 {limit_state['retry_after']} 秒后再试",
            status=429,
        )

    api_key = os.getenv("SILICON_API_KEY")
    if not api_key:
        return err("当前系统未完成 AI 服务配置，请联系管理员", status=500)

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")

    messages = [{"role": "system", "content": DEFAULT_AI_SYSTEM_PROMPT}]
    messages.extend(build_analysis_context_messages(analysis_context, analysis_scene))
    messages.append({"role": "user", "content": user_message})

    def generate_stream():
        """以 SSE 流式返回大模型输出。"""
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                max_tokens=1000,
                temperature=0.7,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate_stream()),
        content_type="text/event-stream",
    )
