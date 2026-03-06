# -*- coding:utf-8 -*-
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from extensions import db
from models import Note, User
from sensitive_filter import reject_sensitive_fields

note_bp = Blueprint("notes", __name__, url_prefix="/api/notes")

def ok(data=None, message="ok", code=0, status=200):
    return jsonify({"code": code, "message": message, "data": data}), status

def err(message="error", code=1, status=400, data=None):
    return jsonify({"code": code, "message": message, "data": data}), status

def as_int(v):
    try:
        return int(v)
    except Exception:
        return None

def current_user():
    uid = as_int(get_jwt_identity())
    if not uid:
        return None
    return User.query.get(uid)

def now():
    return datetime.utcnow()

def serialize_note(x: Note):
    return {
        "id": x.id,
        "title": x.title,
        "content": x.content,
        "created_at": x.created_at.isoformat() if x.created_at else None,
        "updated_at": x.updated_at.isoformat() if x.updated_at else None,
    }


# [前端对应]: 全局右侧边栏 MemoSidebar -> 初始化获取当前用户的所有笔记列表
# [业务逻辑]: 按照创建时间展示这个人的专属云笔记表
@note_bp.get("")
@jwt_required()
def get_my_notes():
    u = current_user()
    if not u:
        return err("Token 无效", status=401)
    
    notes = Note.query.filter_by(user_id=u.id).order_by(Note.updated_at.desc()).all()
    return ok([serialize_note(x) for x in notes])


# [前端对应]: 全局右侧边栏 MemoSidebar -> 点击 "新建笔记本" 按钮
# [业务逻辑]: 增加一篇含有默认标题的新备忘录草稿
@note_bp.post("")
@jwt_required()
def create_note():
    u = current_user()
    if not u:
        return err("Token 无效", status=401)
        
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "未命名笔记").strip()
    sensitive_err = reject_sensitive_fields({"笔记标题": title}, err, scene="content")
    if sensitive_err:
        return sensitive_err
    
    n = Note(
        user_id=u.id,
        title=title,
        content="",
        created_at=now(),
        updated_at=now()
    )
    db.session.add(n)
    db.session.commit()
    
    return ok(serialize_note(n), "创建成功", status=201)


# [前端对应]: 全局右侧边栏 MemoSidebar -> 当在 textarea 编辑内容后失焦 (blur/debounce) 自动保存功能
# [业务逻辑]: 更新云端日记本的内容和时间戳
@note_bp.put("/<int:note_id>")
@jwt_required()
def update_note(note_id):
    u = current_user()
    if not u:
        return err("未登录", status=401)
        
    n = Note.query.get(note_id)
    if not n or n.user_id != u.id:
        return err("无修改权限或文档不存在", status=404)
        
    body = request.get_json(silent=True) or {}
    pending_fields = {}
    if "title" in body:
        pending_fields["笔记标题"] = (body.get("title") or "").strip() or "未命名笔记"
    if "content" in body:
        pending_fields["笔记内容"] = body.get("content") or ""
    sensitive_err = reject_sensitive_fields(pending_fields, err, scene="content")
    if sensitive_err:
        return sensitive_err

    # 支持修改标题或内容
    if "title" in body:
        n.title = (body.get("title") or "").strip() or "未命名笔记"
    if "content" in body:
        n.content = body.get("content") or ""
        
    n.updated_at = now()
    db.session.commit()
    return ok(serialize_note(n), "更新成功")


# [前端对应]: 全局右侧边栏 MemoSidebar ->  笔记标题旁边的删除 (x) 按钮
# [业务逻辑]: 彻底物理删除该文档记录
@note_bp.delete("/<int:note_id>")
@jwt_required()
def delete_note(note_id):
    u = current_user()
    if not u:
        return err("未登录", status=401)
        
    n = Note.query.get(note_id)
    if not n or n.user_id != u.id:
        return err("无权限删除", status=404)
        
    db.session.delete(n)
    db.session.commit()
    return ok({"id": note_id}, "已移入垃圾桶回收站")
