# 使用官方 Python 基础镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 复制可配置的环境变量文件（如果在部署时需要）
# COPY .env.example .env

# 复制后端的依赖文件
COPY requirements.txt .

# 安装依赖
# 更换为国内源以加快下载速度（例如清华源或阿里云源）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 gunicorn 作为生产环境的 WSGI 服务器
RUN pip install --no-cache-dir gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制整个 backend 目录下的内容
COPY . .

# 暴露端口给容器外
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
