# 🐳 Docker 生产环境一键部署指南

本项目采用 `docker-compose` 进行完全容器化编排，包含以下三个核心组件容器：
1. **Frontend (前端)**: 基于 Nginx，内部包含 Vue3 打包后的静态文件，并负责对后端的反向代理。
2. **Backend (后端)**: 基于 Python 3.13，使用 Gunicorn 托管 Flask 服务提供 REST API 与大模型 SSE 流输出。
3. **Database (数据库)**: 基于官方 MySQL 8.0 镜像，自动做持久化映射与初装 SQL 载入。

---

## ⚡ 第一步：准备服务器环境

确保你的云服务器/服务器实例已经安装了：
*   **Git**: 用于拉取仓库代码
*   **Docker Engine**: Docker 运行核心
*   **Docker Compose**: 容器独立编排工具（建议使用 V2 较新版本）

## 📦 第二步：拉取项目并配置环境变量

```bash
# 1. 克隆代码仓库进入目录
git clone https://github.com/c3811yyds/Graduation_project.git
cd Graduation_project

# 2. 为后端创建生产环境的密钥配置
# 强烈建议不要将生产的密码泄露入代码库，所以我们在生产机手动创建 `.env`
cat << 'EOF' > backend/.env
SECRET_KEY=填入你随机生成的Flask安全密钥_越长越好
JWT_SECRET_KEY=填入你随机生成的JWT加密密钥_越长越好
# 数据库连接字符串（请勿修改账号密码和数据库名，必须与 docker-compose.yml 中的数据库配置严格对应）
DATABASE_URL=mysql+pymysql://admin:admin@db:3306/graduation_project?charset=utf8mb4
UPLOAD_DIR=./storage
# 替换下方为你自己申请的 硅基流动 AI API Key
SILICON_API_KEY=sk-xxxxxxx
# 邮箱注册验证码配置 (必填 - 用于注册发送验证码)
MAIL_SERVER=smtp.qq.com
MAIL_PORT=465
MAIL_USERNAME=your_email@qq.com
MAIL_PASSWORD=your_email_auth_code
EOF
```

## 🚀 第三步：一键构建并启动服务

在包含了 `docker-compose.yml` 的项目根目录下，执行如下命令：

```bash
# 执行无感静默强制拉取构建，过程大约需要 2-5 分钟
docker-compose up -d --build --force-recreate
```

*这一步 Docker 会自动下载所需环境镜像、下载前端 NPM 库与打包、下载后端 Pip 依赖并在后台相互连接启动。*

## 🏁 第四步：验证服务与日志

在构建完成后，给 MySQL 大约 15 秒钟的自动初始化表结构的时间。
你可以使用以下命令监控后端服务的存活状态与错误日志：

```bash
docker logs -f graduation_project_backend_1
```
当你在面板看见 `Listening at: http://0.0.0.0:5000` 表示后端已经成功连接数据库并运转。

**直接访问你的云服务器**：
现在，打开浏览器访问 `http://<你服务器的公网IP地址>` 即可看到系统正常运行：
- 前端 Nginx 接管 80 端口，不再受到 127.0.0.1 阻绝
- AJAX `/api/*` 请求会被 Nginx 完美的打给 `gunicorn`
- 挂载的 `storage` 与数据库文件将在服务器上落地留存不受重启影响。

---

## 🔧 常见维护指令

| 操作场景 | 执行命令 |
| :--- | :--- |
| **应用代码更新(极简版)** | 在项目根录执行: <br> `git pull`<br>`docker-compose up -d --build` |
| 仅重启后端(修改.env后生效) | `docker restart graduation_project_backend_1` |
| 完全销毁当前运行环境(保留数据盘) | `docker-compose down` |
| 完全销毁(不留情面，连数据库都清空) | `docker-compose down -v` |
| 查看前端 Nginx 访问记录 | `docker logs -f graduation_project_frontend_1` |