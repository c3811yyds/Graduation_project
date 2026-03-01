from flask import Flask, jsonify
from dotenv import load_dotenv
import os
from flask_cors import CORS
from extensions import db, jwt
from routes_auth import auth_bp, user_bp, course_bp, content_bp

load_dotenv()

def create_app():
    app = Flask(__name__)

    # 基础配置
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://gp_user:gp_user@127.0.0.1:3306/graduation_project?charset=utf8mb4",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY",
        "gp_dev_super_secret_key_2026_please_change_32bytes_plus",
    )
    
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
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 蓝图注册
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(content_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"code": 0, "message": "ok", "data": {"service": "backend"}})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)