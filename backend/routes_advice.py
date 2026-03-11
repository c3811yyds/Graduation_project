from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from extensions import db
from models import Content, Course, Enrollment, Progress, Review, User
from routes_account import current_user, err, is_admin, is_student, is_teacher, now, ok

advice_bp = Blueprint("advice", __name__, url_prefix="/api/users")


def build_advice_stat(label: str, value):
    """统一生成前端可直接消费的统计卡片。"""
    return {"label": label, "value": value}


def build_advice_item(title: str, description: str, action_label: str = "", action_path: str = ""):
    """统一生成建议项结构，方便总览页和 AI 侧栏复用。"""
    return {
        "title": title,
        "description": description,
        "action_label": action_label,
        "action_path": action_path,
    }


def build_focus_card(
    title: str,
    description: str,
    action_label: str = "",
    action_path: str = "",
    course_id: int | None = None,
):
    """突出展示当前最值得优先处理的一条建议。"""
    return {
        "title": title,
        "description": description,
        "action_label": action_label,
        "action_path": action_path,
        "course_id": course_id,
    }


def build_student_learning_advice(user: User):
    """基于学生的选课和进度生成下一步学习建议。"""
    enrollment_rows = (
        db.session.query(Enrollment.course_id, Course.title, Enrollment.enrolled_at)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(
            Enrollment.student_id == user.id,
            Enrollment.status == "enrolled",
            Course.status == "published",
        )
        .order_by(Enrollment.enrolled_at.asc(), Enrollment.id.asc())
        .all()
    )

    if not enrollment_rows:
        hot_course = (
            db.session.query(Course.id, Course.title, func.count(Enrollment.id).label("enroll_count"))
            .outerjoin(
                Enrollment,
                (Enrollment.course_id == Course.id) & (Enrollment.status == "enrolled"),
            )
            .filter(Course.status == "published")
            .group_by(Course.id, Course.title)
            .order_by(func.count(Enrollment.id).desc(), Course.id.desc())
            .first()
        )

        recommendations = [
            build_advice_item(
                "先从一门公开课程开始",
                "你当前还没有选修课程，建议先进入课程大厅选择一门感兴趣的课程开始学习。",
                "去课程大厅",
                "/",
            )
        ]
        if hot_course:
            recommendations.append(
                build_advice_item(
                    f"可优先体验《{hot_course.title}》",
                    "这门课当前较受欢迎，适合作为第一门体验课程。",
                    "查看课程",
                    f"/courses/{hot_course.id}",
                )
            )

        return {
            "role": "student",
            "headline": "当前还没有学习记录，建议先选修一门课程开始学习",
            "summary": "系统会在你产生选课和学习进度后，持续给出下一步学习建议。",
            "stats": [
                build_advice_stat("已选课程", "0 门"),
                build_advice_stat("推进中", "0 门"),
                build_advice_stat("已完成", "0 门"),
                build_advice_stat("待开始", "0 门"),
            ],
            "focus": build_focus_card(
                "先建立第一条学习轨迹",
                "建议先从课程大厅挑选一门课程，后续系统会根据你的进度自动给出更具体的个性化建议。",
                "去课程大厅",
                "/",
            ),
            "recommendations": recommendations,
        }

    course_meta = {
        row.course_id: {
            "course_id": row.course_id,
            "course_title": row.title,
            "enrolled_at": row.enrolled_at,
        }
        for row in enrollment_rows
    }
    course_ids = list(course_meta.keys())

    content_totals = dict(
        db.session.query(Content.course_id, func.count(Content.id))
        .filter(Content.course_id.in_(course_ids))
        .group_by(Content.course_id)
        .all()
    )

    progress_rows = {
        row.course_id: row
        for row in (
            db.session.query(
                Content.course_id.label("course_id"),
                func.count(func.distinct(Progress.content_id)).label("viewed_count"),
                func.max(Progress.last_viewed_at).label("last_viewed_at"),
            )
            .join(Progress, Progress.content_id == Content.id)
            .filter(
                Progress.student_id == user.id,
                Content.course_id.in_(course_ids),
            )
            .group_by(Content.course_id)
            .all()
        )
    }

    learned_ids = {
        content_id
        for (content_id,) in db.session.query(Progress.content_id)
        .join(Content, Content.id == Progress.content_id)
        .filter(
            Progress.student_id == user.id,
            Content.course_id.in_(course_ids),
        )
        .all()
    }

    next_content_map = {}
    for content in (
        Content.query.filter(Content.course_id.in_(course_ids))
        .order_by(Content.course_id.asc(), Content.id.asc())
        .all()
    ):
        if content.course_id not in next_content_map and content.id not in learned_ids:
            next_content_map[content.course_id] = content.title

    current_time = now()
    course_states = []
    for course_id in course_ids:
        meta = course_meta[course_id]
        total = int(content_totals.get(course_id, 0) or 0)
        progress_row = progress_rows.get(course_id)
        viewed = int(getattr(progress_row, "viewed_count", 0) or 0)
        last_viewed_at = getattr(progress_row, "last_viewed_at", None)
        progress_pct = int((viewed / total) * 100) if total > 0 else 0
        days_idle = None
        if last_viewed_at:
            days_idle = max(0, (current_time - last_viewed_at).days)

        if total == 0:
            stage = "waiting_content"
        elif progress_pct >= 100:
            stage = "completed"
        elif progress_pct > 0:
            stage = "in_progress"
        else:
            stage = "not_started"

        course_states.append(
            {
                **meta,
                "total": total,
                "viewed": viewed,
                "progress": progress_pct,
                "last_viewed_at": last_viewed_at,
                "days_idle": days_idle,
                "stage": stage,
                "next_content_title": next_content_map.get(course_id),
            }
        )

    waiting_content_count = sum(1 for item in course_states if item["stage"] == "waiting_content")
    completed_courses = [item for item in course_states if item["stage"] == "completed"]
    in_progress_courses = [item for item in course_states if item["stage"] == "in_progress"]
    not_started_courses = [item for item in course_states if item["stage"] == "not_started"]
    stalled_courses = [
        item for item in in_progress_courses if item["days_idle"] is not None and item["days_idle"] >= 3
    ]
    nearly_done_courses = [item for item in in_progress_courses if item["progress"] >= 80]

    focus = None
    if stalled_courses:
        focus = sorted(
            stalled_courses,
            key=lambda item: (item["days_idle"] or 0, item["progress"]),
            reverse=True,
        )[0]
        headline = f"建议优先恢复学习《{focus['course_title']}》"
        focus_card = build_focus_card(
            f"优先恢复学习《{focus['course_title']}》",
            (
                f"这门课已中断 {focus['days_idle']} 天，当前进度 {focus['progress']}%。"
                f"{' 下一步建议先学习《' + focus['next_content_title'] + '》。' if focus['next_content_title'] else ' 建议先回到课程详情继续推进。'}"
            ),
            "进入课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    elif nearly_done_courses:
        focus = sorted(nearly_done_courses, key=lambda item: item["progress"], reverse=True)[0]
        headline = f"建议优先完成《{focus['course_title']}》的学习"
        focus_card = build_focus_card(
            f"优先完成《{focus['course_title']}》的学习",
            (
                f"这门课已完成 {focus['progress']}%，再补完剩余内容就能形成一门完整学习成果。"
                f"{' 可优先学习《' + focus['next_content_title'] + '》。' if focus['next_content_title'] else ''}"
            ),
            "进入课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    elif in_progress_courses:
        focus = sorted(in_progress_courses, key=lambda item: item["progress"], reverse=True)[0]
        headline = f"建议继续学习《{focus['course_title']}》"
        focus_card = build_focus_card(
            f"继续学习《{focus['course_title']}》",
            (
                f"当前进度 {focus['progress']}%，已经形成连续学习轨迹。"
                f"{' 下一步可继续《' + focus['next_content_title'] + '》。' if focus['next_content_title'] else ' 建议保持学习节奏。'}"
            ),
            "进入课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    elif not_started_courses:
        focus = sorted(not_started_courses, key=lambda item: item["enrolled_at"] or current_time)[0]
        headline = f"建议开始学习《{focus['course_title']}》"
        focus_card = build_focus_card(
            f"开始第一节《{focus['course_title']}》",
            "这门课已选修但尚未开始，建议尽快进入课程建立第一条学习进度记录。",
            "进入课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    else:
        headline = "当前已完成全部已选课程，可开始复盘或选修新课程"
        focus_card = build_focus_card(
            "已完成当前全部学习任务",
            "你已完成当前已选课程，可进入课程大厅继续选修新课程，或回顾已完成课程巩固知识。",
            "去课程大厅",
            "/",
        )

    summary_parts = [
        f"已选修 {len(course_states)} 门课程",
        f"推进中 {len(in_progress_courses)} 门",
        f"已完成 {len(completed_courses)} 门",
        f"待开始 {len(not_started_courses)} 门",
    ]
    if waiting_content_count:
        summary_parts.append(f"另有 {waiting_content_count} 门课程暂未上传课件")
    summary = "，".join(summary_parts) + "。"

    recommendations = []
    if focus:
        next_content = (
            f"，建议下一步优先学习《{focus['next_content_title']}》"
            if focus.get("next_content_title")
            else ""
        )
        recommendations.append(
            build_advice_item(
                f"优先学习《{focus['course_title']}》",
                f"当前进度 {focus['progress']}%{next_content}。",
                "进入课程",
                f"/courses/{focus['course_id']}",
            )
        )

    if stalled_courses and (not focus or focus["course_id"] != stalled_courses[0]["course_id"]):
        stalled = sorted(stalled_courses, key=lambda item: item["days_idle"] or 0, reverse=True)[0]
        recommendations.append(
            build_advice_item(
                "恢复一门停滞课程",
                f"《{stalled['course_title']}》已中断 {stalled['days_idle']} 天，建议本周优先恢复学习。",
                "进入课程",
                f"/courses/{stalled['course_id']}",
            )
        )

    if not_started_courses:
        waiting = sorted(not_started_courses, key=lambda item: item["enrolled_at"] or current_time)[0]
        recommendations.append(
            build_advice_item(
                "启动一门未开始课程",
                f"《{waiting['course_title']}》尚未开始，建议尽快完成第一节内容，建立连续学习节奏。",
                "进入课程",
                f"/courses/{waiting['course_id']}",
            )
        )
    elif completed_courses:
        finished = sorted(completed_courses, key=lambda item: item["progress"], reverse=True)[0]
        recommendations.append(
            build_advice_item(
                "安排一次课程复盘",
                f"你已完成《{finished['course_title']}》，建议回看重点内容或结合笔记做一次知识复盘。",
                "查看课程",
                f"/courses/{finished['course_id']}",
            )
        )

    return {
        "role": "student",
        "headline": headline,
        "summary": summary,
        "stats": [
            build_advice_stat("已选课程", f"{len(course_states)} 门"),
            build_advice_stat("推进中", f"{len(in_progress_courses)} 门"),
            build_advice_stat("已完成", f"{len(completed_courses)} 门"),
            build_advice_stat("待开始", f"{len(not_started_courses)} 门"),
        ],
        "focus": focus_card,
        "recommendations": recommendations[:3],
    }


def build_teacher_learning_advice(user: User):
    """基于教师课程运行情况生成教学优化建议。"""
    courses = (
        Course.query.filter_by(teacher_id=user.id)
        .order_by(Course.updated_at.desc(), Course.id.desc())
        .all()
    )

    if not courses:
        return {
            "role": "teacher",
            "headline": "当前还没有课程，建议先创建第一门课程",
            "summary": "创建课程并上传课件后，系统会继续根据学生学习情况生成教学建议。",
            "stats": [
                build_advice_stat("课程总数", "0 门"),
                build_advice_stat("已发布", "0 门"),
                build_advice_stat("草稿箱", "0 门"),
                build_advice_stat("在学人数", "0 人"),
            ],
            "focus": build_focus_card(
                "先创建第一门课程",
                "建议先创建课程并补充课件内容，后续系统会根据选课、进度和评价提供更具体的运营建议。",
                "返回首页",
                "/",
            ),
            "recommendations": [
                build_advice_item(
                    "从一门核心课程开始",
                    "先搭建一门结构完整的课程，更容易快速形成可对外发布的教学内容。",
                    "返回首页",
                    "/",
                )
            ],
        }

    course_ids = [course.id for course in courses]
    content_counts = dict(
        db.session.query(Content.course_id, func.count(Content.id))
        .filter(Content.course_id.in_(course_ids))
        .group_by(Content.course_id)
        .all()
    )
    enroll_counts = dict(
        db.session.query(Enrollment.course_id, func.count(Enrollment.id))
        .filter(
            Enrollment.course_id.in_(course_ids),
            Enrollment.status == "enrolled",
        )
        .group_by(Enrollment.course_id)
        .all()
    )
    review_avg_map = dict(
        db.session.query(Review.course_id, func.avg(Review.rating))
        .filter(Review.course_id.in_(course_ids))
        .group_by(Review.course_id)
        .all()
    )
    total_progress_rows = dict(
        db.session.query(Content.course_id, func.count(Progress.id))
        .join(Progress, Progress.content_id == Content.id)
        .filter(Content.course_id.in_(course_ids))
        .group_by(Content.course_id)
        .all()
    )

    course_stats = []
    for course in courses:
        content_count = int(content_counts.get(course.id, 0) or 0)
        enroll_count = int(enroll_counts.get(course.id, 0) or 0)
        review_avg = round(float(review_avg_map.get(course.id, 0) or 0), 1)
        total_progress = int(total_progress_rows.get(course.id, 0) or 0)
        avg_progress = 0
        if course.status == "published" and content_count > 0 and enroll_count > 0:
            avg_progress = min(100, int((total_progress / (content_count * enroll_count)) * 100))

        course_stats.append(
            {
                "course_id": course.id,
                "course_title": course.title,
                "status": course.status,
                "content_count": content_count,
                "enroll_count": enroll_count,
                "review_avg": review_avg,
                "avg_progress": avg_progress,
            }
        )

    published_courses = [item for item in course_stats if item["status"] == "published"]
    draft_courses = [item for item in course_stats if item["status"] == "draft"]
    low_progress_courses = [
        item for item in published_courses if item["enroll_count"] > 0 and item["avg_progress"] < 40
    ]
    low_enroll_courses = [item for item in published_courses if item["enroll_count"] <= 1]

    progress_capacity = sum(
        item["content_count"] * item["enroll_count"]
        for item in published_courses
        if item["content_count"] > 0 and item["enroll_count"] > 0
    )
    overall_student_progress = 0
    if progress_capacity > 0:
        overall_student_progress = int(
            (
                sum(
                    item["avg_progress"] * item["content_count"] * item["enroll_count"]
                    for item in published_courses
                    if item["content_count"] > 0 and item["enroll_count"] > 0
                )
            )
            / progress_capacity
        )

    if low_progress_courses:
        focus = sorted(low_progress_courses, key=lambda item: item["avg_progress"])[0]
        headline = f"建议优先关注《{focus['course_title']}》的学生学习进展"
        focus_card = build_focus_card(
            f"重点跟进《{focus['course_title']}》的学生学习进展",
            f"当前学生平均学习进度仅 {focus['avg_progress']}%，建议补充过渡说明、重点提示或优化课件结构，帮助学生更顺利完成学习。",
            "查看课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    elif draft_courses:
        focus = sorted(draft_courses, key=lambda item: (item["content_count"], item["course_id"]))[0]
        headline = f"建议优先完善《{focus['course_title']}》这门草稿课程"
        focus_card = build_focus_card(
            f"优先完善《{focus['course_title']}》这门草稿课程",
            f"当前已上传 {focus['content_count']} 份课件，建议补齐课程结构后尽快发布，形成稳定教学入口。",
            "查看课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    elif low_enroll_courses:
        focus = sorted(low_enroll_courses, key=lambda item: item["enroll_count"])[0]
        headline = f"建议提升《{focus['course_title']}》的吸引力"
        focus_card = build_focus_card(
            f"优化《{focus['course_title']}》的选课吸引力",
            f"当前仅有 {focus['enroll_count']} 名学生选修，建议补充课程简介亮点、优化课件封面与目录结构。",
            "查看课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    else:
        best_course = None
        if published_courses:
            best_course = sorted(
                published_courses,
                key=lambda item: (item["enroll_count"], item["review_avg"], item["avg_progress"]),
                reverse=True,
            )[0]
        headline = "当前课程整体运行平稳，可继续优化课程质量"
        if best_course:
            focus_card = build_focus_card(
                f"保持课程运营节奏：重点课程《{best_course['course_title']}》",
                f"该课程当前选课 {best_course['enroll_count']} 人，评价 {best_course['review_avg']} 分，可作为后续课程优化参考。",
                "查看课程",
                f"/courses/{best_course['course_id']}",
                best_course["course_id"],
            )
        else:
            focus_card = build_focus_card(
                "保持课程运营节奏",
                f"当前已发布 {len(published_courses)} 门课程，建议持续关注选课与评价数据变化。",
                "返回首页",
                "/",
            )

    total_students = sum(item["enroll_count"] for item in published_courses)
    recommendations = []
    if draft_courses:
        draft = sorted(draft_courses, key=lambda item: (item["content_count"], item["course_id"]))[0]
        recommendations.append(
            build_advice_item(
                "优先处理草稿课程",
                f"《{draft['course_title']}》仍在草稿箱，建议补齐关键课件后尽快发布。",
                "查看课程",
                f"/courses/{draft['course_id']}",
            )
        )
    if low_progress_courses:
        low_progress = sorted(low_progress_courses, key=lambda item: item["avg_progress"])[0]
        recommendations.append(
            build_advice_item(
                "关注低进度课程",
                f"《{low_progress['course_title']}》当前学生平均学习进度仅 {low_progress['avg_progress']}%，建议增加引导说明或拆分难点内容。",
                "查看课程",
                f"/courses/{low_progress['course_id']}",
            )
        )
    if low_enroll_courses:
        low_enroll = sorted(low_enroll_courses, key=lambda item: item["enroll_count"])[0]
        recommendations.append(
            build_advice_item(
                "提升课程吸引力",
                f"《{low_enroll['course_title']}》当前仅有 {low_enroll['enroll_count']} 名学生选修，可优先优化课程简介与课件封面。",
                "查看课程",
                f"/courses/{low_enroll['course_id']}",
            )
        )

    return {
        "role": "teacher",
        "headline": headline,
        "summary": (
            f"你当前共维护 {len(course_stats)} 门课程，其中已发布 {len(published_courses)} 门、草稿 {len(draft_courses)} 门，"
            f"累计服务 {total_students} 名在学学生。"
        ),
        "stats": [
            build_advice_stat("课程总数", f"{len(course_stats)} 门"),
            build_advice_stat("已发布", f"{len(published_courses)} 门"),
            build_advice_stat("草稿箱", f"{len(draft_courses)} 门"),
            build_advice_stat("在学人数", f"{total_students} 人"),
            build_advice_stat("学生平均进展", f"{overall_student_progress}%"),
        ],
        "focus": focus_card,
        "recommendations": recommendations[:3],
    }


def build_admin_learning_advice():
    """基于平台数据生成管理员视角的运营建议。"""
    teacher_count = User.query.filter_by(role="teacher", status="active").count()
    student_count = User.query.filter_by(role="student", status="active").count()
    courses = Course.query.order_by(Course.updated_at.desc(), Course.id.desc()).all()
    course_ids = [course.id for course in courses]

    content_counts = {}
    enroll_counts = {}
    if course_ids:
        content_counts = dict(
            db.session.query(Content.course_id, func.count(Content.id))
            .filter(Content.course_id.in_(course_ids))
            .group_by(Content.course_id)
            .all()
        )
        enroll_counts = dict(
            db.session.query(Enrollment.course_id, func.count(Enrollment.id))
            .filter(
                Enrollment.course_id.in_(course_ids),
                Enrollment.status == "enrolled",
            )
            .group_by(Enrollment.course_id)
            .all()
        )

    published_courses = []
    draft_courses = []
    empty_courses = []
    zero_enroll_courses = []

    for course in courses:
        content_count = int(content_counts.get(course.id, 0) or 0)
        enroll_count = int(enroll_counts.get(course.id, 0) or 0)
        item = {
            "course_id": course.id,
            "course_title": course.title,
            "content_count": content_count,
            "enroll_count": enroll_count,
        }
        if course.status == "published":
            published_courses.append(item)
            if enroll_count == 0:
                zero_enroll_courses.append(item)
        else:
            draft_courses.append(item)
        if content_count == 0:
            empty_courses.append(item)

    if zero_enroll_courses:
        focus = zero_enroll_courses[0]
        headline = f"建议优先关注尚未形成选课的课程《{focus['course_title']}》"
        focus_card = build_focus_card(
            f"跟进《{focus['course_title']}》的运营情况",
            "该课程已经发布但当前无人选修，建议检查课程简介、教师引导和课件完整度。",
            "查看课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    elif empty_courses:
        focus = empty_courses[0]
        headline = f"建议优先补齐《{focus['course_title']}》的课件内容"
        focus_card = build_focus_card(
            f"尽快补齐《{focus['course_title']}》的课件内容",
            "该课程当前未配置课件内容，建议尽快提醒责任教师补齐基础教学资源。",
            "查看课程",
            f"/courses/{focus['course_id']}",
            focus["course_id"],
        )
    else:
        headline = "平台课程结构整体稳定，可继续跟进运营质量"
        focus_card = build_focus_card(
            "保持平台课程质量巡检",
            f"当前共有 {len(courses)} 门课程、{teacher_count} 名活跃教师与 {student_count} 名活跃学生，建议持续关注课程发布质量与选课分布。",
            "前往后台",
            "/admin",
        )

    recommendations = []
    if draft_courses:
        recommendations.append(
            build_advice_item(
                "跟进草稿课程进度",
                f"当前仍有 {len(draft_courses)} 门草稿课程，建议催促教师尽快完善并发布。",
                "前往后台",
                "/admin",
            )
        )
    if zero_enroll_courses:
        recommendations.append(
            build_advice_item(
                "排查低活跃课程情况",
                f"当前有 {len(zero_enroll_courses)} 门已发布课程尚未形成选课转化，建议优先做课程运营回访。",
                "前往后台",
                "/admin",
            )
        )
    if empty_courses:
        recommendations.append(
            build_advice_item(
                "补齐缺失的课件内容",
                f"当前有 {len(empty_courses)} 门课程未上传课件，建议优先提醒责任教师补充资源。",
                "前往后台",
                "/admin",
            )
        )

    return {
        "role": "admin",
        "headline": headline,
        "summary": f"平台当前共有 {teacher_count} 名活跃教师、{student_count} 名活跃学生、{len(courses)} 门课程。",
        "stats": [
            build_advice_stat("活跃教师", f"{teacher_count} 人"),
            build_advice_stat("活跃学生", f"{student_count} 人"),
            build_advice_stat("已发布课程", f"{len(published_courses)} 门"),
            build_advice_stat("待处理课程", f"{len(draft_courses) + len(empty_courses)} 门"),
        ],
        "focus": focus_card,
        "recommendations": recommendations[:3],
    }


def iso_datetime(value):
    """将时间字段转成前端和 AI 都可直接消费的 ISO 字符串。"""
    return value.isoformat() if value else None


def build_global_page_context(role: str):
    """大厅页统一使用全局分析范围说明。"""
    scope_label = {
        "student": "大厅总览学习分析",
        "teacher": "大厅总览教学分析",
        "admin": "大厅总览运营分析",
    }.get(role, "大厅总览分析")
    return {
        "scope": "global",
        "scope_label": scope_label,
        "scope_description": "将综合当前账号在整个平台内的课程、进度和运营数据给出整体建议。",
    }


def build_course_page_context(user: User, course_id: int):
    """课程详情页上下文只保留当前课程相关的核心分析数据。"""
    course = Course.query.get(course_id)
    if not course:
        return None

    if course.status == "draft" and not (is_teacher(user) and course.teacher_id == user.id):
        return None

    content_count = Content.query.filter_by(course_id=course.id).count()
    enroll_count = Enrollment.query.filter_by(course_id=course.id, status="enrolled").count()
    review_avg = (
        db.session.query(func.avg(Review.rating))
        .filter(Review.course_id == course.id)
        .scalar()
    )

    page_context = {
        "scope": "course-detail",
        "scope_label": "课程详情页分析",
        "scope_description": f"将优先围绕当前课程《{course.title}》生成建议。",
        "course_id": course.id,
        "course_title": course.title,
        "course_status": course.status,
        "content_count": int(content_count or 0),
        "enroll_count": int(enroll_count or 0),
        "review_avg": round(float(review_avg or 0), 1),
        "viewer_role": user.role,
    }

    if is_student(user):
        viewed_count = (
            db.session.query(func.count(func.distinct(Progress.content_id)))
            .join(Content, Content.id == Progress.content_id)
            .filter(
                Progress.student_id == user.id,
                Content.course_id == course.id,
            )
            .scalar()
        ) or 0
        last_viewed_at = (
            db.session.query(func.max(Progress.last_viewed_at))
            .join(Content, Content.id == Progress.content_id)
            .filter(
                Progress.student_id == user.id,
                Content.course_id == course.id,
            )
            .scalar()
        )
        learned_ids = {
            content_id
            for (content_id,) in db.session.query(Progress.content_id)
            .join(Content, Content.id == Progress.content_id)
            .filter(
                Progress.student_id == user.id,
                Content.course_id == course.id,
            )
            .all()
        }
        next_content = (
            Content.query.filter(Content.course_id == course.id)
            .order_by(Content.id.asc())
            .all()
        )
        next_content_title = ""
        for item in next_content:
            if item.id not in learned_ids:
                next_content_title = item.title
                break

        progress_pct = int((viewed_count / content_count) * 100) if content_count > 0 else 0
        days_idle = None
        if last_viewed_at:
            days_idle = max(0, (now() - last_viewed_at).days)

        if content_count == 0:
            course_stage = "waiting_content"
        elif progress_pct >= 100:
            course_stage = "completed"
        elif progress_pct > 0:
            course_stage = "in_progress"
        else:
            course_stage = "not_started"

        page_context.update(
            {
                "progress": progress_pct,
                "viewed_count": int(viewed_count),
                "last_viewed_at": iso_datetime(last_viewed_at),
                "days_idle": days_idle,
                "course_stage": course_stage,
                "next_content_title": next_content_title,
                "is_enrolled": bool(
                    Enrollment.query.filter_by(
                        course_id=course.id,
                        student_id=user.id,
                        status="enrolled",
                    ).first()
                ),
            }
        )
    elif is_teacher(user) and course.teacher_id == user.id:
        total_progress = (
            db.session.query(func.count(Progress.id))
            .join(Content, Content.id == Progress.content_id)
            .filter(Content.course_id == course.id)
            .scalar()
        ) or 0
        avg_student_progress = 0
        if content_count > 0 and enroll_count > 0:
            avg_student_progress = min(100, int((total_progress / (content_count * enroll_count)) * 100))
        page_context.update(
            {
                "avg_student_progress": avg_student_progress,
                "is_teacher_owner": True,
            }
        )

    return page_context


def apply_page_context(context: dict, page_context: dict | None):
    """根据当前页面上下文调整 AI 侧栏的分析焦点。"""
    role = context.get("role")
    context["page_context"] = page_context or build_global_page_context(role)

    if not page_context or page_context.get("scope") != "course-detail":
        return context

    if role == "student":
        stage = page_context.get("course_stage")
        if stage == "waiting_content":
            reason = "当前课程还没有可学习课件，可先关注课程内容是否补齐。"
        elif stage == "completed":
            reason = "当前课程已完成，可转向复盘或切换到其他课程。"
        elif stage == "in_progress" and page_context.get("days_idle", 0) >= 3:
            reason = f"当前课程已中断 {page_context.get('days_idle')} 天，建议优先恢复学习。"
        elif stage == "in_progress":
            reason = "当前课程正在推进中，建议围绕这门课继续安排下一步学习。"
        else:
            reason = "当前课程尚未开始，适合作为接下来的启动任务。"

        context["focus_course"] = {
            "course_id": page_context.get("course_id"),
            "course_title": page_context.get("course_title"),
            "progress": page_context.get("progress", 0),
            "content_count": page_context.get("content_count", 0),
            "viewed_count": page_context.get("viewed_count", 0),
            "days_idle": page_context.get("days_idle"),
            "next_content_title": page_context.get("next_content_title"),
            "stage": page_context.get("course_stage"),
            "reason": reason,
        }
    elif role == "teacher":
        avg_progress = page_context.get("avg_student_progress", 0)
        if page_context.get("course_status") == "draft":
            reason = "当前课程仍处于草稿状态，可优先补充课件后再发布。"
        elif page_context.get("content_count", 0) == 0:
            reason = "当前课程还没有课件内容，建议先补齐基础教学资源。"
        elif avg_progress < 40 and page_context.get("enroll_count", 0) > 0:
            reason = "当前课程学生平均进展偏低，适合优先做教学干预。"
        else:
            reason = "当前课程整体运行正常，可围绕本课继续优化教学安排。"

        context["focus_course"] = {
            "course_id": page_context.get("course_id"),
            "course_title": page_context.get("course_title"),
            "avg_progress": avg_progress,
            "content_count": page_context.get("content_count", 0),
            "enroll_count": page_context.get("enroll_count", 0),
            "review_avg": page_context.get("review_avg", 0),
            "reason": reason,
        }
    elif role == "admin":
        if page_context.get("content_count", 0) == 0:
            reason = "当前课程缺少课件内容，优先补齐可直接改善课程可用性。"
        elif page_context.get("enroll_count", 0) == 0:
            reason = "当前课程虽已上线但暂无选课，可优先关注曝光和引导策略。"
        else:
            reason = "当前课程已有内容和选课，可结合本课数据做更细的运营判断。"

        context["focus_course"] = {
            "course_id": page_context.get("course_id"),
            "course_title": page_context.get("course_title"),
            "content_count": page_context.get("content_count", 0),
            "enroll_count": page_context.get("enroll_count", 0),
            "review_avg": page_context.get("review_avg", 0),
            "reason": reason,
        }

    return context


def build_student_analysis_context(user: User):
    """整理学生侧 AI 分析上下文，避免把整库数据直接交给模型。"""
    enrollment_rows = (
        db.session.query(Enrollment.course_id, Course.title, Enrollment.enrolled_at)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(
            Enrollment.student_id == user.id,
            Enrollment.status == "enrolled",
            Course.status == "published",
        )
        .order_by(Enrollment.enrolled_at.asc(), Enrollment.id.asc())
        .all()
    )

    if not enrollment_rows:
        return {
            "role": "student",
            "generated_at": iso_datetime(now()),
            "overview": {
                "selected_course_count": 0,
                "in_progress_course_count": 0,
                "completed_course_count": 0,
                "not_started_course_count": 0,
                "stalled_course_count": 0,
                "average_progress": 0,
            },
            "focus_course": None,
            "priority_courses": [],
            "stalled_courses": [],
        }

    course_meta = {
        row.course_id: {
            "course_id": row.course_id,
            "course_title": row.title,
            "enrolled_at": row.enrolled_at,
        }
        for row in enrollment_rows
    }
    course_ids = list(course_meta.keys())

    content_totals = dict(
        db.session.query(Content.course_id, func.count(Content.id))
        .filter(Content.course_id.in_(course_ids))
        .group_by(Content.course_id)
        .all()
    )
    progress_rows = {
        row.course_id: row
        for row in (
            db.session.query(
                Content.course_id.label("course_id"),
                func.count(func.distinct(Progress.content_id)).label("viewed_count"),
                func.max(Progress.last_viewed_at).label("last_viewed_at"),
            )
            .join(Progress, Progress.content_id == Content.id)
            .filter(
                Progress.student_id == user.id,
                Content.course_id.in_(course_ids),
            )
            .group_by(Content.course_id)
            .all()
        )
    }

    learned_ids = {
        content_id
        for (content_id,) in db.session.query(Progress.content_id)
        .join(Content, Content.id == Progress.content_id)
        .filter(
            Progress.student_id == user.id,
            Content.course_id.in_(course_ids),
        )
        .all()
    }

    next_content_map = {}
    for content in (
        Content.query.filter(Content.course_id.in_(course_ids))
        .order_by(Content.course_id.asc(), Content.id.asc())
        .all()
    ):
        if content.course_id not in next_content_map and content.id not in learned_ids:
            next_content_map[content.course_id] = content.title

    current_time = now()
    course_states = []
    for course_id in course_ids:
        meta = course_meta[course_id]
        total = int(content_totals.get(course_id, 0) or 0)
        progress_row = progress_rows.get(course_id)
        viewed = int(getattr(progress_row, "viewed_count", 0) or 0)
        last_viewed_at = getattr(progress_row, "last_viewed_at", None)
        progress_pct = int((viewed / total) * 100) if total > 0 else 0
        days_idle = None
        if last_viewed_at:
            days_idle = max(0, (current_time - last_viewed_at).days)

        if total == 0:
            stage = "waiting_content"
        elif progress_pct >= 100:
            stage = "completed"
        elif progress_pct > 0:
            stage = "in_progress"
        else:
            stage = "not_started"

        course_states.append(
            {
                "course_id": course_id,
                "course_title": meta["course_title"],
                "progress": progress_pct,
                "content_count": total,
                "viewed_count": viewed,
                "days_idle": days_idle,
                "last_viewed_at": iso_datetime(last_viewed_at),
                "stage": stage,
                "next_content_title": next_content_map.get(course_id),
            }
        )

    in_progress_courses = [item for item in course_states if item["stage"] == "in_progress"]
    completed_courses = [item for item in course_states if item["stage"] == "completed"]
    not_started_courses = [item for item in course_states if item["stage"] == "not_started"]
    stalled_courses = [
        item for item in in_progress_courses if item["days_idle"] is not None and item["days_idle"] >= 3
    ]
    waiting_content_courses = [item for item in course_states if item["stage"] == "waiting_content"]
    sortable_progress = [item["progress"] for item in course_states if item["content_count"] > 0]
    average_progress = int(sum(sortable_progress) / len(sortable_progress)) if sortable_progress else 0

    focus_course = None
    if stalled_courses:
        focus_course = sorted(
            stalled_courses,
            key=lambda item: (item["days_idle"] or 0, -item["progress"]),
            reverse=True,
        )[0]
        focus_reason = "该课程已开始学习，但最近连续多天没有新的学习记录。"
    elif in_progress_courses:
        focus_course = sorted(in_progress_courses, key=lambda item: item["progress"], reverse=True)[0]
        focus_reason = "该课程正在推进中，继续学习更容易形成连续学习节奏。"
    elif not_started_courses:
        focus_course = not_started_courses[0]
        focus_reason = "该课程已选修但尚未开始，适合作为新的启动任务。"
    else:
        focus_reason = ""

    priority_courses = []
    for item in stalled_courses:
        priority_courses.append(
            {
                **item,
                "priority_reason": f"已停滞 {item['days_idle']} 天，建议优先恢复学习。",
            }
        )
    for item in sorted(
        [row for row in in_progress_courses if row not in stalled_courses],
        key=lambda row: row["progress"],
        reverse=True,
    ):
        priority_courses.append(
            {
                **item,
                "priority_reason": "课程已进入推进阶段，继续学习更容易完成闭环。",
            }
        )
    for item in not_started_courses:
        priority_courses.append(
            {
                **item,
                "priority_reason": "课程已选修但还未开始，可以安排首个学习切入点。",
            }
        )

    return {
        "role": "student",
        "generated_at": iso_datetime(current_time),
        "overview": {
            "selected_course_count": len(course_states),
            "in_progress_course_count": len(in_progress_courses),
            "completed_course_count": len(completed_courses),
            "not_started_course_count": len(not_started_courses),
            "stalled_course_count": len(stalled_courses),
            "waiting_content_course_count": len(waiting_content_courses),
            "average_progress": average_progress,
        },
        "focus_course": {
            **focus_course,
            "reason": focus_reason,
        }
        if focus_course
        else None,
        "priority_courses": priority_courses[:3],
        "stalled_courses": stalled_courses[:3],
    }


def build_teacher_analysis_context(user: User):
    """整理教师侧 AI 分析上下文，重点突出学生学习进展和待处理课程。"""
    courses = (
        Course.query.filter_by(teacher_id=user.id)
        .order_by(Course.updated_at.desc(), Course.id.desc())
        .all()
    )

    if not courses:
        return {
            "role": "teacher",
            "generated_at": iso_datetime(now()),
            "overview": {
                "course_count": 0,
                "published_course_count": 0,
                "draft_course_count": 0,
                "total_students": 0,
                "overall_student_progress": 0,
            },
            "focus_course": None,
            "low_progress_courses": [],
            "draft_courses": [],
            "low_enrollment_courses": [],
        }

    course_ids = [course.id for course in courses]
    content_counts = dict(
        db.session.query(Content.course_id, func.count(Content.id))
        .filter(Content.course_id.in_(course_ids))
        .group_by(Content.course_id)
        .all()
    )
    enroll_counts = dict(
        db.session.query(Enrollment.course_id, func.count(Enrollment.id))
        .filter(
            Enrollment.course_id.in_(course_ids),
            Enrollment.status == "enrolled",
        )
        .group_by(Enrollment.course_id)
        .all()
    )
    review_avg_map = dict(
        db.session.query(Review.course_id, func.avg(Review.rating))
        .filter(Review.course_id.in_(course_ids))
        .group_by(Review.course_id)
        .all()
    )
    total_progress_rows = dict(
        db.session.query(Content.course_id, func.count(Progress.id))
        .join(Progress, Progress.content_id == Content.id)
        .filter(Content.course_id.in_(course_ids))
        .group_by(Content.course_id)
        .all()
    )

    course_stats = []
    for course in courses:
        content_count = int(content_counts.get(course.id, 0) or 0)
        enroll_count = int(enroll_counts.get(course.id, 0) or 0)
        review_avg = round(float(review_avg_map.get(course.id, 0) or 0), 1)
        total_progress = int(total_progress_rows.get(course.id, 0) or 0)
        avg_progress = 0
        if course.status == "published" and content_count > 0 and enroll_count > 0:
            avg_progress = min(100, int((total_progress / (content_count * enroll_count)) * 100))

        course_stats.append(
            {
                "course_id": course.id,
                "course_title": course.title,
                "status": course.status,
                "content_count": content_count,
                "enroll_count": enroll_count,
                "review_avg": review_avg,
                "avg_progress": avg_progress,
            }
        )

    published_courses = [item for item in course_stats if item["status"] == "published"]
    draft_courses = [item for item in course_stats if item["status"] == "draft"]
    low_progress_courses = [
        {
            **item,
            "reason": "已发布且有人在学，但当前学生平均学习进度偏低。",
        }
        for item in published_courses
        if item["enroll_count"] > 0 and item["avg_progress"] < 40
    ]
    low_enrollment_courses = [
        {
            **item,
            "reason": "已发布课程的实际选课人数偏少，后续可以补充引导或优化内容组织。",
        }
        for item in published_courses
        if item["enroll_count"] <= 1
    ]
    draft_course_items = [
        {
            **item,
            "reason": "课程仍处于草稿状态，可以继续补充课件和说明后发布。",
        }
        for item in draft_courses
    ]

    progress_capacity = sum(
        item["content_count"] * item["enroll_count"]
        for item in published_courses
        if item["content_count"] > 0 and item["enroll_count"] > 0
    )
    overall_student_progress = 0
    if progress_capacity > 0:
        overall_student_progress = int(
            sum(
                item["avg_progress"] * item["content_count"] * item["enroll_count"]
                for item in published_courses
                if item["content_count"] > 0 and item["enroll_count"] > 0
            )
            / progress_capacity
        )

    focus_course = None
    if low_progress_courses:
        focus_course = sorted(low_progress_courses, key=lambda item: item["avg_progress"])[0]
    elif draft_course_items:
        focus_course = sorted(draft_course_items, key=lambda item: (item["content_count"], item["course_id"]))[0]
    elif low_enrollment_courses:
        focus_course = sorted(low_enrollment_courses, key=lambda item: item["enroll_count"])[0]

    return {
        "role": "teacher",
        "generated_at": iso_datetime(now()),
        "overview": {
            "course_count": len(course_stats),
            "published_course_count": len(published_courses),
            "draft_course_count": len(draft_courses),
            "total_students": sum(item["enroll_count"] for item in published_courses),
            "overall_student_progress": overall_student_progress,
            "low_progress_course_count": len(low_progress_courses),
        },
        "focus_course": focus_course,
        "low_progress_courses": sorted(low_progress_courses, key=lambda item: item["avg_progress"])[:3],
        "draft_courses": draft_course_items[:3],
        "low_enrollment_courses": sorted(low_enrollment_courses, key=lambda item: item["enroll_count"])[:3],
    }


def build_admin_analysis_context():
    """整理管理员侧 AI 分析上下文，突出平台课程建设和运营风险。"""
    teacher_count = User.query.filter_by(role="teacher", status="active").count()
    student_count = User.query.filter_by(role="student", status="active").count()
    courses = Course.query.order_by(Course.updated_at.desc(), Course.id.desc()).all()
    course_ids = [course.id for course in courses]

    content_counts = {}
    enroll_counts = {}
    if course_ids:
        content_counts = dict(
            db.session.query(Content.course_id, func.count(Content.id))
            .filter(Content.course_id.in_(course_ids))
            .group_by(Content.course_id)
            .all()
        )
        enroll_counts = dict(
            db.session.query(Enrollment.course_id, func.count(Enrollment.id))
            .filter(
                Enrollment.course_id.in_(course_ids),
                Enrollment.status == "enrolled",
            )
            .group_by(Enrollment.course_id)
            .all()
        )

    published_courses = []
    draft_courses = []
    empty_courses = []
    zero_enroll_courses = []

    for course in courses:
        content_count = int(content_counts.get(course.id, 0) or 0)
        enroll_count = int(enroll_counts.get(course.id, 0) or 0)
        item = {
            "course_id": course.id,
            "course_title": course.title,
            "content_count": content_count,
            "enroll_count": enroll_count,
        }
        if course.status == "published":
            published_courses.append(item)
            if enroll_count == 0:
                zero_enroll_courses.append(
                    {
                        **item,
                        "reason": "课程已发布但暂时没有学生选课，值得优先分析原因。",
                    }
                )
        else:
            draft_courses.append(
                {
                    **item,
                    "reason": "课程仍处于草稿状态，可继续跟进建设进度。",
                }
            )
        if content_count == 0:
            empty_courses.append(
                {
                    **item,
                    "reason": "课程尚未配置课件内容，会直接影响学习体验。",
                }
            )

    focus_course = None
    if zero_enroll_courses:
        focus_course = zero_enroll_courses[0]
    elif empty_courses:
        focus_course = empty_courses[0]
    elif draft_courses:
        focus_course = draft_courses[0]

    return {
        "role": "admin",
        "generated_at": iso_datetime(now()),
        "overview": {
            "teacher_count": teacher_count,
            "student_count": student_count,
            "course_count": len(courses),
            "published_course_count": len(published_courses),
            "draft_course_count": len(draft_courses),
            "empty_course_count": len(empty_courses),
            "zero_enrollment_course_count": len(zero_enroll_courses),
        },
        "focus_course": focus_course,
        "draft_courses": draft_courses[:3],
        "empty_courses": empty_courses[:3],
        "zero_enrollment_courses": zero_enroll_courses[:3],
    }


@advice_bp.get("/learning-advice-context")
@jwt_required()
def learning_advice_context():
    """为 AI 助手提供精简分析上下文 JSON。"""
    user = current_user()
    if not user:
        return err("登录状态无效", status=401)

    scope = (request.args.get("scope") or "global").strip()
    course_id = request.args.get("course_id", type=int)

    if is_student(user):
        data = build_student_analysis_context(user)
    elif is_teacher(user):
        data = build_teacher_analysis_context(user)
    elif is_admin(user):
        data = build_admin_analysis_context()
    else:
        return err("当前角色暂不支持生成分析上下文", status=403)

    page_context = build_global_page_context(data["role"])
    if scope == "course-detail" and course_id:
        page_context = build_course_page_context(user, course_id) or page_context

    data = apply_page_context(data, page_context)

    return ok(data)


@advice_bp.get("/learning-advice")
@jwt_required()
def learning_advice():
    """基于站内学习数据生成角色化、个性化的下一步建议。"""
    user = current_user()
    if not user:
        return err("请先登录", status=401)

    if is_student(user):
        data = build_student_learning_advice(user)
    elif is_teacher(user):
        data = build_teacher_learning_advice(user)
    elif is_admin(user):
        data = build_admin_learning_advice()
    else:
        return err("无权限访问智能建议", status=403)

    return ok(data)
