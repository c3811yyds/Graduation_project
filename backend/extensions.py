from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from redis import Redis

# 全局扩展实例：在 app.py 初始化后供各路由/模型模块复用
db = SQLAlchemy()
jwt = JWTManager()
redis_client = None


def init_redis(app):
    """初始化 Redis 客户端，后续缓存和限流统一复用这里的连接。"""
    global redis_client
    redis_client = Redis.from_url(
        app.config["REDIS_URL"],
        decode_responses=True,
    )
