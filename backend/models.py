from datetime import datetime
from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # student/teacher
    status = db.Column(db.String(20), nullable=False, default="active")
    gender = db.Column(db.String(10), default="未知")
    hobby = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft/published
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="enrolled")  # enrolled/dropped
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)


class Content(db.Model):
    __tablename__ = "contents"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)  # video/doc/quiz/other
    title = db.Column(db.String(255), nullable=False)
    url_or_path = db.Column(db.String(500), nullable=False)
    duration_seconds = db.Column(db.Integer)
    size_bytes = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Progress(db.Model):
    __tablename__ = "progress"

    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    progress_percent = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="not_started")  # not_started/in_progress/completed
    last_viewed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reply_content = db.Column(db.Text, nullable=True)
    reply_time = db.Column(db.DateTime, nullable=True)
    likes_count = db.Column(db.Integer, default=0)

class ReviewLike(db.Model):
    __tablename__ = "review_likes"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('review_id', 'user_id', name='uq_review_user_like'),)

class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

class VerifyCode(db.Model):
    __tablename__ = "verify_codes"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, nullable=False)
    code = db.Column(db.String(10), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

class TeacherInviteCode(db.Model):
    __tablename__ = "teacher_invite_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
