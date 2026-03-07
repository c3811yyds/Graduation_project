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

git clone https://github.com/c3811yyds/Graduation_project.git
cd Graduation_project

说明：当前敏感词库已经并入主仓库，不再需要执行子模块相关命令。
版本号说明：
  每次准备 Docker 上线前，请先手动修改项目根目录 `VERSION`。
  例如先执行 `nano VERSION`，再把内容改成 `v1.0.1` 这类你自己能识别的版本号。
  后端镜像构建时会把这个版本号写入镜像，前端页面顶部会显示当前部署版本。
备份目录说明：
  服务器日常数据库备份建议统一导出到 `/root/db-backups/`。
  项目根目录 `db-backups/` 统一存放数据库相关文件。
  其中 `db-backups/database_seed.sql` 默认代表本地主数据库的最新快照，部署演示环境或把本地数据同步到服务器时，都以这份文件为准；其他带时间戳的 `.sql` 文件作为日常滚动备份文件。
  如果仓库中的 `backend/storage` 也跟随本地最新数据一起提交，那么服务器同步数据时要把 `db-backups/database_seed.sql` 和 `backend/storage` 一起应用，不能只导入其中一项。

四、创建后端环境变量文件
在项目根目录执行：

1. 先复制示例文件

cp backend/env.example backend/.env

2. 再编辑 backend/.env

nano backend/.env

3. 至少改成下面这些值

SECRET_KEY=填入你随机生成的Flask安全密钥_越长越好
JWT_SECRET_KEY=填入你随机生成的JWT加密密钥_越长越好
DATABASE_URL=mysql+pymysql://admin:admin@db:3306/graduation_project?charset=utf8mb4
UPLOAD_DIR=./storage
SILICON_API_KEY=sk-xxxxxxx
MAIL_SERVER=smtp.qq.com
MAIL_PORT=465
MAIL_USERNAME=your_email@qq.com
MAIL_PASSWORD=your_email_auth_code
ADMIN_INIT_EMAIL=
ADMIN_INIT_USERNAME=
ADMIN_INIT_PASSWORD=

管理员初始化变量说明：
ADMIN_INIT_EMAIL 填要自动提升/创建为管理员的邮箱；留空则不启用
如果这里填写的是系统里已经注册过的邮箱，启动时会直接把该账号角色改成 admin，则不会有学生端和教师端功能
如果你想单独新建一个管理员账号，不要填已注册的学生/教师邮箱，可以直接填一个未注册的随机邮箱
ADMIN_INIT_USERNAME 仅在自动新建管理员账号时使用
ADMIN_INIT_PASSWORD 仅在自动新建管理员账号时使用，建议至少 6 位

如果你习惯直接覆盖写入，也可以改用下面这条：

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
ADMIN_INIT_EMAIL=
ADMIN_INIT_USERNAME=
ADMIN_INIT_PASSWORD=
EOF

说明：
1. DATABASE_URL 要和 docker-compose.yml 里数据库账号保持一致。
2. UPLOAD_DIR 使用 ./storage，对应后端容器内目录，已通过数据卷持久化。
3. ADMIN_INIT_* 为可选项，仅在你需要首次自动创建/提升管理员账号时填写。

五、启动服务
在项目根目录执行：

先确认根目录 `VERSION` 已经改成这次准备上线的版本号，再执行下面命令：
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

git pull
手动修改根目录 `VERSION`
docker compose up -d --build

2. 只重启后端

docker compose restart backend

3. 停止并删除容器，保留数据卷

docker compose down

4. 停止并删除容器和数据卷（会清空数据库）

docker compose down -v

说明：该命令不仅会删除 MySQL 数据卷 `db_data`，也会一起删除课件上传数据卷 `backend_storage`，相当于同时清空数据库和已上传课件文件，仅适合彻底重置环境时使用。

5. 查看前端日志

docker compose logs -f frontend

6. 备份数据库到固定目录

mkdir -p /root/db-backups
docker compose exec -T db mysqldump -u root -proot --default-character-set=utf8mb4 --no-tablespaces graduation_project > /root/db-backups/backup_$(date +%F_%H%M).sql

7. 备份上传文件

docker compose exec -T backend sh -c "cd /app/backend && tar czf - storage" > /root/backend_storage_$(date +%F_%H%M).tar.gz

8. 使用仓库中的最新数据库快照和课件文件覆盖当前运行环境

适用场景：
本地数据库与 `backend/storage` 是主数据源，云服务器只作为运行和测试环境，需要整体同步到服务器。

在项目根目录执行：

docker compose exec -T db mysql -u root -proot graduation_project < db-backups/database_seed.sql

tar -czf /root/backend_storage_sync.tar.gz -C /root/Graduation_project backend/storage
BACKEND_ID=$(docker compose ps -q backend)
docker cp /root/backend_storage_sync.tar.gz "$BACKEND_ID":/tmp/backend_storage_sync.tar.gz
docker compose exec backend sh -c "rm -rf /app/backend/storage/* && cd /app && tar xzf /tmp/backend_storage_sync.tar.gz && rm -f /tmp/backend_storage_sync.tar.gz"
rm -f /root/backend_storage_sync.tar.gz
docker compose restart backend frontend

说明：
1. 这组命令会把服务器数据库覆盖成仓库里的 `db-backups/database_seed.sql`。
2. 这组命令会把运行中的 `backend_storage` 数据卷覆盖成仓库里的 `backend/storage`。
3. 如果你只同步数据库、不同步 `storage`，课件记录和文件会不匹配；反过来只同步 `storage` 也一样。

九、数据持久化说明
1. MySQL 数据保存在 db_data 卷中。
2. 上传文件保存在 backend_storage 卷中。
3. 容器重建后，这两类数据默认不会丢失。
