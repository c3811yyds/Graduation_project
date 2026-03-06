Docker 生产环境部署说明

一、整体组成
1. 前端服务
使用 Nginx 提供静态页面，并把 /api 请求转发到后端。
2. 后端服务
使用 Python 3.13 + Gunicorn 提供接口服务。
3. 数据库服务
使用 MySQL 8.0，并通过数据卷持久化。

二、服务器环境准备
请先确认服务器已安装以下组件：
1. Git
2. Docker Engine
3. Docker Compose V2

三、拉取项目代码
在服务器执行：

git clone --recurse-submodules https://github.com/c3811yyds/Graduation_project.git
cd Graduation_project

如果之前已经 clone 过，再执行一次：

git submodule update --init --recursive

四、创建后端环境变量文件
在项目根目录执行：

cat << EOF > backend/.env
SECRET_KEY=填入你随机生成的Flask安全密钥_越长越好
JWT_SECRET_KEY=填入你随机生成的JWT加密密钥_越长越好
DATABASE_URL=mysql+pymysql://admin:admin@db:3306/graduation_project?charset=utf8mb4
UPLOAD_DIR=./storage
SILICON_API_KEY=sk-xxxxxxx
MAIL_SERVER=smtp.qq.com
MAIL_PORT=465
MAIL_USERNAME=your_email@qq.com
MAIL_PASSWORD=your_email_auth_code
EOF

说明：
1. DATABASE_URL 要和 docker-compose.yml 里数据库账号保持一致。
2. UPLOAD_DIR 使用 ./storage，对应后端容器内目录，已通过数据卷持久化。

五、启动服务
在项目根目录执行：

docker compose up -d --build --force-recreate

说明：
1. 首次部署或大版本更新建议使用上面这条命令。
2. 该命令会自动构建前后端镜像并启动数据库。

六、验证服务状态
查看后端日志：

docker compose logs -f backend

如果日志里出现 Listening at: http://0.0.0.0:5000，说明后端已正常运行。

浏览器访问：
http://你的服务器公网IP

七、日常维护命令
1. 更新代码并重新构建

git pull --recurse-submodules
docker compose up -d --build

2. 只重启后端

docker compose restart backend

3. 停止并删除容器，保留数据卷

docker compose down

4. 停止并删除容器和数据卷（会清空数据库）

docker compose down -v

5. 查看前端日志

docker compose logs -f frontend

八、数据持久化说明
1. MySQL 数据保存在 db_data 卷中。
2. 上传文件保存在 backend_storage 卷中。
3. 容器重建后，这两类数据默认不会丢失。
