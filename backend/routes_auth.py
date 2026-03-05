from __future__ import annotations

from datetime import datetime
from pathlib import Path
from functools import lru_cache
import os
import uuid
import random
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.header import Header

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import create_access_token, decode_token, get_jwt_identity, jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from extensions import db
from models import User, Course, Enrollment, Content, Progress, Message, Review, ReviewLike, VerifyCode, TeacherInviteCode

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
user_bp = Blueprint("users", __name__, url_prefix="/api/users")
course_bp = Blueprint("courses", __name__, url_prefix="/api/courses")
content_bp = Blueprint("contents", __name__, url_prefix="/api/contents")


# ---------- helpers ----------

def ok(data=None, message="ok", code=0, status=200):
    return jsonify({"code": code, "message": message, "data": data}), status


def err(message="error", code=1, status=400, data=None):
    return jsonify({"code": code, "message": message, "data": data}), status


def now():
    return datetime.utcnow()


def role_of(user: User):
    return (user.role or "").strip().lower()


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


def is_teacher(u: User):
    return role_of(u) == "teacher"


def is_student(u: User):
    return role_of(u) == "student"


def course_by_id(course_id: int):
    return Course.query.get(course_id)


def enrollment_status(course_id: int, student_id: int):
    rec = (
        Enrollment.query.filter_by(course_id=course_id, student_id=student_id)
        .order_by(Enrollment.id.desc())
        .first()
    )
    return rec.status if rec else None


def is_enrolled(course_id: int, student_id: int):
    return (
        Enrollment.query.filter_by(
            course_id=course_id, student_id=student_id, status="enrolled"
        ).first()
        is not None
    )


def can_view_content(u, c: Course):
    if c.status == "draft":
        if u is None or c.teacher_id != u.id:
            return False
    return True


def serialize_course(c: Course, u: User | None = None):
    # Calculate average rating and review count
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


def serialize_content(x: Content):
    return {
        "id": x.id,
        "course_id": x.course_id,
        "type": x.type,
        "title": x.title,
        "url_or_path": x.url_or_path,
        "duration_seconds": x.duration_seconds,
        "size_bytes": x.size_bytes,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def serialize_message(x: Message):
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
    p = current_app.config.get("UPLOAD_DIR") or os.path.join(current_app.root_path, "uploads")
    p = Path(p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def allowed_ext(filename: str):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    allowed = {
        # 视频 (Video) - 通常浏览器支持 mp4, webm, ogg预览
        "mp4", "webm", "ogg", "mov", "avi",
        # 音频 (Audio) - 通常浏览器支持 mp3, ogg, wav预览
        "mp3", "wav", "flac", "aac", "m4a",
        # 图片 (Image) - 浏览器原生支持预览
        "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico",
        # 文档 (Document) - pdf可原生存预览，其余通常需下载或Office Web Viewer
        "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "csv", "md",
        # 压缩包等 (Archive)
        "zip", "rar", "7z", "tar", "gz"
    }
    return ext in allowed


DEFAULT_SENSITIVE_WORDS = {
    "admin", "root", "system", "管理员", "官方", "客服",
    "傻逼", "操", "妈的", "废物", "垃圾", "弱智",
    "抗议", "示威", "革命", "政变", "分裂", "颠覆", "暴动",
    "性", "色情", "淫秽", "约炮", "裸聊", "黄片", "黄色网站", "援交",
    "攻击", "冲突", "战争", "屠杀", "爆炸", "枪击", "刺杀", "恐袭",
    "毒品", "赌博", "非法交易", "贩毒", "洗钱", "诈骗", "走私", "黑市",
    "歧视", "虚假宣传", "夸大效果", "造谣", "仇恨言论", "传销", "测试",
}


def _candidate_sensitive_lexicon_dirs() -> list[Path]:
    custom_dir = (os.getenv("SENSITIVE_LEXICON_DIR") or "").strip()
    this_file = Path(__file__).resolve()
    candidates = []

    if custom_dir:
        candidates.append(Path(custom_dir))

    # 本地开发：仓库根目录/third_party/Sensitive-lexicon/Vocabulary
    candidates.append(this_file.parent.parent / "third_party" / "Sensitive-lexicon" / "Vocabulary")
    # 兼容将词库直接放到 backend 目录下的场景
    candidates.append(this_file.parent / "third_party" / "Sensitive-lexicon" / "Vocabulary")
    return candidates


def _read_text_with_fallback_encodings(path: Path):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception:
            return None
    return None


@lru_cache(maxsize=1)
def load_sensitive_words() -> tuple[str, ...]:
    words = {w.lower() for w in DEFAULT_SENSITIVE_WORDS}

    for base_dir in _candidate_sensitive_lexicon_dirs():
        if not base_dir.exists() or not base_dir.is_dir():
            continue
        for txt_file in base_dir.glob("*.txt"):
            text = _read_text_with_fallback_encodings(txt_file)
            if not text:
                continue
            for raw in text.splitlines():
                word = raw.strip().lstrip("\ufeff")
                if not word or word.startswith("#"):
                    continue
                words.add(word.lower())

    # 长词优先，提升命中稳定性
    return tuple(sorted(words, key=len, reverse=True))


def find_sensitive_word(text: str):
    lowered = (text or "").strip().lower()
    if not lowered:
        return None
    for word in load_sensitive_words():
        if word and word in lowered:
            return word
    return None


# ---------- auth ----------

def send_email_code(email: str, code: str):
    # This expects env variables to send real emails, else prints to console
    mail_server = os.getenv("MAIL_SERVER")
    mail_port = as_int(os.getenv("MAIL_PORT")) or 465
    mail_user = os.getenv("MAIL_USERNAME")
    mail_pass = os.getenv("MAIL_PASSWORD")

    print(f"========== 验证码已生成 [用于测试/备用] ==========")
    print(f"邮箱: {email} | 验证码: {code}")
    print(f"==================================================")

    if not all([mail_server, mail_port, mail_user, mail_pass]):
        print("注意: 暂未配置完整的 MAIL 相关环境变量(MAIL_SERVER等)，将只在控制台打印验证码")
        return True

    try:
        from email.utils import formataddr
        msg = MIMEText(f"【智能学习网站】您的注册验证码为：{code}，5分钟内有效。", 'plain', 'utf-8')
        msg['From'] = formataddr((str(Header("学习平台", 'utf-8')), mail_user))
        msg['To'] = email
        msg['Subject'] = Header("账号注册验证码", 'utf-8')

        if mail_port in [465]:
            server = smtplib.SMTP_SSL(mail_server, mail_port)
        else:
            server = smtplib.SMTP(mail_server, mail_port)
            server.starttls()
            
        server.login(mail_user, mail_pass)
        server.sendmail(mail_user, [email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("发送邮件失败:", e)
        return False

# [前端对应]: 登录注册弹窗 (AuthModal.vue) -> 点击“发送验证码”
# [业务逻辑]: 生成并保存邮箱验证码，写入过期时间并尝试发送邮件
@auth_bp.post("/send-code")
def send_code():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    if "@" not in email:
        return err("请输入有效的邮箱地址")
        
    if User.query.filter_by(email=email).first():
        return err("该邮箱已注册账号，请直接登录", status=409)
        
    code = str(random.randint(100000, 999999))
    expires = now() + timedelta(minutes=5)
    
    # 清理旧验证码并插入新验证码
    VerifyCode.query.filter_by(email=email).delete()
    vc = VerifyCode(email=email, code=code, expires_at=expires)
    db.session.add(vc)
    db.session.commit()
    
    if send_email_code(email, code):
        return ok(None, "验证码已发送，请注意查收")
    else:
        return err("验证码发送失败，请检查系统邮件配置", status=500)

# [前端对应]: 登录注册弹窗 (AuthModal.vue) -> "注册" 按钮/表单
# [业务逻辑]: 处理新用户注册并入库
@auth_bp.post("/register")
def register():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    role = (body.get("role") or "student").strip().lower()
    verify_code = (body.get("verify_code") or "").strip()
    invite_code = (body.get("invite_code") or "").strip()

    if role not in {"student", "teacher"}:
        return err("role 必须是 student/teacher")
    if len(username) < 2:
        return err("username 至少 2 位")
    if "@" not in email:
        return err("请输入有效的邮箱地址")
    if len(password) < 6:
        return err("password 至少 6 位")
    if not verify_code:
        return err("请输入邮箱验证码")

    if role == "teacher":
        if not invite_code:
            return err("注册教师账号需要提供专属邀请码")
        ic = TeacherInviteCode.query.filter_by(code=invite_code, is_used=False).first()
        if not ic or ic.expires_at < now():
            return err("无效或已过期的教师邀请码")

    # 查验验证码
    vc = VerifyCode.query.filter_by(email=email).first()
    if not vc or vc.code != verify_code:
        return err("验证码错误")
    if vc.expires_at < now():
        return err("验证码已过期，请重新获取")

    if User.query.filter_by(username=username).first():
        return err("用户名已存在", status=409)
    if User.query.filter_by(email=email).first():
        return err("该邮箱已被注册", status=409)

    u = User(
        username=username,
        email=email,
        status="active",
        password_hash=generate_password_hash(password),
        role=role,
        created_at=now(),
        updated_at=now()
    )
    db.session.add(u)
    db.session.commit()
    
    # 标记验证码和邀请码已使用
    db.session.delete(vc)
    if role == "teacher":
        ic = TeacherInviteCode.query.filter_by(code=invite_code).first()
        if ic:
            ic.is_used = True
            ic.used_by_id = u.id
    db.session.commit()

    return ok({"id": u.id, "username": u.username, "role": u.role}, "注册成功", status=201)


# [前端对应]: 教师端邀请码管理入口 -> 生成邀请码按钮
# [业务逻辑]: 教师生成 1 天有效期的邀请码并入库，供教师注册校验使用
@auth_bp.post("/generate-invite")
@jwt_required()
def generate_invite():
    u = current_user()
    if not is_teacher(u):
        return err("仅限教师生成邀请码", status=403)
    
    code = f"TCH-{uuid.uuid4().hex[:8].upper()}"
    expires = now() + timedelta(days=1)
    ic = TeacherInviteCode(code=code, expires_at=expires)
    db.session.add(ic)
    db.session.commit()
    
    return ok({"code": code, "expires_at": expires.isoformat()})

# [前端对应]: 登录注册弹窗 (AuthModal.vue) -> "登录" 按钮/表单
# [业务逻辑]: 验证用户身份并下发可跨越请求的 JWT Token
@auth_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    account = (body.get("username") or "").strip()
    password = body.get("password") or ""

    u = User.query.filter((User.username == account) | (User.email == account)).first()
    if not u or not check_password_hash(u.password_hash, password):
        return err("用户名/邮箱或密码错误", status=401)

    token = create_access_token(identity=str(u.id))
    return ok(
        {"token": token, "user": {"id": u.id, "username": u.username, "role": u.role}},
        "登录成功",
    )


# [前端对应]: 全局 (App.vue/router) -> 路由守卫/进入页面时初始化身份
# [业务逻辑]: 解析请求头里的 Token 来获取当前使用者的角色和基础信息
@user_bp.get("/me")
@jwt_required()
def me():
    u = current_user()
    if not u:
        return err("token无效或用户不存在", status=401)
    return ok({
        "id": u.id, 
        "username": u.username, 
        "role": u.role,
        "gender": getattr(u, 'gender', '未知'),
        "hobby": getattr(u, 'hobby', '')
    })

# [前端对应]: 个人中心 (ProfileView/AuthModal) -> 编辑个人资料并保存
# [业务逻辑]: 更新当前登录用户的用户名/性别/爱好，并进行用户名校验
@user_bp.patch("/me")
@jwt_required()
def update_profile():
    u = current_user()
    if not u:
        return err("请求未授权", status=401)
    
    data = request.json or {}
    new_username = data.get("username", "").strip()
    new_gender = data.get("gender", "").strip()
    new_hobby = data.get("hobby", "").strip()
    
    # 敏感词检查（优先读取 third_party/Sensitive-lexicon 词库，缺失时回退内置词表）
    if new_username:
        hit_word = find_sensitive_word(new_username)
        if hit_word:
            return err(f"用户名包含敏感词汇：{hit_word}", status=400)
                
        # 检查重名
        if new_username != u.username:
            exist = User.query.filter_by(username=new_username).first()
            if exist:
                return err("该名字已被其他用户使用", status=400)
            u.username = new_username
            
    if "gender" in data:
        u.gender = new_gender
    if "hobby" in data:
        u.hobby = new_hobby
        
    db.session.commit()
    return ok({
        "id": u.id, 
        "username": u.username, 
        "role": u.role,
        "gender": u.gender,
        "hobby": u.hobby
    }, "个人资料更新成功")


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
    uid = as_int(get_jwt_identity()) if get_jwt_identity() else None
    u = User.query.get(uid) if uid else None

    query = Course.query
    if u and is_teacher(u):
        query = query.filter((Course.status == "published") | ((Course.status == "draft") & (Course.teacher_id == u.id)))
    else:
        query = query.filter_by(status="published")

    courses = query.order_by(Course.id.desc()).all()
    return ok([serialize_course(c, u) for c in courses])


# [前端对应]: 课程详情页 (CourseDetailView.vue) -> 进入页面按课程 id 拉取详情
# [业务逻辑]: 返回单课程详情，草稿课程仅所属教师可访问
@course_bp.get("/<int:course_id>")
@jwt_required(optional=True)
def get_course(course_id):
    uid = as_int(get_jwt_identity()) if get_jwt_identity() else None
    u = User.query.get(uid) if uid else None

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

    if has_title:
        title = (body.get("title") or "").strip()
        if not title:
            return err("课程标题不能为空")
        c.title = title

    if has_desc:
        c.description = (body.get("description") or "").strip()

    c.updated_at = now()
    db.session.commit()
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
    viewed = Progress.query.filter(
        Progress.student_id == u.id,
        Progress.content_id.in_(c_ids)
    ).count()

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
            viewed = Progress.query.filter(
                Progress.student_id == student.id,
                Progress.content_id.in_(c_ids)
            ).count()
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
    return ok([serialize_content(x) for x in rows])


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
    f.save(full)

    # 不再硬编码 uploads/，直接保存文件名，因为我们在读取时会自动使用 upload_dir() 来查找
    rel = final_name
    title = (request.form.get("title") or "").strip() or safe
    
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
        
    # Check if existing review
    existing = Review.query.filter_by(course_id=course_id, user_id=u.id).first()
    if existing:
        return err("你已经评价过该课程，不能重复评价", status=400)
        
    body = request.get_json(silent=True) or {}
    rating = as_int(body.get("rating"))
    comment = (body.get("comment") or "").strip()
    
    if not rating or rating < 1 or rating > 5:
        return err("请输入1到5的有效星级评分", status=400)
        
    r = Review(
        course_id=course_id,
        user_id=u.id,
        rating=rating,
        comment=comment,
        created_at=now()
    )
    db.session.add(r)
    db.session.commit()

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

# ---------- analytics (数据大屏专用接口) ----------
# [前端对应]: 数据大屏统计看板界面 (DashboardView.vue) -> 进入页面时发送的初始图表报表请求
# [业务逻辑]: 按不同身份组装核心数据给图表：学生算全课进度，老师算全班人头基数和平均分大盘
@user_bp.get("/analytics")
@jwt_required()
def user_analytics():
    u = current_user()
    if not u:
        return err("仅允许登录用户调用", status=401)
        
    if is_student(u):
        # 学生端：按课程展示进度
        enrollments = Enrollment.query.filter_by(student_id=u.id).all()
        course_names = []
        progress_data = [] # 百分比
        completed_counts = []
        
        for en in enrollments:
            c = course_by_id(en.course_id)
            if c and c.status == "published":
                course_names.append(c.title)
                contents = Content.query.filter_by(course_id=c.id).all()
                total = len(contents)
                if total > 0:
                    c_ids = [ct.id for ct in contents]
                    viewed = Progress.query.filter(
                        Progress.student_id == u.id,
                        Progress.content_id.in_(c_ids)
                    ).count()
                    progress_data.append(int((viewed / total) * 100))
                    completed_counts.append(viewed)
                else:
                    progress_data.append(0)
                    completed_counts.append(0)
                    
        return ok({
            "role": "student",
            "courseNames": course_names,
            "progressRates": progress_data,
            "completedCounts": completed_counts
        })
        
    elif is_teacher(u):
        # 教师端：只展示"已发布"课程的选修人数分布
        courses = Course.query.filter_by(teacher_id=u.id, status="published").all()
        course_names = []
        enroll_counts = []
        review_averages = []
        
        total_students = 0
        
        for c in courses:
            course_names.append(c.title)
            
            # 选修人数统计
            c_enrolled = Enrollment.query.filter_by(course_id=c.id).count()
            enroll_counts.append(c_enrolled)
            total_students += c_enrolled
            
            # 平均评分统计
            reviews = Review.query.filter_by(course_id=c.id).all()
            avg = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
            review_averages.append(round(avg, 1))
            
        return ok({
            "role": "teacher",
            "courseNames": course_names,
            "enrollCounts": enroll_counts,
            "reviewAverages": review_averages,
            "totalStudents": total_students
        })
        
    return err("无权限访问大屏数据", status=403)


# ---------- upload helpers ----------

def upload_dir() -> Path:
    p = current_app.config.get("UPLOAD_DIR") or os.path.join(current_app.root_path, "uploads")
    p = Path(p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def allowed_ext(filename: str):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    allowed = {
        # 视频 (Video) - 通常浏览器支持 mp4, webm, ogg预览
        "mp4", "webm", "ogg", "mov", "avi",
        # 音频 (Audio) - 通常浏览器支持 mp3, ogg, wav预览
        "mp3", "wav", "flac", "aac", "m4a",
        # 图片 (Image) - 浏览器原生支持预览
        "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico",
        # 文档 (Document) - pdf可原生存预览，其余通常需下载或Office Web Viewer
        "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "csv", "md",
        # 压缩包等 (Archive)
        "zip", "rar", "7z", "tar", "gz"
    }
    return ext in allowed
