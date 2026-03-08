from __future__ import annotations

from datetime import datetime
import os
import uuid
import random
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.header import Header

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

from cache_utils import cache_delete, cache_get_json, cache_set_json, cache_ttl
from extensions import db
from models import User, Course, Enrollment, Content, Progress, Review, VerifyCode, TeacherInviteCode
from sensitive_filter import reject_sensitive_fields

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
user_bp = Blueprint("users", __name__, url_prefix="/api/users")

# 账号与个人资料相关接口模块（由原 routes_auth.py 拆分）

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


def is_admin(u: User):
    """判断用户是否为管理员。"""
    return role_of(u) == "admin"


def course_by_id(course_id: int):
    """按主键查询课程。"""
    return Course.query.get(course_id)


def normalize_verify_email(email: str):
    """统一验证码相关邮箱键，避免同一邮箱因空格导致缓存和数据库不一致。"""
    return (email or "").strip()


def verify_code_cache_key(email: str):
    """生成邮箱验证码缓存键。"""
    return f"verify:code:{normalize_verify_email(email)}"


def verify_code_cooldown_cache_key(email: str):
    """生成邮箱验证码发送冷却缓存键。"""
    return f"verify:cooldown:{normalize_verify_email(email)}"


def write_verify_code_cache(
    email: str,
    code: str,
    expires_at: datetime,
    cooldown_seconds: int = 0,
):
    """把验证码主数据和冷却时间一起写入 Redis。"""
    email = normalize_verify_email(email)
    ttl_seconds = max(1, int((expires_at - now()).total_seconds()))
    cache_set_json(
        verify_code_cache_key(email),
        {"email": email, "code": code, "expires_at": expires_at.isoformat()},
        ttl_seconds,
    )
    if cooldown_seconds > 0:
        cache_set_json(
            verify_code_cooldown_cache_key(email),
            {"email": email, "active": True},
            cooldown_seconds,
        )


def load_verify_code_record(email: str):
    """优先从 Redis 读取验证码，未命中时退回数据库兜底。"""
    email = normalize_verify_email(email)
    cached = cache_get_json(verify_code_cache_key(email))
    if cached:
        expires_at = cached.get("expires_at")
        code = cached.get("code")
        if expires_at and code:
            try:
                return {
                    "email": email,
                    "code": code,
                    "expires_at": datetime.fromisoformat(expires_at),
                }
            except ValueError:
                pass

    vc = VerifyCode.query.filter_by(email=email).first()
    if not vc:
        return None

    if vc.expires_at > now():
        write_verify_code_cache(email, vc.code, vc.expires_at)
    return {"email": email, "code": vc.code, "expires_at": vc.expires_at}


def clear_verify_code_record(email: str):
    """统一清理 Redis 和数据库中的验证码记录。"""
    email = normalize_verify_email(email)
    cache_delete(
        verify_code_cache_key(email),
        verify_code_cooldown_cache_key(email),
    )
    VerifyCode.query.filter_by(email=email).delete()


# 把教师邀请码模型转换成前端可直接消费的字段结构。
def serialize_invite_code(invite: TeacherInviteCode):
    """序列化教师端邀请码列表项。"""
    return {
        "id": invite.id,
        "code": invite.code,
        "is_used": bool(invite.is_used),
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
    }


# 生成一个数据库中未被占用的教师邀请码。
def build_teacher_invite_code():
    """生成不重复的教师邀请码字符串。"""
    code = f"TCH-{uuid.uuid4().hex[:8].upper()}"
    while TeacherInviteCode.query.filter_by(code=code).first():
        code = f"TCH-{uuid.uuid4().hex[:8].upper()}"
    return code

def analytics_cache_key(user_id: int):
    """按用户维度区分数据总览缓存，避免不同账号读到彼此的统计结果。"""
    return f"analytics:user:{user_id}"


def invalidate_admin_overview_cache():
    """账号数量或邀请码数量变动后，清理管理员首页统计卡片缓存。"""
    cache_delete("admin:overview")



# ---------- auth ----------

PASSWORD_VERIFY_CODE_EXPIRE_MINUTES = 2
PASSWORD_VERIFY_CODE_COOLDOWN_SECONDS = 60


def send_email_code(email: str, code: str, scene_name: str = "账号注册", valid_minutes: int = 5):
    """发送邮箱验证码；未配置邮件服务时退化为控制台打印。"""
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
        msg = MIMEText(f"【智能学习网站】您的{scene_name}验证码为：{code}，{valid_minutes}分钟内有效。", 'plain', 'utf-8')
        msg['From'] = formataddr((str(Header("学习平台", 'utf-8')), mail_user))
        msg['To'] = email
        msg['Subject'] = Header(f"{scene_name}验证码", 'utf-8')

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


def upsert_verify_code(email: str, expire_minutes: int, cooldown_seconds: int = 0):
    """统一写入验证码到 Redis，并保留数据库记录作为兜底。"""
    email = normalize_verify_email(email)
    code = str(random.randint(100000, 999999))
    expires = now() + timedelta(minutes=expire_minutes)
    write_verify_code_cache(email, code, expires, cooldown_seconds=cooldown_seconds)
    VerifyCode.query.filter_by(email=email).delete()
    db.session.add(VerifyCode(email=email, code=code, expires_at=expires))
    db.session.commit()
    return code, expires


def password_code_cooldown_left_seconds(email: str):
    """优先读取 Redis 冷却剩余时间，数据库仅作为兼容兜底。"""
    email = normalize_verify_email(email)
    cooldown_left = cache_ttl(verify_code_cooldown_cache_key(email))
    if cooldown_left > 0:
        return cooldown_left

    vc = VerifyCode.query.filter_by(email=email).first()
    if not vc:
        return 0
    remaining = int((vc.expires_at - now()).total_seconds())
    fallback_left = max(0, remaining - PASSWORD_VERIFY_CODE_COOLDOWN_SECONDS)
    if fallback_left > 0:
        cache_set_json(
            verify_code_cooldown_cache_key(email),
            {"email": email, "active": True},
            fallback_left,
        )
    return fallback_left

# [前端对应]: 登录注册弹窗 (AuthModal.vue) -> 点击“发送验证码”
# [业务逻辑]: 生成并保存邮箱验证码，写入过期时间并尝试发送邮件
@auth_bp.post("/send-code")
def send_code():
    body = request.get_json(silent=True) or {}
    email = normalize_verify_email(body.get("email") or "")
    if "@" not in email:
        return err("请输入有效的邮箱地址")
        
    if User.query.filter_by(email=email).first():
        return err("该邮箱已注册账号，请直接登录", status=409)
        
    code, _ = upsert_verify_code(email, expire_minutes=5)
    
    if send_email_code(email, code, scene_name="账号注册", valid_minutes=5):
        return ok(None, "验证码已发送，请注意查收")
    else:
        return err("验证码发送失败，请检查系统邮件配置", status=500)

# [前端对应]: 登录注册弹窗 (AuthModal.vue) -> "注册" 按钮/表单
# [业务逻辑]: 处理新用户注册并入库
@auth_bp.post("/register")
def register():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    email = normalize_verify_email(body.get("email") or "")
    password = body.get("password") or ""
    role = (body.get("role") or "student").strip().lower()
    verify_code = (body.get("verify_code") or "").strip()
    invite_code = (body.get("invite_code") or "").strip()
    invite_record = None

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

    sensitive_err = reject_sensitive_fields({"用户名": username}, err, scene="content")
    if sensitive_err:
        return sensitive_err

    if role == "teacher":
        if not invite_code:
            return err("注册教师账号需要提供专属邀请码")
        # 锁定未使用的邀请码记录，确保同一个邀请码不会被并发注册重复消费。
        invite_record = (
            TeacherInviteCode.query
            .filter_by(code=invite_code, is_used=False)
            .with_for_update()
            .first()
        )
        if not invite_record or invite_record.expires_at < now():
            return err("无效或已过期的教师邀请码")

    # 查验验证码
    vc = load_verify_code_record(email)
    if not vc or vc["code"] != verify_code:
        return err("验证码错误")
    if vc["expires_at"] < now():
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
    db.session.flush()
    
    # 标记验证码和邀请码已使用，并与用户创建保持同一笔提交。
    clear_verify_code_record(email)
    if role == "teacher" and invite_record:
        invite_record.is_used = True
        invite_record.used_by_id = u.id
    db.session.commit()
    invalidate_admin_overview_cache()

    return ok({"id": u.id, "username": u.username, "role": u.role}, "注册成功", status=201)


# [前端对应]: 教师端邀请码管理入口 -> 生成邀请码按钮
# [业务逻辑]: 教师生成 1 天有效期的邀请码并入库，供教师注册校验使用
@auth_bp.post("/generate-invite")
@jwt_required()
def generate_invite():
    u = current_user()
    if not is_teacher(u):
        return err("仅限教师生成邀请码", status=403)

    code = build_teacher_invite_code()
    expires = now() + timedelta(days=1)
    ic = TeacherInviteCode(code=code, expires_at=expires, created_by_id=u.id)
    db.session.add(ic)
    db.session.commit()
    invalidate_admin_overview_cache()

    return ok(serialize_invite_code(ic), "邀请码生成成功")


# [前端对应]: 教师首页 (HomeView.vue) -> 邀请码弹窗打开/刷新时读取当前仍可使用的邀请码
# [业务逻辑]: 只返回当前教师创建、未使用且未过期的邀请码，便于刷新页面后继续查看和分发
@auth_bp.get("/invite-codes")
@jwt_required()
def list_my_invite_codes():
    u = current_user()
    if not is_teacher(u):
        return err("仅限教师查看邀请码", status=403)

    invite_codes = (
        TeacherInviteCode.query
        .filter(TeacherInviteCode.is_used.is_(False))
        .filter(
            or_(
                TeacherInviteCode.created_by_id == u.id,
                TeacherInviteCode.created_by_id.is_(None),
            )
        )
        .filter(TeacherInviteCode.expires_at >= now())
        .order_by(TeacherInviteCode.expires_at.desc(), TeacherInviteCode.id.desc())
        .all()
    )
    return ok({"items": [serialize_invite_code(code) for code in invite_codes]})


# [前端对应]: 登录注册弹窗 (AuthModal.vue) -> 输入账号密码后点击“登录”
# [业务逻辑]: 支持用户名或邮箱登录，校验密码与账号状态后签发 JWT
@auth_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    account = (body.get("username") or "").strip()
    password = body.get("password") or ""

    u = User.query.filter((User.username == account) | (User.email == account)).first()
    if not u or not check_password_hash(u.password_hash, password):
        return err("用户名/邮箱或密码错误", status=401)

    if u.status != "active":
        return err("账号已被停用", status=403)
    token = create_access_token(identity=str(u.id))
    return ok(
        {"token": token, "user": {"id": u.id, "username": u.username, "role": u.role}},
        "登录成功",
    )


# [前端对应]: 登录弹窗 (AuthModal.vue) -> 登录页内“忘记密码”发送验证码
# [业务逻辑]: 给已注册邮箱发送重置密码验证码（2分钟有效，60秒内不可重复发送）
@auth_bp.post("/send-reset-code")
def send_reset_code():
    body = request.get_json(silent=True) or {}
    email = normalize_verify_email(body.get("email") or "")
    if "@" not in email:
        return err("请输入有效的邮箱地址")

    user = User.query.filter_by(email=email).first()
    if not user:
        return err("该邮箱未注册账号", status=404)

    cooldown_left = password_code_cooldown_left_seconds(email)
    if cooldown_left > 0:
        return err(f"验证码发送过于频繁，请{cooldown_left}秒后再试", status=429)

    code, _ = upsert_verify_code(
        email,
        expire_minutes=PASSWORD_VERIFY_CODE_EXPIRE_MINUTES,
        cooldown_seconds=PASSWORD_VERIFY_CODE_COOLDOWN_SECONDS,
    )
    if send_email_code(
        email,
        code,
        scene_name="找回密码",
        valid_minutes=PASSWORD_VERIFY_CODE_EXPIRE_MINUTES,
    ):
        return ok(
            {"expires_seconds": PASSWORD_VERIFY_CODE_EXPIRE_MINUTES * 60, "cooldown_seconds": PASSWORD_VERIFY_CODE_COOLDOWN_SECONDS},
            "验证码已发送，请注意查收",
        )
    return err("验证码发送失败，请检查系统邮件配置", status=500)


# [前端对应]: 登录弹窗 (AuthModal.vue) -> 忘记密码页提交“验证码 + 新密码”
# [业务逻辑]: 校验邮箱验证码后，重置目标账号密码
@auth_bp.post("/reset-password")
def reset_password():
    body = request.get_json(silent=True) or {}
    email = normalize_verify_email(body.get("email") or "")
    verify_code = (body.get("verify_code") or "").strip()
    new_password = body.get("new_password") or ""

    if "@" not in email:
        return err("请输入有效的邮箱地址")
    if not verify_code:
        return err("请输入邮箱验证码")
    if len(new_password) < 6:
        return err("新密码至少 6 位")

    user = User.query.filter_by(email=email).first()
    if not user:
        return err("该邮箱未注册账号", status=404)

    vc = load_verify_code_record(email)
    if not vc or vc["code"] != verify_code:
        return err("验证码错误")
    if vc["expires_at"] < now():
        return err("验证码已过期，请重新获取")

    user.password_hash = generate_password_hash(new_password)
    user.updated_at = now()
    clear_verify_code_record(email)
    db.session.commit()
    return ok(None, "密码重置成功，请使用新密码登录")


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
        "email": u.email,
        "role": u.role,
        "status": u.status,
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
    
    sensitive_err = reject_sensitive_fields(
        {"用户名": new_username, "个人简介": new_hobby},
        err,
        scene="content",
    )
    if sensitive_err:
        return sensitive_err

    if new_username:
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
        "email": u.email,
        "role": u.role,
        "status": u.status,
        "gender": u.gender,
        "hobby": u.hobby
    }, "个人资料更新成功")


# [前端对应]: 个人中心 (ProfileView.vue) -> 点击“发送验证码”用于修改密码
# [业务逻辑]: 给当前登录用户邮箱发送修改密码验证码（2分钟有效，60秒内不可重复发送）
@user_bp.post("/me/password-code")
@jwt_required()
def send_my_password_code():
    u = current_user()
    if not u:
        return err("请求未授权", status=401)

    cooldown_left = password_code_cooldown_left_seconds(u.email)
    if cooldown_left > 0:
        return err(f"验证码发送过于频繁，请{cooldown_left}秒后再试", status=429)

    code, _ = upsert_verify_code(
        u.email,
        expire_minutes=PASSWORD_VERIFY_CODE_EXPIRE_MINUTES,
        cooldown_seconds=PASSWORD_VERIFY_CODE_COOLDOWN_SECONDS,
    )
    if send_email_code(
        u.email,
        code,
        scene_name="修改密码",
        valid_minutes=PASSWORD_VERIFY_CODE_EXPIRE_MINUTES,
    ):
        return ok(
            {"expires_seconds": PASSWORD_VERIFY_CODE_EXPIRE_MINUTES * 60, "cooldown_seconds": PASSWORD_VERIFY_CODE_COOLDOWN_SECONDS},
            "验证码已发送，请注意查收",
        )
    return err("验证码发送失败，请检查系统邮件配置", status=500)


# [前端对应]: 个人中心 (ProfileView.vue) -> 填写验证码后提交新密码
# [业务逻辑]: 校验当前账号邮箱验证码，通过后更新密码哈希
@user_bp.patch("/me/password")
@jwt_required()
def change_my_password():
    u = current_user()
    if not u:
        return err("请求未授权", status=401)

    body = request.get_json(silent=True) or {}
    verify_code = (body.get("verify_code") or "").strip()
    new_password = body.get("new_password") or ""

    if not verify_code:
        return err("请输入邮箱验证码")
    if len(new_password) < 6:
        return err("新密码至少 6 位")

    vc = load_verify_code_record(u.email)
    if not vc or vc["code"] != verify_code:
        return err("验证码错误")
    if vc["expires_at"] < now():
        return err("验证码已过期，请重新获取")

    u.password_hash = generate_password_hash(new_password)
    u.updated_at = now()
    clear_verify_code_record(u.email)
    db.session.commit()
    return ok(None, "密码修改成功")



# ---------- analytics (数据大屏专用接口) ----------
# [前端对应]: 数据大屏统计看板界面 (DashboardView.vue) -> 进入页面时发送的初始图表报表请求
# [业务逻辑]: 按不同身份组装核心数据给图表：学生算全课进度，老师算全班人头基数和平均分大盘
@user_bp.get("/analytics")
@jwt_required()
def user_analytics():
    u = current_user()
    if not u:
        return err("仅允许登录用户调用", status=401)

    cache_key = analytics_cache_key(u.id)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return ok(cached)

    if is_student(u):
        # 学生端：按课程展示进度
        enrollments = Enrollment.query.filter_by(student_id=u.id).all()
        course_names = []
        course_ids = []
        progress_data = [] # 百分比
        completed_counts = []
        
        for en in enrollments:
            c = course_by_id(en.course_id)
            if c and c.status == "published":
                course_names.append(c.title)
                course_ids.append(c.id)
                contents = Content.query.filter_by(course_id=c.id).all()
                total = len(contents)
                if total > 0:
                    c_ids = [ct.id for ct in contents]
                    # 数据总览按不同课件去重统计，和课程详情页进度口径保持一致。
                    viewed = (
                        db.session.query(Progress.content_id)
                        .filter(
                            Progress.student_id == u.id,
                            Progress.content_id.in_(c_ids),
                        )
                        .distinct()
                        .count()
                    )
                    progress_data.append(int((viewed / total) * 100))
                    completed_counts.append(viewed)
                else:
                    progress_data.append(0)
                    completed_counts.append(0)
                    
        data = {
            "role": "student",
            "courseNames": course_names,
            "courseIds": course_ids,
            "progressRates": progress_data,
            "completedCounts": completed_counts
        }
        cache_set_json(cache_key, data, ttl_seconds=60)
        return ok(data)
        
    elif is_teacher(u):
        # 教师端：只展示"已发布"课程的选修人数分布
        courses = Course.query.filter_by(teacher_id=u.id, status="published").all()
        course_names = []
        course_ids = []
        enroll_counts = []
        review_averages = []
        
        total_students = 0
        
        for c in courses:
            course_names.append(c.title)
            course_ids.append(c.id)
            
            # 选修人数统计
            c_enrolled = Enrollment.query.filter_by(course_id=c.id).count()
            enroll_counts.append(c_enrolled)
            total_students += c_enrolled
            
            # 平均评分统计
            reviews = Review.query.filter_by(course_id=c.id).all()
            avg = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
            review_averages.append(round(avg, 1))
            
        data = {
            "role": "teacher",
            "courseNames": course_names,
            "courseIds": course_ids,
            "enrollCounts": enroll_counts,
            "reviewAverages": review_averages,
            "totalStudents": total_students
        }
        cache_set_json(cache_key, data, ttl_seconds=60)
        return ok(data)
        
    return err("无权限访问大屏数据", status=403)
