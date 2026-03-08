from __future__ import annotations

from datetime import datetime, timedelta
import os
import uuid

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from extensions import db
from models import (
    Course,
    Enrollment,
    Review,
    TeacherInviteCode,
    User,
)
from cache_utils import cache_delete, cache_get_json, cache_set_json

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def ok(data=None, message="ok", code=0, status=200):
    """返回统一成功响应。"""
    return jsonify({"code": code, "message": message, "data": data}), status


def err(message="error", code=1, status=400, data=None):
    """返回统一错误响应。"""
    return jsonify({"code": code, "message": message, "data": data}), status


def now():
    """返回当前 UTC 时间。"""
    return datetime.utcnow()


def as_int(v):
    """安全地把输入转成整数。"""
    try:
        return int(v)
    except Exception:
        return None


def role_of(user: User | None):
    """读取用户角色并统一为小写。"""
    return ((user.role if user else "") or "").strip().lower()


def is_admin(user: User | None):
    """判断用户是否为管理员。"""
    return role_of(user) == "admin"


def current_user():
    """按 JWT 身份读取当前有效用户。"""
    uid = as_int(get_jwt_identity())
    if not uid:
        return None
    user = User.query.get(uid)
    if not user or user.status != "active":
        return None
    return user


def require_admin():
    """校验当前请求是否来自管理员。"""
    user = current_user()
    if not user:
        return None, err("请先登录", status=401)
    if not is_admin(user):
        return None, err("仅管理员可访问", status=403)
    return user, None


def iso(value):
    """把时间对象序列化为 ISO 字符串。"""
    return value.isoformat() if value else None


def serialize_user(user: User):
    """序列化用户基础信息。"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "created_at": iso(user.created_at),
    }


def serialize_invite(code: TeacherInviteCode):
    """序列化管理员邀请码列表项。"""
    creator = User.query.get(code.created_by_id) if code.created_by_id else None
    used_by = User.query.get(code.used_by_id) if code.used_by_id else None
    return {
        "id": code.id,
        "code": code.code,
        "is_used": bool(code.is_used),
        "expires_at": iso(code.expires_at),
        "is_expired": bool(code.expires_at and code.expires_at < now()),
        "created_by_name": creator.username if creator else "",
        "used_by_name": used_by.username if used_by else "",
    }


def admin_overview_cache_key():
    """返回管理员概览统计缓存键。"""
    return "admin:overview"


def admin_analytics_cache_key():
    """返回管理员数据总览缓存键。"""
    return "admin:analytics"


def invalidate_admin_overview_cache():
    """管理员修改账号状态或邀请码后，清理首页统计卡片缓存。"""
    cache_delete(admin_overview_cache_key())


def bootstrap_admin_account():
    """按环境变量自动创建或提升管理员账号。"""
    # 如果邮箱已存在，只执行提权和激活，不重置原密码。
    admin_email = (os.getenv("ADMIN_INIT_EMAIL") or "").strip()
    admin_username = (os.getenv("ADMIN_INIT_USERNAME") or "admin").strip() or "admin"
    admin_password = os.getenv("ADMIN_INIT_PASSWORD") or ""

    if not admin_email:
        return

    user = User.query.filter_by(email=admin_email).first()
    if user:
        changed = False
        if user.role != "admin":
            user.role = "admin"
            changed = True
        if user.status != "active":
            user.status = "active"
            changed = True
        if changed:
            user.updated_at = now()
            db.session.commit()
        return

    if len(admin_password) < 6:
        return

    username = admin_username
    suffix = 1
    while User.query.filter_by(username=username).first():
        username = f"{admin_username}{suffix}"
        suffix += 1

    user = User(
        username=username,
        email=admin_email,
        password_hash=generate_password_hash(admin_password),
        role="admin",
        status="active",
        created_at=now(),
        updated_at=now(),
    )
    db.session.add(user)
    db.session.commit()


# [前端对应]: 管理员后台首页 (AdminView.vue) -> 顶部统计卡片
# [业务逻辑]: 返回账号总数、启用停用状态、角色分布和可用邀请码等首页卡片数据
@admin_bp.get("/overview")
@jwt_required()
def admin_overview():
    """返回管理员首页概览统计。"""
    _, denied = require_admin()
    if denied:
        return denied

    cache_key = admin_overview_cache_key()
    cached = cache_get_json(cache_key)
    if cached is not None:
        return ok(cached)

    data = {
        "user_count": User.query.count(),
        "active_user_count": User.query.filter_by(status="active").count(),
        "disabled_user_count": User.query.filter_by(status="disabled").count(),
        "admin_count": User.query.filter_by(role="admin").count(),
        "teacher_count": User.query.filter_by(role="teacher").count(),
        "student_count": User.query.filter_by(role="student").count(),
        "unused_invite_count": TeacherInviteCode.query.filter_by(is_used=False).filter(
            TeacherInviteCode.expires_at >= now()
        ).count(),
    }
    cache_set_json(cache_key, data, ttl_seconds=60)
    return ok(data)


# [前端对应]: 数据总览页 (DashboardView.vue) -> 管理员视角的全课程统计图表
# [业务逻辑]: 汇总已发布课程的选课人数和综合评分，供管理员查看全站课程走势
@admin_bp.get("/analytics")
@jwt_required()
def admin_analytics():
    """返回管理员的数据总览图表数据。"""
    _, denied = require_admin()
    if denied:
        return denied

    cache_key = admin_analytics_cache_key()
    cached = cache_get_json(cache_key)
    if cached is not None:
        return ok(cached)

    courses = Course.query.filter_by(status="published").all()
    course_names = []
    course_ids = []
    enroll_counts = []
    review_averages = []
    for course in courses:
        course_names.append(course.title)
        course_ids.append(course.id)

        enroll_count = Enrollment.query.filter_by(course_id=course.id).count()
        enroll_counts.append(enroll_count)

        reviews = Review.query.filter_by(course_id=course.id).all()
        avg_rating = sum(review.rating for review in reviews) / len(reviews) if reviews else 0
        review_averages.append(round(avg_rating, 1))

    data = {
        "role": "admin",
        "courseNames": course_names,
        "courseIds": course_ids,
        "enrollCounts": enroll_counts,
        "reviewAverages": review_averages,
    }
    cache_set_json(cache_key, data, ttl_seconds=60)
    return ok(data)


# [前端对应]: 管理员后台 (AdminView.vue) -> “账号管理” 标签页列表
# [业务逻辑]: 支持按关键词、角色、状态分页筛选账号
@admin_bp.get("/users")
@jwt_required()
def admin_list_users():
    """按分页和筛选条件返回用户列表。"""
    _, denied = require_admin()
    if denied:
        return denied

    page = as_int(request.args.get("page")) or 1
    page_size = as_int(request.args.get("page_size")) or 10
    keyword = (request.args.get("keyword") or "").strip()
    role = (request.args.get("role") or "").strip().lower()
    status = (request.args.get("status") or "").strip().lower()

    page = max(1, page)
    page_size = max(5, min(page_size, 50))

    query = User.query

    if keyword:
        like_keyword = f"%{keyword}%"
        query = query.filter(
            or_(
                User.username.like(like_keyword),
                User.email.like(like_keyword),
            )
        )

    if role in {"admin", "teacher", "student"}:
        query = query.filter(User.role == role)

    if status in {"active", "disabled"}:
        query = query.filter(User.status == status)

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    page = min(page, total_pages)

    users = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ok(
        {
            "items": [serialize_user(user) for user in users],
            "pagination": {
                "page": page,
                "total": total,
                "total_pages": total_pages,
            },
        }
    )


# [前端对应]: 管理员后台 (AdminView.vue) -> 账号列表中的“启用/停用”按钮
# [业务逻辑]: 切换账号状态，并阻止管理员停用自己或停用最后一个启用中的管理员
@admin_bp.patch("/users/<int:user_id>/status")
@jwt_required()
def admin_update_user_status(user_id):
    """更新指定用户的启用或停用状态。"""
    admin_user, denied = require_admin()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    new_status = (body.get("status") or "").strip().lower()
    if new_status not in {"active", "disabled"}:
        return err("status 仅支持 active 或 disabled")

    target = User.query.get(user_id)
    if not target:
        return err("用户不存在", status=404)

    if target.id == admin_user.id and new_status != "active":
        return err("不能停用当前管理员账号", status=400)

    if target.role == "admin" and new_status != "active":
        active_admin_count = User.query.filter_by(role="admin", status="active").count()
        if active_admin_count <= 1:
            return err("至少保留一个启用中的管理员", status=400)

    target.status = new_status
    target.updated_at = now()
    db.session.commit()
    invalidate_admin_overview_cache()
    return ok(serialize_user(target), "账号状态已更新")


# [前端对应]: 管理员后台 (AdminView.vue) -> “教师邀请码” 标签页列表
# [业务逻辑]: 按状态、邀请码、创建人、使用人关键词分页筛选教师邀请码
@admin_bp.get("/invite-codes")
@jwt_required()
def admin_list_invite_codes():
    """分页读取邀请码列表，并支持状态与关键词筛选。"""
    _, denied = require_admin()
    if denied:
        return denied

    page = as_int(request.args.get("page")) or 1
    page_size = as_int(request.args.get("page_size")) or 10
    keyword = (request.args.get("keyword") or "").strip()
    status = (request.args.get("status") or "").strip().lower()

    page = max(1, page)
    page_size = max(5, min(page_size, 50))

    query = TeacherInviteCode.query

    if status == "used":
        query = query.filter(TeacherInviteCode.is_used.is_(True))
    elif status == "unused":
        query = query.filter(TeacherInviteCode.is_used.is_(False))
    elif status == "active":
        query = query.filter(
            TeacherInviteCode.is_used.is_(False),
            TeacherInviteCode.expires_at >= now(),
        )
    elif status == "expired":
        query = query.filter(TeacherInviteCode.expires_at < now())

    if keyword:
        like_keyword = f"%{keyword}%"
        matched_user_ids = [
            user.id
            for user in User.query.filter(
                or_(User.username.like(like_keyword), User.email.like(like_keyword))
            ).all()
        ]
        conditions = [TeacherInviteCode.code.like(like_keyword)]
        if matched_user_ids:
            conditions.append(TeacherInviteCode.created_by_id.in_(matched_user_ids))
            conditions.append(TeacherInviteCode.used_by_id.in_(matched_user_ids))
        query = query.filter(or_(*conditions))

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    page = min(page, total_pages)

    invite_codes = (
        query.order_by(TeacherInviteCode.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok(
        {
            "items": [serialize_invite(code) for code in invite_codes],
            "pagination": {
                "page": page,
                "total": total,
                "total_pages": total_pages,
            },
        }
    )


# [前端对应]: 管理员后台 (AdminView.vue) -> “生成邀请码” 按钮
# [业务逻辑]: 按管理员指定的有效天数生成一个新的教师邀请码
@admin_bp.post("/invite-codes")
@jwt_required()
def admin_create_invite_code():
    """按管理员指定天数生成教师邀请码。"""
    admin_user, denied = require_admin()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    expire_days = as_int(body.get("expire_days")) or 1
    if expire_days < 1 or expire_days > 30:
        return err("邀请码有效天数仅支持 1 到 30 天", status=400)

    code = f"TCH-{uuid.uuid4().hex[:8].upper()}"
    while TeacherInviteCode.query.filter_by(code=code).first():
        code = f"TCH-{uuid.uuid4().hex[:8].upper()}"

    expires_at = now() + timedelta(days=expire_days)
    invite_code = TeacherInviteCode(
        code=code,
        expires_at=expires_at,
        created_by_id=admin_user.id,
    )
    db.session.add(invite_code)
    db.session.commit()
    invalidate_admin_overview_cache()
    return ok(
        serialize_invite(invite_code),
        f"已生成 {expire_days} 天有效的教师邀请码",
        status=201,
    )
