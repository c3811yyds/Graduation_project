from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# 全局扩展实例：在 app.py 初始化后供各路由/模型模块复用
db = SQLAlchemy()
jwt = JWTManager()
