Docker 生产环境部署说明

一、整体组成

1. 前端服务
使用 Nginx 提供静态页面，并把 `/api` 请求转发到后端。

2. 后端服务
使用 Python 3.13 + Gunicorn 提供接口服务。

3. 数据库服务
使用 MySQL 8.0，并通过数据卷持久化。

4. Redis 服务
使用 `redis:7-alpine`，当前用于：
- 课程列表、个人总览、管理员概览/总览缓存
- 注册/找回密码/个人中心改密验证码与冷却时间
- 登录失败限流、验证码请求限流、AI 请求限流

二、服务器环境准备

请先确认服务器已安装：

1. Git
2. Docker Engine
3. Docker Compose V2

三、拉取项目代码

在服务器执行：

```bash
git clone https://github.com/c3811yyds/Graduation_project.git
cd Graduation_project
```

说明：

1. 当前敏感词库已并入主仓库，不需要再执行子模块命令。
2. 每次准备 Docker 上线前，请先手动修改根目录 `VERSION`。
3. `db-backups/database_seed.sql` 默认代表本地主数据库最新快照。
4. 如果仓库中的 `backend/storage` 也跟随本地最新数据一起提交，那么同步数据时要和 `db-backups/database_seed.sql` 一起应用，不能只同步其中一项。

四、创建后端环境变量文件

在项目根目录执行：

```bash
cp backend/env.example backend/.env
nano backend/.env
```

至少改成下面这些值，可询问ai怎么改：

```env
SECRET_KEY=填入你随机生成的 Flask 安全密钥
JWT_SECRET_KEY=填入你随机生成的 JWT 密钥
DATABASE_URL=mysql+pymysql://admin:admin@db:3306/graduation_project?charset=utf8mb4
REDIS_URL=redis://redis:6379/0
UPLOAD_DIR=./storage
SILICON_API_KEY=sk-xxxxxxx
MAIL_SERVER=smtp.qq.com
MAIL_PORT=465
MAIL_USERNAME=your_email@qq.com
MAIL_PASSWORD=your_email_auth_code
MAIL_CONSOLE_FALLBACK=false
ADMIN_INIT_EMAIL=
ADMIN_INIT_USERNAME=
ADMIN_INIT_PASSWORD=
```

说明：

1. `DATABASE_URL` 要和 `docker-compose.yml` 中数据库账号保持一致。
2. `REDIS_URL` 在线上必须指向 Compose 内的 Redis 服务，也就是 `redis://redis:6379/0`。
3. `UPLOAD_DIR=./storage` 对应后端容器内目录，已通过数据卷持久化。
4. `MAIL_CONSOLE_FALLBACK` 线上应保持 `false`，不要再使用控制台验证码兜底；正常邮件发送链路不会在日志里输出明文验证码，只有开发环境启用兜底且实际走兜底时才会打印验证码。
5. `ADMIN_INIT_*` 仅在你需要首次自动创建/提升管理员账号时填写。

补充说明：

1. 当前登录失败限流、验证码请求限流、AI 请求限流在 Nginx 反向代理场景下会优先识别真实客户端 IP（`X-Forwarded-For` / `X-Real-IP`），不要再按容器内网 IP 判断是否命中限流。
2. 课程详情页受限课件预览已改为短时访问票据链路，前端不会再把 JWT 直接拼进预览 URL；如需排查预览问题，优先检查 `POST /api/contents/{id}/access-ticket` 和 `/api/contents/{id}/file?ticket=...`。

管理员初始化变量说明：

`ADMIN_INIT_EMAIL` 填要自动提升/创建为管理员的邮箱；留空则不启用。
如果这里填写的是系统里已经注册过的邮箱，启动时会直接把该账号角色改成 `admin`。
如果你想单独新建一个管理员账号，不要填已注册的学生/教师邮箱，可以直接填一个未注册的随机邮箱。
`ADMIN_INIT_USERNAME` 仅在自动新建管理员账号时使用。
`ADMIN_INIT_PASSWORD` 仅在自动新建管理员账号时使用，建议至少 6 位。

五、首次启动服务

先确认根目录 `VERSION` 已经改成这次准备上线的版本号，再执行：

```bash
docker compose up -d --build --force-recreate
```

说明：

1. 首次部署会同时启动前端、后端、MySQL、Redis。
2. MySQL 在空库首次初始化时，会自动导入 `db-backups/database_seed.sql`。
3. Redis 会自动启用 AOF 持久化，数据写入 `redis_data` 卷。

六、验证服务状态

查看后端日志：

```bash
docker compose logs -f backend
```

查看 Redis 日志：

```bash
docker compose logs -f redis
```

如果后端日志中出现 Gunicorn 正常监听 5000 端口，Redis 日志中出现 `Ready to accept connections`，说明服务已正常运行。

浏览器访问：

```text
http://你的服务器公网IP
```

七、旧环境补接 Redis

如果你的服务器之前已经部署过项目，但当时还没有 Redis，这次升级按下面做：

```bash
cd ~/Graduation_project
git pull origin main
nano backend/.env
```

确认 `backend/.env` 中包含：

```env
REDIS_URL=redis://redis:6379/0
MAIL_CONSOLE_FALLBACK=false
```

补充说明：

1. 线上保持 `MAIL_CONSOLE_FALLBACK=false` 时，验证码只会在邮件发送成功后写入 Redis / 数据库兜底，不会额外打印到后端日志。
2. 如果前端出现课件预览失败，但下载正常，优先查看 backend 日志里 `POST /api/contents/{id}/access-ticket` 与 `/api/contents/{id}/file?ticket=...` 是否返回 401/403。

然后执行：

```bash
docker compose up -d --build
docker compose logs -f redis
docker compose logs -f backend
```

说明：

1. 这一步会把 Redis 服务补进现有环境。
2. 如果你这次同时有数据库快照更新，仍然要按数据同步流程额外导入 `db-backups/database_seed.sql`。

八、日常维护命令

1. 更新代码并重建

```bash
git pull origin main
nano VERSION
docker compose up -d --build
```

2. 只重启后端

```bash
docker compose restart backend
```

3. 只重启 Redis

```bash
docker compose restart redis
```

4. 停止并删除容器，保留数据卷

```bash
docker compose down
```

5. 停止并删除容器和数据卷

```bash
docker compose down -v
```

说明：
该命令不仅会删除 MySQL 数据卷 `db_data`，也会一起删除课件文件卷 `backend_storage` 和 Redis 数据卷 `redis_data`，相当于同时清空数据库、课件文件和 Redis 持久化数据，仅适合彻底重置环境时使用。

6. 查看前端日志

```bash
docker compose logs -f frontend
```

7. 查看 Redis 当前 key

```bash
docker compose exec redis redis-cli KEYS '*'
```

8. 备份数据库到固定目录

```bash
mkdir -p /root/db-backups
docker compose exec -T db mysqldump -u root -proot --default-character-set=utf8mb4 --no-tablespaces graduation_project > /root/db-backups/backup_$(date +%F_%H%M).sql
```

9. 备份上传文件

```bash
docker compose exec -T backend sh -c "cd /app/backend && tar czf - storage" > /root/backend_storage_$(date +%F_%H%M).tar.gz
```

九、用仓库中的最新快照覆盖服务器运行环境

适用场景：
本地数据库与 `backend/storage` 是主数据源，云服务器只作为运行和测试环境，需要整体同步到服务器。

在项目根目录执行：

```bash
docker compose exec -T db mysql -u root -proot graduation_project < db-backups/database_seed.sql

tar -czf /root/backend_storage_sync.tar.gz -C /root/Graduation_project backend/storage
BACKEND_ID=$(docker compose ps -q backend)
docker cp /root/backend_storage_sync.tar.gz "$BACKEND_ID":/tmp/backend_storage_sync.tar.gz
docker compose exec backend sh -c "rm -rf /app/backend/storage/* && cd /app && tar xzf /tmp/backend_storage_sync.tar.gz && rm -f /tmp/backend_storage_sync.tar.gz"
rm -f /root/backend_storage_sync.tar.gz
docker compose restart backend frontend
```

说明：

1. 这组命令会把服务器数据库覆盖成仓库里的 `db-backups/database_seed.sql`。
2. 这组命令会把运行中的 `backend_storage` 卷覆盖成仓库里的 `backend/storage`。
3. 如果你只同步数据库、不同步 `storage`，课件记录和文件会不匹配；反过来也一样。

十、只把服务器 SQL 回拉到本地

如果你只需要把服务器网站上的最新 SQL 数据回拉到本地，不回拉 `storage`，可以按下面执行：

服务器导出：

```bash
docker compose exec -T db mysqldump -u root -proot --default-character-set=utf8mb4 --no-tablespaces graduation_project > /root/db-backups/server_dump_$(date +%F_%H%M).sql
```

本地下载：

```bash
scp root@服务器IP:/root/db-backups/server_dump_时间.sql ./db-backups/
```

本地导入：

```bash
mysql -u root -p graduation_project < ./db-backups/server_dump_时间.sql
```

说明：

1. 这组命令只适合账号、选课、留言、评价、笔记、邀请码这类纯数据库数据回拉。
2. 如果服务器还改了课件文件，仍然需要把 `backend/storage` 一起同步回本地。

十一、数据持久化说明

1. MySQL 数据保存在 `db_data` 卷中。
2. 上传文件保存在 `backend_storage` 卷中。
3. Redis AOF 数据保存在 `redis_data` 卷中。
4. 容器重建后，只要不删卷，这三类数据默认不会丢失。
