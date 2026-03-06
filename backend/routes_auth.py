"""
兼容入口：
- 账号/个人资料相关接口已拆分到 routes_account.py
- 课程/内容相关接口已拆分到 routes_course.py
保留本文件用于兼容历史导入路径，避免一次性改动过大。
"""

from routes_account import auth_bp, user_bp
from routes_course import course_bp, content_bp

