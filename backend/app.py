import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from extensions import db, init_redis, jwt
from routes_account import auth_bp, user_bp
from routes_admin import admin_bp, bootstrap_admin_account
from routes_course import course_bp, content_bp
from routes_note import note_bp
from routes_ai import ai_bp

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


def load_app_version():
    """读取当前部署版本号。"""
    # 部署版本默认读项目根目录 VERSION；Docker 中可通过 APP_VERSION_FILE 指定镜像内路径
    version_path = Path(os.getenv("APP_VERSION_FILE", str(BASE_DIR / "VERSION")))
    try:
        version = version_path.read_text(encoding="utf-8").strip()
        return version or "dev"
    except OSError:
        return "dev"

def create_app():
    """创建并初始化 Flask 应用。"""
    app = Flask(__name__)

    # 基础配置
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://gp_user:gp_user@127.0.0.1:3306/graduation_project?charset=utf8mb4",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    jwt_secret_key = (os.getenv("JWT_SECRET_KEY") or "").strip()
    # JWT 密钥禁止回退到代码内置默认值，漏配时直接启动失败。
    if not jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY 未配置，后端拒绝启动")
    app.config["JWT_SECRET_KEY"] = jwt_secret_key
    
    # Redis 先只接基础连接，后续再逐步接入缓存和限流逻辑。
    app.config["REDIS_URL"] = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    app.config["APP_VERSION"] = load_app_version()
    
    # 优先使用 .env 里的 UPLOAD_DIR 绝对路径，如果没有则默认存放在项目同级的 uploads 文件夹
    app.config["UPLOAD_DIR"] = os.getenv(
        "UPLOAD_DIR", 
        os.path.join(os.path.dirname(__file__), "..", "uploads")
    )
    
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB

    # MySQL utf8mb4 连接参数
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "connect_args": {"charset": "utf8mb4"},
    }

    # 扩展初始化
    db.init_app(app)
    jwt.init_app(app)
    init_redis(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    with app.app_context():
        import models
        db.create_all()
        bootstrap_admin_account()

    # 蓝图注册
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(note_bp)
    app.register_blueprint(ai_bp)

    @app.get("/api/health")
    def health():
        """返回后端健康状态和版本号。"""
        return jsonify({
            "code": 0,
            "message": "ok",
            "data": {"service": "backend", "version": app.config["APP_VERSION"]},
        })

    @app.get("/api/version")
    def version():
        """返回当前部署版本号。"""
        return jsonify({
            "code": 0,
            "message": "ok",
            "data": {"version": app.config["APP_VERSION"]},
        })

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
