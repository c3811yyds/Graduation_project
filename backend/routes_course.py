from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from cache_utils import cache_delete, cache_delete_pattern, cache_get_json, cache_set_json
from extensions import db
from models import User, Course, Enrollment, Content, Progress, Message, Review, ReviewLike
from sensitive_filter import reject_sensitive_fields

course_bp = Blueprint("courses", __name__, url_prefix="/api/courses")
content_bp = Blueprint("contents", __name__, url_prefix="/api/contents")

# 课程与内容相关接口模块（由原 routes_auth.py 拆分）

# ---------- helpers ----------

def ok(data=None, message="ok", code=0, status=200):
    """返回统一成功响应。"""
    return jsonify({"code": code, "message": message, "data": data}), status


def err(message="error", code=1, status=400, data=None):
    """返回统一错误响应。"""
    return jsonify({"code": code, "message": message, "data": data}), status


def now():
    """返回当前 UTC 时间。"""
    return datetime.utcnow()


def role_of(user: User):
    """读取用户角色并统一为小写。"""
    return (user.role or "").strip().lower()


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


def is_teacher(u: User):
    """判断用户是否为教师。"""
    return role_of(u) == "teacher"


def is_student(u: User):
    """判断用户是否为学生。"""
    return role_of(u) == "student"


def course_by_id(course_id: int):
    """按主键查询课程。"""
    return Course.query.get(course_id)


def enrollment_status(course_id: int, student_id: int):
    """查询学生在某课程下的最新选课状态。"""
    rec = (
        Enrollment.query.filter_by(course_id=course_id, student_id=student_id)
        .order_by(Enrollment.id.desc())
        .first()
    )
    return rec.status if rec else None


def is_enrolled(course_id: int, student_id: int):
    """判断学生是否处于已选课状态。"""
    return (
        Enrollment.query.filter_by(
            course_id=course_id, student_id=student_id, status="enrolled"
        ).first()
        is not None
    )


def can_view_content(u, c: Course):
    """判断当前用户是否可以查看课程内容。"""
    if c.status == "draft":
        if u is None or c.teacher_id != u.id:
            return False
    return True


def course_list_cache_key(u: User | None):
    """按当前浏览身份构造课程列表缓存 key，避免不同用户看到的状态串值。"""
    if u is None:
        return "courses:list:guest"
    return f"courses:list:{role_of(u) or 'unknown'}:{u.id}"


def invalidate_course_list_cache():
    """课程和选课写操作完成后，统一清理课程列表缓存。"""
    cache_delete_pattern("courses:list:*")


def invalidate_user_analytics_cache(student_id: int | None):
    """按学生维度精准清理个人数据总览缓存，避免无关用户缓存被一起删除。"""
    if not student_id:
        return
    cache_delete(f"analytics:user:{student_id}")


def serialize_course(c: Course, u: User | None = None):
    """序列化课程信息。"""
    # 统计课程平均评分与评价数量。
    reviews = Review.query.filter_by(course_id=c.id).all()
    avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 0.0

    teacher = User.query.get(c.teacher_id)
    t_name = teacher.username if teacher else "未知"

    data = {
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "teacher_id": c.teacher_id,
        "teacher_name": t_name,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "rating": round(avg_rating, 1),
        "review_count": len(reviews),
        "is_enrolled": False,
        "enrollment_status": None,
    }
    if u and is_student(u):
        st = enrollment_status(c.id, u.id)
        data["enrollment_status"] = st
        data["is_enrolled"] = st == "enrolled"
    return data


def serialize_content(x: Content, is_learned: bool = False):
    """序列化课件内容信息，并按需附带学生学习标记。"""
    return {
        "id": x.id,
        "course_id": x.course_id,
        "type": x.type,
        "title": x.title,
        "url_or_path": x.url_or_path,
        "duration_seconds": x.duration_seconds,
        "size_bytes": x.size_bytes,
        "created_at": x.created_at.isoformat() if x.created_at else None,
        "is_learned": is_learned,
    }


def serialize_message(x: Message):
    """序列化课程留言信息。"""
    sender = User.query.get(x.sender_id)
    sender_name = sender.username if sender else "未知用户"
    if sender and getattr(sender, 'real_name', None):
        sender_name = sender.real_name
        
    return {
        "id": x.id,
        "course_id": x.course_id,
        "sender_id": x.sender_id,
        "sender_name": sender_name,
        "sender_role": sender.role if sender else "student",
        "receiver_id": x.receiver_id,
        "content": x.content,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def upload_dir() -> Path:
    """返回课件上传目录，并在缺失时自动创建。"""
    p = current_app.config.get("UPLOAD_DIR") or os.path.join(current_app.root_path, "uploads")
    p = Path(p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def allowed_ext(filename: str):
    """判断上传文件扩展名是否允许。"""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    allowed = {
        # 视频：浏览器通常可直接预览。
        "mp4", "webm", "ogg", "mov", "avi",
        # 音频：浏览器通常可直接预览。
        "mp3", "wav", "flac", "aac", "m4a",
        # 图片：浏览器原生支持预览。
        "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico",
        # 文档：PDF 可直接预览，其余通常下载后查看。
        "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "csv", "md",
        # 压缩包：仅允许上传和下载。
        "zip", "rar", "7z", "tar", "gz"
    }
    return ext in allowed



# ---------- courses ----------

# [前端对应]: 首页课程大厅 (HomeView.vue) -> 加载并展示分类好的所有课程卡片
# [业务逻辑]: 返回课程列表数据，可供未登录及各种不同角色的用户进行自由浏览
@course_bp.get("")
@jwt_required(optional=True)
def list_courses():
    """
    正式站点策略：
    - 未登录也可浏览课程
    - 登录后学生可看到 is_enrolled / enrollment_status
    """
    u = current_user()
    cache_key = course_list_cache_key(u)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return ok(cached)

    query = Course.query
    if u and is_teacher(u):
        query = query.filter((Course.status == "published") | ((Course.status == "draft") & (Course.teacher_id == u.id)))
    else:
        query = query.filter_by(status="published")

    courses = query.order_by(Course.id.desc()).all()
    data = [serialize_course(c, u) for c in courses]
    cache_set_json(cache_key, data, ttl_seconds=60)
    return ok(data)


# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 进入页面按课程 id 拉取详情
# [业务逻辑]: 返回单课程详情，草稿课程仅所属教师可访问
@course_bp.get("/<int:course_id>")
@jwt_required(optional=True)
def get_course(course_id):
    u = current_user()

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    # 草稿课程仅课程所属教师本人可见
    if c.status == "draft":
        if not u or not (is_teacher(u) and c.teacher_id == u.id):
            return err("无权限访问该课程", status=403)

    return ok(serialize_course(c, u))


# [前端对应]: 教师首页 (HomeView.vue) -> 右上角 "+ 创建新课程" 弹窗内确定按钮
# [业务逻辑]: 构建状态初始默认为未发布的“草稿(draft)”状态课程元数据
@course_bp.post("")
@jwt_required()
def create_course():
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)
    if not is_teacher(u):
        return err("仅教师可创建课程", status=403)

    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    if not title:
        return err("课程标题不能为空")

    sensitive_err = reject_sensitive_fields(
        {"课程标题": title, "课程简介": description},
        err,
        scene="content",
    )
    if sensitive_err:
        return sensitive_err

    c = Course(
        title=title,
        description=description,
        teacher_id=u.id,
        status="draft",
        created_at=now(),
        updated_at=now(),
    )
    db.session.add(c)
    db.session.commit()
    invalidate_course_list_cache()
    return ok(serialize_course(c, u), "创建成功", status=201)


# [前端对应]: 课程详情页教师编辑弹窗 -> 保存课程标题/简介
# [业务逻辑]: 仅课程所属教师可更新课程基础信息并刷新 updated_at
@course_bp.patch("/<int:course_id>")
@jwt_required()
def update_course(course_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限修改", status=403)

    body = request.get_json(silent=True) or {}
    has_title = "title" in body
    has_desc = "description" in body
    if not has_title and not has_desc:
        return err("至少提交一个可修改字段(title/description)")

    pending_fields = {}
    if has_title:
        title = (body.get("title") or "").strip()
        if not title:
            return err("课程标题不能为空")
        pending_fields["课程标题"] = title

    if has_desc:
        description = (body.get("description") or "").strip()
        pending_fields["课程简介"] = description

    sensitive_err = reject_sensitive_fields(pending_fields, err, scene="content")
    if sensitive_err:
        return sensitive_err

    if has_title:
        c.title = title

    if has_desc:
        c.description = description

    c.updated_at = now()
    db.session.commit()
    invalidate_course_list_cache()
    return ok(serialize_course(c, u), "更新成功")


# [前端对应]: 教师首页 (HomeView.vue) -> 针对单个未发课程点击 "发布课程" 按钮
# [业务逻辑]: 变动课程权限字段为对外通过并上架(published)供学生阅览
@course_bp.put("/<int:course_id>/publish")
@jwt_required()
def publish_course(course_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限发布", status=403)

    c.status = "published"
    c.updated_at = now()
    db.session.commit()
    invalidate_course_list_cache()
    return ok(serialize_course(c, u), "发布成功")


# [前端对应]: 教师首页 (HomeView.vue) -> 针对已发布课程点击 "下架课程" 按钮操作
# [业务逻辑]: 将发售课程冻结并强行撤回草稿(draft)，学生从此无法再在课程大厅选此课
@course_bp.put("/<int:course_id>/unpublish")
@jwt_required()
def unpublish_course(course_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限下架", status=403)

    c.status = "draft"
    c.updated_at = now()
    db.session.commit()
    invalidate_course_list_cache()
    return ok(serialize_course(c, u), "下架成功")


# [前端对应]: 首页草稿分类模块 -> "永久删除" 无效记录选项
# [业务逻辑]: 强力物理根除一门处于“未发布(草稿)”状态的课程及所有的级联关联数据
@course_bp.delete("/<int:course_id>")
@jwt_required()
def delete_course(course_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权删除", status=403)
        
    if c.status != "draft":
        return err("仅允许删除草稿箱（未发布/已下架）状态的课程", status=400)

    # 级联删除: Enrollment(选课), Message(留言), Progress(进度), Content(课件), Review(评价)
    Enrollment.query.filter_by(course_id=course_id).delete()
    Message.query.filter_by(course_id=course_id).delete()
    Review.query.filter_by(course_id=course_id).delete()

    contents = Content.query.filter_by(course_id=course_id).all()
    c_ids = [ct.id for ct in contents]
    if c_ids:
        Progress.query.filter(Progress.content_id.in_(c_ids)).delete()
        Content.query.filter_by(course_id=course_id).delete()

    db.session.delete(c)
    db.session.commit()
    invalidate_course_list_cache()
    return ok({"id": course_id}, "课程已永久删除")

# ---------- enrollment ----------

# [前端对应]: 课程大厅/详情页 (HomeView.vue / CourseDetailView.vue) -> 学生的深蓝色 "选课" 动作
# [业务逻辑]: 正式记录学生与此课产生的“已受教”归属关系绑定
@course_bp.post("/<int:course_id>/enroll")
@jwt_required()
def enroll(course_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)
    if not is_student(u):
        return err("仅学生可选课", status=403)

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)
    if c.status != "published":
        return err("仅可选已发布课程", status=400)

    rec = (
        Enrollment.query.filter_by(course_id=course_id, student_id=u.id)
        .order_by(Enrollment.id.desc())
        .first()
    )
    if rec and rec.status == "enrolled":
        return ok({"course_id": course_id, "status": "enrolled"}, "已选课")

    if rec:
        rec.status = "enrolled"
        rec.enrolled_at = now()
    else:
        db.session.add(
            Enrollment(course_id=course_id, student_id=u.id, status="enrolled", enrolled_at=now())
        )

    db.session.commit()
    invalidate_course_list_cache()
    invalidate_user_analytics_cache(u.id)
    return ok({"course_id": course_id, "status": "enrolled"}, "选课成功")


# [前端对应]: 首页 (HomeView.vue) -> 学生处于已选课程列表中按下红色 "退课" 按钮
# [业务逻辑]: 解除学籍物理清理关联此选课关系的登记名册
@course_bp.delete("/<int:course_id>/enroll")
@jwt_required()
def drop(course_id):
    u = current_user()
    if not u or not is_student(u):
        return err("禁止操作", status=403)
    rec = Enrollment.query.filter_by(course_id=course_id, student_id=u.id).first()
    if rec:
        db.session.delete(rec)
        db.session.commit()
        invalidate_course_list_cache()
        invalidate_user_analytics_cache(u.id)
    return ok(None, "退课成功")


# ---------- progress (恢复丢失的进度和学生列表接口) ----------

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 顶端横向或环形学习进展条及百分比
# [业务逻辑]: 统计学完课程具体章节数的子集总长映射总章节计算得出进度分值比例
@course_bp.get("/<int:course_id>/progress")
@jwt_required()
def my_course_progress(course_id):
    u = current_user()
    if not u or not is_student(u):
        return ok({"progress": 0, "completed": 0, "total": 0}, "无进度")

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    contents = Content.query.filter_by(course_id=course_id).all()
    total_contents = len(contents)
    if total_contents == 0:
        return ok({"progress": 0, "completed": 0, "total": 0})

    c_ids = [ct.id for ct in contents]
    # 进度按“已学习的不同课件数”计算，避免历史重复记录把百分比冲高。
    viewed = (
        db.session.query(Progress.content_id)
        .filter(
            Progress.student_id == u.id,
            Progress.content_id.in_(c_ids),
        )
        .distinct()
        .count()
    )

    return ok({
        "progress": int((viewed / total_contents) * 100),
        "completed": viewed,
        "total": total_contents
    })

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 教师端切到 "选课学生" Tab 页面时触发
# [业务逻辑]: 直接把选这门课的所有学子人员名录连带他们各自看视频/文章的完成进度拉取出来展示
@course_bp.get("/<int:course_id>/students")
@jwt_required()
def get_course_students(course_id):
    u = current_user()
    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if not is_teacher(u) or c.teacher_id != u.id:
        return err("无权限查看", status=403)

    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    contents = Content.query.filter_by(course_id=course_id).all()
    total_contents = len(contents)
    c_ids = [ct.id for ct in contents]

    students_data = []
    for en in enrollments:
        student = User.query.get(en.student_id)
        if not student:
            continue
        viewed = 0
        if total_contents > 0:
            # 教师查看学生进度时同样按不同课件去重统计，和学生端口径保持一致。
            viewed = (
                db.session.query(Progress.content_id)
                .filter(
                    Progress.student_id == student.id,
                    Progress.content_id.in_(c_ids),
                )
                .distinct()
                .count()
            )
        progress_pct = int((viewed / total_contents) * 100) if total_contents > 0 else 0
        
        students_data.append({
            "id": student.id,
            "username": student.username,
            "progress": progress_pct,
            "completed": viewed,
            "total": total_contents,
            "enrolled_at": en.enrolled_at.isoformat() if en.enrolled_at else None
        })

    return ok({"students": students_data})

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 每当多媒体视频/课件被执行完毕(播放到尾/读到最后)后台自动打点调用
# [业务逻辑]: 持久化单向增加对应模块下的“完成”确认并反推更新用户主进度面板
@content_bp.post("/<int:content_id>/view")
@jwt_required()
def record_content_view(content_id):
    u = current_user()
    if not u or not is_student(u):
        return ok(None)

    ct = Content.query.get(content_id)
    if not ct:
        return err("内容不存在", status=404)

    if not is_enrolled(ct.course_id, u.id):
        return err("未选修此课程", status=403)

    exist_prog = Progress.query.filter_by(student_id=u.id, content_id=content_id).first()
    if not exist_prog:
        p = Progress(
            student_id=u.id,
            content_id=content_id,
            progress_percent=100,
            status="completed",
            last_viewed_at=now(),
            completed_at=now()
        )
        db.session.add(p)
        db.session.commit()

    return ok(None, "进度更新成功")

# ---------- contents ----------

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> "课程内容" Tab 分页卡片被点击激活拉取大类列表
# [业务逻辑]: 将针对本课程在库中归档的所有相关 PDF 文稿, 视频文件路径作列表集合返回
@course_bp.get("/<int:course_id>/contents")
@jwt_required(optional=True)
def list_course_contents(course_id):
    u = current_user()

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if not can_view_content(u, c):
        return err("非公开内容无法未授权预览", status=403)

    rows = Content.query.filter_by(course_id=course_id).order_by(Content.id.desc()).all()
    learned_ids = set()
    if u and is_student(u) and rows:
        row_ids = [x.id for x in rows]
        learned_ids = {
            content_id
            for (content_id,) in db.session.query(Progress.content_id)
            .filter(
                Progress.student_id == u.id,
                Progress.content_id.in_(row_ids),
            )
            .all()
        }
    return ok([serialize_content(x, x.id in learned_ids) for x in rows])


# [前端对应]: 课程详情页按课件 id 获取单条内容详情
# [业务逻辑]: 单条内容查询，沿用 can_view_content 的草稿/发布可见性规则
@content_bp.get("/<int:content_id>")
@jwt_required(optional=True)
def get_content(content_id):
    u = current_user()

    item = Content.query.get(content_id)
    if not item:
        return err("内容不存在", status=404)

    c = course_by_id(item.course_id)
    if not c:
        return err("课程不存在", status=404)

    if not can_view_content(u, c):
        return err("非公开内容无法未授权预览", status=403)

    return ok(serialize_content(item))


# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 教师切到这页的 "上传内容/课件" 选择文件提交
# [业务逻辑]: 对物理二进制文件进行本地托管落地并生成唯一链接，写入 contents 记录
@course_bp.post("/<int:course_id>/contents/upload")
@jwt_required()
def upload_course_content(course_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)
    if not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限上传", status=403)

    f = request.files.get("file")
    if not f or not f.filename:
        return err("请上传文件(file)", status=400)
    if not allowed_ext(f.filename):
        return err("不支持的文件类型", status=400)

    safe = secure_filename(f.filename)
    ext = safe.rsplit(".", 1)[-1].lower()
    final_name = f"{uuid.uuid4().hex}.{ext}"
    full = upload_dir() / final_name
    title = (request.form.get("title") or "").strip() or safe

    sensitive_err = reject_sensitive_fields({"课件标题": title}, err, scene="content")
    if sensitive_err:
        return sensitive_err

    f.save(full)

    # 不再硬编码 uploads/，直接保存文件名，因为我们在读取时会自动使用 upload_dir() 来查找
    rel = final_name
    
    if ext in {"mp4", "webm", "ogg", "mov", "avi"}:
        ctype = "video"
    elif ext in {"mp3", "wav", "flac", "aac", "m4a"}:
        ctype = "audio"
    elif ext in {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico"}:
        ctype = "image"
    else:
        ctype = ext

    item = Content(
        course_id=course_id,
        type=ctype,
        title=title,
        url_or_path=rel,
        duration_seconds=None,
        size_bytes=full.stat().st_size,
        created_at=now(),
    )
    db.session.add(item)
    db.session.commit()
    return ok(serialize_content(item), "上传成功", status=201)


# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 课单列表右侧教师专属 "重命名" 按钮
# [业务逻辑]: 仅仅改动映射出页面排版的显示名称字符
@content_bp.put("/<int:content_id>")
@jwt_required()
def update_content(content_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)

    item = Content.query.get(content_id)
    if not item:
        return err("内容不存在", status=404)

    c = course_by_id(item.course_id)
    if not c:
        return err("课程不存在", status=404)
    if not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限修改", status=403)

    data = request.get_json() or {}
    new_title = data.get("title", "").strip()
    if not new_title:
        return err("课件名称不能为空", status=400)

    sensitive_err = reject_sensitive_fields({"课件标题": new_title}, err, scene="content")
    if sensitive_err:
        return sensitive_err

    item.title = new_title
    db.session.commit()
    return ok({"id": item.id, "title": item.title}, "修改成功")

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 教师通过 "删除该资料" 垃圾桶切面图标执行的操作
# [业务逻辑]: 脱钩废弃内容从教案目录里断联并擦去与之交织的小节统计数值点
@content_bp.delete("/<int:content_id>")
@jwt_required()
def delete_content(content_id):
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)

    item = Content.query.get(content_id)
    if not item:
        return err("内容不存在", status=404)

    c = course_by_id(item.course_id)
    if not c:
        return err("课程不存在", status=404)
    if not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限删除", status=403)

    # 级联删除相关学习进度记录
    Progress.query.filter_by(content_id=content_id).delete()
    
    db.session.delete(item)
    db.session.commit()
    return ok({"id": content_id}, "删除成功")


# [前端对应]: 课程详情页面 (CourseDetailView.vue) -> 当触发视频播放器拉流或按下 "下载此份课件" 引发 GET 资源获取
# [业务逻辑]: 实现经过凭据过滤（防盗链）后放行的核心私域文件串流，给前端消费流
@content_bp.get("/<int:content_id>/file")
def access_content_file(content_id):
    """
    支持:
    - Authorization: Bearer <token>
    - ?token=...
    """
    token = None
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = (request.args.get("token") or "").strip()
        
    is_download = request.args.get("download") == "1"
    
    u = None
    if token:
        try:
            from flask_jwt_extended import decode_token
            payload = decode_token(token)
            uid = as_int(payload.get("sub"))
            if uid:
                u = User.query.get(uid)
                if u and u.status != "active":
                    u = None
        except Exception:
            pass

    if is_download and not u:
        return err("下载需登录", status=401)

    item = Content.query.get(content_id)
    if not item:
        return err("内容不存在", status=404)

    c = course_by_id(item.course_id)
    if not c:
        return err("课程不存在", status=404)

    if not can_view_content(u, c):
        return err("非公开内容无法未授权预览", status=403)

    p = (item.url_or_path or "").strip()

    # 外链模式
    if p.startswith("http://") or p.startswith("https://"):
        return ok({"external_url": p}, "外部地址模式")

    # 本地文件模式
    # 先清理历史冗余前缀 uploads/ 或 storage/ 为了兼容历史数据
    if p.startswith("uploads/"):
        p = p[8:]
    elif p.startswith("storage/"):
        p = p[8:]
    
    # 动态拼接当前的绝对挂载目录
    up = upload_dir().resolve()
    full = (up / p).resolve()

    try:
        # 确保下载文件处于我们允许的挂载盘里，防止 ../../ 路径篡改攻击
        full.relative_to(up)
    except Exception:
        return err("非法文件路径", status=400)

    if not full.exists() or not full.is_file():
        return err("文件不存在", status=404)

    # 检查是否请求强制下载
    is_download = request.args.get("download") == "1"
    
    # 获取原始文件名，如果没有则从路径里拿最后一部分
    download_name = item.title if item.title and "." in item.title else f"{item.title or '未知'}{full.suffix}"
    
    return send_file(full, as_attachment=is_download, download_name=download_name)


# ---------- messages ----------

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 切换 "留言交流" Tab 时刷新渲染聊天流水
# [业务逻辑]: 顺着发表的时间节点整理交互回复数据
@course_bp.get("/<int:course_id>/messages")
@jwt_required(optional=True)
def list_course_messages(course_id):
    u = current_user()

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if c.status == "draft":
        if u is None or c.teacher_id != u.id:
            return err("无法查看草稿课程的留言", status=403)
    

    rows = Message.query.filter_by(course_id=course_id).order_by(Message.id.asc()).all()
    return ok([serialize_message(x) for x in rows])


# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 底部留言框敲好字点下 "发送留言" 图标
# [业务逻辑]: 写入一条由学子/老师发出的图文探讨新消息
@course_bp.post("/<int:course_id>/messages")
@jwt_required(optional=True)
def create_course_message(course_id):
    u = current_user()
    if not u:
        return err("请先登录", status=401)

    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)

    if is_student(u) and not is_enrolled(course_id, u.id):
        return err("你未选修该课程，不能留言", status=403)
    if is_teacher(u) and c.teacher_id != u.id:
        return err("无权限在该课程留言", status=403)

    body = request.get_json(silent=True) or {}
    text = (body.get("content") or "").strip()
    receiver_id = body.get("receiver_id")

    if not text:
        return err("留言内容不能为空")

    sensitive_err = reject_sensitive_fields({"留言内容": text}, err, scene="content")
    if sensitive_err:
        return sensitive_err

    m = Message(
        course_id=course_id,
        sender_id=u.id,
        receiver_id=receiver_id,
        content=text,
        created_at=now(),
    )
    db.session.add(m)
    db.session.commit()
    return ok(serialize_message(m), "留言成功", status=201)

# ---------- reviews ----------

def serialize_review(x: Review, cur_user=None):
    """序列化课程评价及点赞状态。"""
    user = User.query.get(x.user_id)
    liked = False
    if cur_user:
        if ReviewLike.query.filter_by(review_id=x.id, user_id=cur_user.id).first():
            liked = True
    return {
        "id": x.id,
        "course_id": x.course_id,
        "user_id": x.user_id,
        "username": user.username if user else "未知",
        "rating": x.rating,
        "comment": x.comment,
        "created_at": x.created_at.isoformat() if x.created_at else None,
        "reply_content": x.reply_content,
        "reply_time": x.reply_time.isoformat() if x.reply_time else None,
        "likes_count": x.likes_count or 0,
        "liked": liked
    }

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 划动到 "课程评价" Tab 界面显示所有带星星的主观长段打分
# [业务逻辑]: 拉出期末结课式的评论与打分(以点赞+时间优先倒排倒序)
@course_bp.get("/<int:course_id>/reviews")
@jwt_required(optional=True)
def list_course_reviews(course_id):
    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)
    rows = Review.query.filter_by(course_id=course_id).order_by(Review.likes_count.desc(), Review.created_at.desc()).all()
    u = current_user()
    return ok([serialize_review(r, u) for r in rows])

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 学生专属的 "点选五角星，提交打分评价" 框表单按钮
# [业务逻辑]: 收留定档学生的最终评价信息(内含查重限制，一人单次)
@course_bp.post("/<int:course_id>/reviews")
@jwt_required(optional=True)
def create_course_review(course_id):
    u = current_user()
    if not u:
        return err("请先登录", status=401)
    
    c = course_by_id(course_id)
    if not c:
        return err("课程不存在", status=404)
        
    if not is_student(u) or not is_enrolled(course_id, u.id):
        return err("只有选修了该课程的学生才能评价", status=403)
        
    # 一人一课只允许保留一条评价记录，先检查是否已经提交过。
    existing = Review.query.filter_by(course_id=course_id, user_id=u.id).first()
    if existing:
        return err("你已经评价过该课程，不能重复评价", status=400)
        
    body = request.get_json(silent=True) or {}
    rating = as_int(body.get("rating"))
    comment = (body.get("comment") or "").strip()
    
    if not rating or rating < 1 or rating > 5:
        return err("请输入1到5的有效星级评分", status=400)

    sensitive_err = reject_sensitive_fields({"评价内容": comment}, err, scene="content")
    if sensitive_err:
        return sensitive_err
        
    r = Review(
        course_id=course_id,
        user_id=u.id,
        rating=rating,
        comment=comment,
        created_at=now()
    )
    db.session.add(r)
    db.session.commit()
    invalidate_course_list_cache()
    invalidate_user_analytics_cache(u.id)

    return ok(serialize_review(r), "评价成功", status=201)

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 评价区供教师使用的红色 "违规删除" 按钮
# [业务逻辑]: 抹掉恶意灌水打分乱写的评价发言并扣减星数基数
@course_bp.delete("/<int:course_id>/reviews/<int:review_id>")
@jwt_required()
def delete_course_review(course_id, review_id):
    u = current_user()
    if not u:
        return err("需登录", status=401)
    
    r = Review.query.get(review_id)
    if not r or r.course_id != course_id:
        return err("评价不存在", status=404)

    c = course_by_id(course_id)
    if not c or not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限删除", status=403)

    db.session.delete(r)
    db.session.commit()
    invalidate_course_list_cache()
    invalidate_user_analytics_cache(r.user_id)
    return ok({"id": review_id}, "评价已删除")

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> "官方追加回复" 互动动作提交
# [业务逻辑]: 任课老师对精辟点评或偏激答疑下的额外跟帖说明
@course_bp.put("/<int:course_id>/reviews/<int:review_id>/reply")
@jwt_required()
def reply_course_review(course_id, review_id):
    u = current_user()
    if not u:
        return err("需登录", status=401)
    
    r = Review.query.get(review_id)
    if not r or r.course_id != course_id:
        return err("评价不存在", status=404)

    c = course_by_id(course_id)
    if not c or not (is_teacher(u) and c.teacher_id == u.id):
        return err("无权限回复", status=403)

    body = request.get_json(silent=True) or {}
    reply_content = body.get("reply_content", "").strip()

    sensitive_err = reject_sensitive_fields({"回复内容": reply_content}, err, scene="content")
    if sensitive_err:
        return sensitive_err
    
    r.reply_content = reply_content
    r.reply_time = now() if reply_content else None
    db.session.commit()
    return ok(serialize_review(r, u), "回复成功")

# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 每条评价边上的 "大拇指（点赞/取消点赞）" 图标
# [业务逻辑]: 累加推高热评赞同数并切换红心亮灭(联合表限制同一个人防刷)
@course_bp.post("/<int:course_id>/reviews/<int:review_id>/like")
@jwt_required()
def toggle_like_review(course_id, review_id):
    u = current_user()
    if not u:
        return err("需登录", status=401)
    
    r = Review.query.get(review_id)
    if not r or r.course_id != course_id:
        return err("评价不存在", status=404)
        
    like = ReviewLike.query.filter_by(review_id=review_id, user_id=u.id).first()
    if like:
        db.session.delete(like)
        r.likes_count = max(0, r.likes_count - 1)
        msg = "取消点赞"
    else:
        new_like = ReviewLike(review_id=review_id, user_id=u.id, created_at=now())
        db.session.add(new_like)
        r.likes_count += 1
        msg = "点赞成功"
        
    db.session.commit()
    return ok(serialize_review(r, u), msg)

