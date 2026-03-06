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
    Content,
    Course,
    Enrollment,
    Message,
    Note,
    Review,
    ReviewLike,
    TeacherInviteCode,
    User,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def ok(data=None, message="ok", code=0, status=200):
    return jsonify({"code": code, "message": message, "data": data}), status


def err(message="error", code=1, status=400, data=None):
    return jsonify({"code": code, "message": message, "data": data}), status


def now():
    return datetime.utcnow()


def as_int(v):
    try:
        return int(v)
    except Exception:
        return None


def role_of(user: User | None):
    return ((user.role if user else "") or "").strip().lower()


def is_admin(user: User | None):
    return role_of(user) == "admin"


def current_user():
    uid = as_int(get_jwt_identity())
    if not uid:
        return None
    user = User.query.get(uid)
    if not user or user.status != "active":
        return None
    return user


def require_admin():
    user = current_user()
    if not user:
        return None, err("请先登录", status=401)
    if not is_admin(user):
        return None, err("仅管理员可访问", status=403)
    return user, None


def iso(value):
    return value.isoformat() if value else None


def serialize_user(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "created_at": iso(user.created_at),
        "updated_at": iso(user.updated_at),
    }


def serialize_review(review: Review):
    course = Course.query.get(review.course_id)
    author = User.query.get(review.user_id)
    return {
        "id": review.id,
        "course_id": review.course_id,
        "course_title": course.title if course else "未知课程",
        "user_id": review.user_id,
        "username": author.username if author else "未知用户",
        "rating": review.rating,
        "comment": review.comment,
        "reply_content": review.reply_content,
        "created_at": iso(review.created_at),
    }


def serialize_message(message: Message):
    course = Course.query.get(message.course_id)
    sender = User.query.get(message.sender_id)
    receiver = User.query.get(message.receiver_id) if message.receiver_id else None
    return {
        "id": message.id,
        "course_id": message.course_id,
        "course_title": course.title if course else "未知课程",
        "sender_id": message.sender_id,
        "sender_name": sender.username if sender else "未知用户",
        "receiver_id": message.receiver_id,
        "receiver_name": receiver.username if receiver else "",
        "content": message.content,
        "created_at": iso(message.created_at),
    }


def serialize_invite(code: TeacherInviteCode):
    used_by = User.query.get(code.used_by_id) if code.used_by_id else None
    return {
        "id": code.id,
        "code": code.code,
        "is_used": bool(code.is_used),
        "expires_at": iso(code.expires_at),
        "used_by_id": code.used_by_id,
        "used_by_name": used_by.username if used_by else "",
    }


def bootstrap_admin_account():
    # Optional bootstrap. If the email already exists, only promote it to admin.
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


@admin_bp.get("/overview")
@jwt_required()
def admin_overview():
    _, denied = require_admin()
    if denied:
        return denied

    return ok(
        {
            "user_count": User.query.count(),
            "active_user_count": User.query.filter_by(status="active").count(),
            "disabled_user_count": User.query.filter_by(status="disabled").count(),
            "admin_count": User.query.filter_by(role="admin").count(),
            "teacher_count": User.query.filter_by(role="teacher").count(),
            "student_count": User.query.filter_by(role="student").count(),
            "course_count": Course.query.count(),
            "published_course_count": Course.query.filter_by(status="published").count(),
            "content_count": Content.query.count(),
            "enrollment_count": Enrollment.query.count(),
            "review_count": Review.query.count(),
            "message_count": Message.query.count(),
            "note_count": Note.query.count(),
            "unused_invite_count": TeacherInviteCode.query.filter_by(is_used=False).count(),
        }
    )


@admin_bp.get("/analytics")
@jwt_required()
def admin_analytics():
    _, denied = require_admin()
    if denied:
        return denied

    courses = Course.query.filter_by(status="published").all()
    course_names = []
    course_ids = []
    enroll_counts = []
    review_averages = []
    total_students = 0

    for course in courses:
        course_names.append(course.title)
        course_ids.append(course.id)

        enroll_count = Enrollment.query.filter_by(course_id=course.id).count()
        enroll_counts.append(enroll_count)
        total_students += enroll_count

        reviews = Review.query.filter_by(course_id=course.id).all()
        avg_rating = sum(review.rating for review in reviews) / len(reviews) if reviews else 0
        review_averages.append(round(avg_rating, 1))

    return ok(
        {
            "role": "admin",
            "courseNames": course_names,
            "courseIds": course_ids,
            "enrollCounts": enroll_counts,
            "reviewAverages": review_averages,
            "totalStudents": total_students,
        }
    )


@admin_bp.get("/users")
@jwt_required()
def admin_list_users():
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
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
            "filters": {
                "keyword": keyword,
                "role": role,
                "status": status,
            },
        }
    )


@admin_bp.patch("/users/<int:user_id>/status")
@jwt_required()
def admin_update_user_status(user_id):
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
    return ok(serialize_user(target), "账号状态已更新")


@admin_bp.get("/reviews")
@jwt_required()
def admin_list_reviews():
    _, denied = require_admin()
    if denied:
        return denied

    reviews = Review.query.order_by(Review.created_at.desc(), Review.id.desc()).all()
    return ok({"items": [serialize_review(review) for review in reviews]})


@admin_bp.delete("/reviews/<int:review_id>")
@jwt_required()
def admin_delete_review(review_id):
    _, denied = require_admin()
    if denied:
        return denied

    review = Review.query.get(review_id)
    if not review:
        return err("评价不存在", status=404)

    ReviewLike.query.filter_by(review_id=review_id).delete()
    db.session.delete(review)
    db.session.commit()
    return ok({"id": review_id}, "评价已删除")


@admin_bp.get("/messages")
@jwt_required()
def admin_list_messages():
    _, denied = require_admin()
    if denied:
        return denied

    messages = Message.query.order_by(Message.created_at.desc(), Message.id.desc()).all()
    return ok({"items": [serialize_message(message) for message in messages]})


@admin_bp.delete("/messages/<int:message_id>")
@jwt_required()
def admin_delete_message(message_id):
    _, denied = require_admin()
    if denied:
        return denied

    message = Message.query.get(message_id)
    if not message:
        return err("留言不存在", status=404)

    db.session.delete(message)
    db.session.commit()
    return ok({"id": message_id}, "留言已删除")


@admin_bp.get("/invite-codes")
@jwt_required()
def admin_list_invite_codes():
    _, denied = require_admin()
    if denied:
        return denied

    invite_codes = TeacherInviteCode.query.order_by(
        TeacherInviteCode.id.desc()
    ).all()
    return ok({"items": [serialize_invite(code) for code in invite_codes]})


@admin_bp.post("/invite-codes")
@jwt_required()
def admin_create_invite_code():
    _, denied = require_admin()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    expire_days = as_int(body.get("expire_days"))
    expire_days = expire_days if expire_days else 1
    if expire_days < 1 or expire_days > 30:
        return err("有效天数仅支持 1 到 30 天")

    code = f"ADM-TCH-{uuid.uuid4().hex[:8].upper()}"
    expires_at = now() + timedelta(days=expire_days)
    invite_code = TeacherInviteCode(code=code, expires_at=expires_at)
    db.session.add(invite_code)
    db.session.commit()
    return ok(serialize_invite(invite_code), "邀请码已生成", status=201)
