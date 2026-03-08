毕设 - 智能学习网站

一、概述

1. 论文主题：基于 Flask 的智能学习网站用户管理模块设计与实现。

2. 技术栈：Flask + Vue 3 + MySQL 8.0，前后端分离，模块化设计。

3. 系统定位：本系统旨在为高校师生提供一个互动性强、支持课程管理、课件上传、学习进度追踪及双向评价的在线学习平台。

4. 用户端核心功能：
   - 个人资料管理：全新的个人中心界面，支持修改昵称（含敏感词过滤）、性别以及个人简介/爱好。
   - 密码管理：支持“忘记密码（登录页）”与“已登录修改密码（个人中心）”两条链路，均基于邮箱验证码。
   - 课程列表与自主选课：课程大厅支持按课程名、教师名、课程简介关键词搜索，并可自主浏览、选课与退课。
   - 剧场模式播放：在课程详情页中央内嵌展开视频/音频/图片/PDF 在线预览，其他常见文档类型提供下载查看入口，保护页面上下文。
   - 与教师留言交流：引入真实姓名显示机制。游客仅可浏览限制内容，必须登录才可查阅完整评论及进行点赞。
   - 在线随堂笔记：通过右侧边栏随时记录学习心得。
   - 查看总体进度：自动记录文档阅读/视频观看进度，在全局仪表盘生成学习情况统计。
  - 课程详情分区切换：课程内容、学生进度、留言、评价改为横向标签切换，减少长页面滚动；学生端可直接看到课件“已学习”状态；教师端学生进度列表支持搜索、排序与每页行数切换。

5. 管理员端核心功能：
  - 轻量管理员后台：支持管理员账号登录后进入独立后台，并通过“账号管理 / 教师邀请码”标签切换不同治理板块。
  - 账号管理：支持分页、关键词筛选、角色筛选、状态筛选，以及违规账号启用/停用。
  - 全站数据总览：支持查看全课程选修人数与评分统计。
  - 数据总览交互：课程较多时支持自定义每组显示数量，并可按课程 ID 自定义对比，便于聚焦分析。
  - 教师邀请码管理：支持自定义有效天数生成邀请码，并分页查看状态、创建人、使用人等信息。

二、开发流程

1. 需求与范围
   - 明确用户角色（学生、教师、管理员）、核心功能与数据流。
   - 编写用户故事与验收标准。

2. 系统设计
   - 架构：REST API（Flask）+ SPA（Vue 3）+ MySQL 8.0。
   - 模块：认证、用户信息、管理员后台、课程、内容（视频/文档）、进度、留言交流、随堂笔记、AI助教。
   - 数据模型：用户、角色、验证码、教师邀请码、课程、选课、内容、进度、消息、笔记、评价点赞。
   - 绘制 ER 图并规范化核心表。
   - 为用户查询、课程查询、进度统计设置索引。

3. 数据库设计
   - 核心数据表采用级联及多对多关联设计。总共包含 11 张结构表。
   - 执行 `db-backups/database_seed.sql` 导入当前最新演示快照与表结构。

4. 后端实现（Flask）
   - 项目结构：应用工厂 + 蓝图按职责拆分（账号/用户、课程/内容、笔记、AI）。
   - 认证：JWT/Session、密码加密、基于角色的权限控制、邮箱验证码、独立的系统/教师邀请码流转体系。
   - 接口：登录、注册、邀请码生成、课程列表、选课、内容上传、进度统计、留言交流、随堂笔记、大模型文本生成对话。

5. 前端实现（Vue 3）
   - 基于角色的路由与布局（学生/教师/管理员）。
   - 页面：登录、仪表盘、课程列表/详情、内容播放、上传、留言、侧边栏笔记、AI全局悬浮对话抽屉。
   - 接口层：axios + SessionStorage（JWT 存储）。

6. 联调
   - CORS 配置、接口契约对齐、错误处理。
   - 端到端流程：登录 -> 角色首页 -> 课程 -> 内容 -> 进度。

7. 测试
   - 后端：服务层单测、API 测试。
   - 前端：关键页面组件测试。
   - 集成测试：主流程验证。

8. 部署
   - 开发：本地 .env，Docker 可选。
   - 生产：Nginx + Gunicorn + MySQL，打包 Vue 静态文件。
   - 服务器完整部署详细步骤请专门参考：[Docker部署指南](./DEPLOY_DOCKER.md)
   - 版本：根目录 `VERSION` 为当前 Docker 上线展示版本号。每次准备上线前，请先手动修改它，再执行 `docker compose up -d --build`。
   - 备份目录：数据库相关文件统一放在项目根目录 `db-backups/`；其中 `db-backups/database_seed.sql` 默认代表本地主数据库的最新快照，需与 `backend/storage` 一起使用；其他带时间戳的 `.sql` 文件作为日常滚动备份。
   - 说明：当前版本更新不涉及数据库表结构变更，无需执行迁移脚本。

三、快速开始

1. 环境依赖
   - Python 3.11+
   - Node.js 18+ (推荐)
   - MySQL 8.0+

2. 后端运行 (Flask)
   请确保您的机器已经安装了 MySQL，并使用 `db-backups/` 目录中的初始化 .sql 文件导入数据库结构和初始数据：

   - (1) 登录 MySQL
     - mysql -u root -p

   - (2) 创建并选择数据库
     - CREATE DATABASE graduation_project DEFAULT CHARACTER SET utf8mb4;
     - USE graduation_project;

   - (3) 导入数据（注意您的实际路径）
     - source /您的路径/db-backups/database_seed.sql;

   - (4) 进入后端目录
     - cd backend

   - (5) 创建并激活虚拟环境
     - python -m venv venv
     - Windows 命令提示符 (cmd): venv\Scripts\activate
     - Windows PowerShell: .\venv\Scripts\Activate.ps1
     - Mac/Linux: source venv/bin/activate
     - 说明：以上激活命令按你的系统环境三选一执行即可。

   - (6) 安装依赖
     - pip install -r requirements.txt

   - (7) 配置环境变量
     - 复制示例环境变量文件，并按需修改：
     - cp env.example .env
     - 【.env 必填修改项提醒】:
     - SECRET_KEY=填入你的Flask密钥
     - JWT_SECRET_KEY=填入你的JWT密钥
     - DATABASE_URL=mysql+pymysql://你的账号:你的密码@127.0.0.1:3306/graduation_project?charset=utf8mb4
     - SILICON_API_KEY=sk-xxxxxxx (替换为你自己的硅基流动 API Key)
     - MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD=填入你的发信邮箱配置(用于发送注册验证码)
     - ADMIN_INIT_EMAIL=可选，首次启动时要提升/创建的管理员邮箱
     - ADMIN_INIT_USERNAME=可选，默认 admin，仅在自动创建管理员时使用
     - ADMIN_INIT_PASSWORD=可选，自动创建管理员时使用的初始密码
     - 说明：若 ADMIN_INIT_EMAIL 填入已注册邮箱，启动时会直接将该账号角色改为 admin；若要单独新建管理员，请填写未注册邮箱

   - (8) 运行服务 (默认监听在 5000 端口)
     - python app.py


3. 前端运行 (Vue 3)
   - (1) 新开一个终端并进入前端目录
     - cd frontend

   - (2) 安装模块（首次运行）
     - npm install

   - (3) 启动服务 (默认监听在 5173 端口)
     - npm run dev


   打开浏览器访问 http://localhost:5173 即可开始体验！

四、基础功能清单

1. 认证模块
   - 登录/注册，学生/教师 角色分离
   - 引入邮箱验证码防刷机制（注册/找回/改密）
   - 忘记密码：登录页通过邮箱验证码重置密码
   - 已登录修改密码：个人中心通过邮箱验证码更新密码
   - 密码验证码规则：2 分钟有效，60 秒发送冷却
   - 引入独立的系统分配教师邀请码机制
   - 基于 SessionStorage 的跨 Tab 页独立登录环境机制

2. 学生端
   - 课程列表与自主选课：支持按课程名、教师名、课程简介关键词搜索可选课程
   - 观看视频、阅读文档
   - 与教师留言交流
   - 在线随堂笔记：通过右侧侧边栏随时记录学习心得。
   - 查看课程进度与完成度
   - 课程大厅自主选课与退课。
   - 播放在线视频、预览与下载教师下发教学文档。
   - 系统自动记录文档阅读/视频观看进度。
   - 课程互动机制：只能对已选课程发布评价一次，支持点赞老师或其他同学评价。

3. 教师端
   - 上传视频与文档
   - 留言回复
   - 管理选课学生
   - 查看观看情况与完成度统计
   - 首页支持按课程名、教师名、课程简介关键词搜索其他教师发布的课程。
   - 从草稿箱创建课程、上架课程与下线保护功能。
   - 上传教学材料，支持系统智能重命名“第X讲”，亦支持手动单条重命名。
   - 实时掌控选课学生的名单与实际学习推进量。
   - 回复学生的课程评价，删除恶意评论。

4. 管理员端
  - 管理员登录后进入独立后台页面。
  - 支持分页查看用户列表，并按关键词、角色、状态筛选。
  - 支持启用/停用账号，作为违规账号处理入口。
  - 支持查看全课程选修人数与评分总览。
  - 支持通过标签切换生成与管理教师邀请码，并按状态、关键词分页筛选邀请码。

五、数据库表设计
  核心数据表采用级联及多对多关联设计。总共包含 11 张表。

  注：本节按当前 `db-backups/database_seed.sql` 与 backend/models.py 实际字段整理。
  注：若后续你新增字段/索引，请同步更新这里，避免文档与代码漂移。

1. Table 1: users (用户表)
    - id (PK)  （主键，用户唯一标识）
    - username (唯一)  （用户名/昵称字段，系统内不可重复）
    - email (唯一)  （邮箱字段，用于登录与验证码接收，系统内不可重复）
    - password_hash（密码哈希值，存储加密结果而非明文密码）
    - role (student/teacher/admin)  （角色字段，决定用户权限范围）
    - status (active/disabled)  （账号状态字段，用于标记账号是否可用）
    - 其他信息: gender, hobby, created_at, updated_at（gender 为性别，hobby 为爱好，created_at 为创建时间，updated_at 为更新时间）
    - 注：当前导出的真实数据库里，历史账号的 email 仍可能为空；这类账号若要使用忘记密码/改密验证码链路，需要先补齐邮箱。

2. Table 2: courses (课程表)
    - id (PK)  （主键，课程唯一标识）
    - title, description（title 为课程标题，description 为课程简介）
    - teacher_id (FK -> users.id)  （外键，指向课程所属教师用户）
    - status (draft/published)  （课程状态，draft 为草稿，published 为已发布）
    - created_at, updated_at（created_at 为创建时间，updated_at 为最后更新时间）
    - 注：当前后端没有 archived 状态流转接口。

3. Table 3: enrollments (选课表)
    - id (PK)  （主键，选课记录唯一标识）
    - course_id (FK -> courses.id)  （外键，指向被选课程）
    - student_id (FK -> users.id)  （外键，指向选课学生）
    - status (enrolled/dropped)  （选课状态，enrolled 为已选，dropped 为已退）
    - enrolled_at（选课时间）
    - 约束：(course_id, student_id) 联合唯一

4. Table 4: contents (课件内容表)
    - id (PK)  （主键，课件记录唯一标识）
    - course_id (FK -> courses.id)  （外键，指向所属课程）
    - title (智能命名的课件名)  （课件展示名称）
    - type (video/audio/image/pdf/doc/...，按扩展名映射)  （课件类型字段，用于前端选择预览方式）
    - url_or_path (静态服务器文件标识)  （文件访问路径或外部资源地址）
    - duration_seconds (视频可用)  （视频/音频时长，单位秒）
    - size_bytes（文件大小，单位字节）
    - created_at（课件上传时间）

5. Table 5: progress (学习进度记录表)
    - id (PK)  （主键，进度记录唯一标识）
    - content_id (FK -> contents.id)  （外键，指向具体课件）
    - student_id (FK -> users.id)  （外键，指向学习该课件的学生）
    - progress_percent (0-100)  （学习进度百分比）
    - status (not_started/in_progress/completed)  （进度状态：未开始/进行中/已完成）
    - last_viewed_at, completed_at（last_viewed_at 为最近学习时间，completed_at 为完成时间）

6. Table 6: reviews (课程评价表)
    - id (PK)  （主键，评价记录唯一标识）
    - course_id (FK -> courses.id)  （外键，指向被评价课程）
    - user_id (FK -> users.id)  （外键，指向评价发起用户）
    - rating (1-5星), comment (文字评价)  （rating 为评分，comment 为评价内容）
    - reply_content (教师回复内容), reply_time（reply_content 为教师回复，reply_time 为回复时间）
    - likes_count (累计获赞总数)  （该评价的总点赞数）

7. Table 7: review_likes (评价点赞连接表)
    - id (PK)  （主键，点赞记录唯一标识）
    - review_id (FK -> reviews.id)  （外键，指向被点赞评价）
    - user_id (FK -> users.id)  （外键，指向点赞用户）
    - created_at（点赞时间）
    - 拥有联合唯一约束防止重复点赞

8. Table 8: messages (留言交流表)
    - id (PK)  （主键，留言记录唯一标识）
    - course_id (FK -> courses.id)  （外键，指向所属课程）
    - sender_id (FK -> users.id)  （外键，指向发送方用户）
    - receiver_id (FK -> users.id, 可选)  （外键，指向接收方用户，可为空）
    - content（留言正文内容）
    - created_at（留言创建时间）

9. Table 9: notes (随堂笔记表)
    - id (PK)  （主键，笔记记录唯一标识）
    - user_id (FK -> users.id)  （外键，指向笔记所属用户）
    - title（笔记标题）
    - content (长文本格式笔记内容)  （笔记正文内容，支持较长文本）
    - created_at, updated_at（created_at 为创建时间，updated_at 为更新时间）
    - 注：当前实现是“用户个人笔记”，不绑定 course_id。

10. Table 10: verify_codes (邮箱验证码表)
    - id (PK)  （主键，验证码记录唯一标识）
    - email (目标邮箱)  （验证码发送目标邮箱）
    - code (验证码)  （一次性验证码内容）
    - expires_at（验证码过期时间）
    - 用途：注册验证码、忘记密码验证码、个人中心改密验证码
    - 注：当前表中没有 created_at 字段，验证码过期/冷却由业务层按 expires_at 控制。

11. Table 11: teacher_invite_codes (教师邀请码表)
    - id (PK)  （主键，邀请码记录唯一标识）
    - code (系统分配的邀请码)  （教师注册使用的邀请码字符串）
    - is_used (布尔值：是否已使用)  （邀请码是否已被注册流程消耗）
    - expires_at（邀请码过期时间）
    - created_by_id (FK -> users.id)  （外键，指向生成该邀请码的教师或管理员）
    - used_by_id (FK -> users.id, 绑定的用户)  （外键，指向实际使用该邀请码注册的教师账号）
    - 注：当前表中没有 created_at、used_at 字段；历史邀请码若生成于本版本之前，created_by_id 可能为空。

关系说明
  - users(teacher) 1-N courses
  - users(student) M-N courses (通过 enrollments 桥接)
  - courses 1-N contents
  - contents N-M users(student) (通过 progress)
  - courses 1-N reviews
  - users(student/teacher) M-N reviews (通过 review_likes 桥接)
  - courses 1-N messages
  - users 1-N notes
  - 注：notes 当前仅与 users 关联，不与 courses 关联。

六、接口清单（REST + JWT）

包含认证保护头 Authorization: Bearer {token}

  - 注：本节按当前后端蓝图实际路由整理（backend/app.py + routes_*.py）。
  - 注：路径参数在 Flask 中是 {int:xxx}，文档统一简写为 {id}。
  - 注：当前路由实现文件为 routes_account.py（认证/用户）、routes_course.py（课程/内容）与 routes_admin.py（管理员），routes_auth.py 为兼容导出入口。

1. 【认证及用户】
    - POST /api/auth/send-code : 发送邮箱验证码
    - POST /api/auth/send-reset-code : 忘记密码发送验证码（已注册邮箱）
    - POST /api/auth/reset-password : 忘记密码提交验证码并重置新密码
    - POST /api/auth/register : 用户身份注册（需验证码，教师登录需系统邀请码）
    - POST /api/auth/login : 用户认证换取 Token (前端清除 token 即退出)
    - GET /api/auth/invite-codes : 教师查看自己当前未使用且未过期的邀请码
    - POST /api/auth/generate-invite : 教师生成固定 1 天有效的邀请码（一邀请码仅限注册一个教师账号）
    - GET /api/users/me : 获取当前凭证所有者信息
    - PATCH /api/users/me : 更新个人资料
    - POST /api/users/me/password-code : 已登录用户发送改密验证码
    - PATCH /api/users/me/password : 已登录用户验证码改密
    - GET /api/users/analytics : 获取数据大盘（学生/教师视角）
    - GET /api/health : 健康检查
    - GET /api/version : 获取当前部署版本号
    - 说明：密码找回/改密依赖用户邮箱；若历史账号 users.email 为空，需要先补邮箱后再使用验证码链路。

2. 【课程模块】
    - GET /api/courses : 获取已发布/自己的课程列表
    - GET /api/courses/{id} : 获取单课程详情（已发布课程可见；草稿仅课程教师可见）
    - POST /api/courses : 创建草稿课程
    - PATCH /api/courses/{id} : 更新课程基础信息（标题/简介，仅课程教师）
    - PUT /api/courses/{id}/publish : 发布课程
    - PUT /api/courses/{id}/unpublish : 下架课程（回到 draft）
    - DELETE /api/courses/{id} : 删除废弃课程
    - GET /api/courses/{id}/students : 教师查看选课学生

3. 【选课/进度模块】
    - POST /api/courses/{id}/enroll : 学生确认报名
    - DELETE /api/courses/{id}/enroll : 学生退课
    - GET /api/courses/{id}/progress : 学生查看课程进度
    - 注：教师学生进度汇总由 GET /api/courses/{id}/students 返回（含每个学生 progress 字段）；课程详情页教师端当前支持对学生进度按姓名/账号搜索、按进度排序，并自定义每页显示行数。

4. 【课件内容模块】
    - GET /api/courses/{id}/contents : 内容列表（学生查询时会带 is_learned 字段）
    - GET /api/contents/{id} : 获取单个课件详情
    - POST /api/courses/{id}/contents/upload : 上传课件（FormData: file, title）
    - PUT /api/contents/{id} : 重命名修改某个课件名称
    - DELETE /api/contents/{id} : 删除课件
    - POST /api/contents/{id}/view : 记录学习进度（学生观看打点）
    - GET /api/contents/{id}/file : 访问/下载课件文件（支持 token 查询参数）
    - 注：课程详情页当前通过标签切换展示“课程内容 / 学生进度 / 留言 / 评价”；PDF 支持在线预览，其他常见文档暂为下载查看；学生课件列表中的“已学习”状态由 `GET /api/courses/{id}/contents` 返回的 `is_learned` 字段驱动。

5. 【课程评价与交流模块】
    - GET /api/courses/{course_id}/reviews : 获取某门课的评论列表，按“点赞+时间”降序
    - POST /api/courses/{course_id}/reviews : 提交课程打分与评价
    - POST /api/courses/{course_id}/reviews/{review_id}/like : 切换点赞状态
    - PUT /api/courses/{course_id}/reviews/{review_id}/reply : 授课教师填写官方回复
    - DELETE /api/courses/{course_id}/reviews/{review_id} : 移除评论
    - GET /api/courses/{course_id}/messages : 课程留言列表
    - POST /api/courses/{course_id}/messages : 发送留言

6. 【笔记模块】
    - GET /api/notes : 获取当前用户笔记列表
    - POST /api/notes : 新建笔记
    - PUT /api/notes/{id} : 更新笔记
    - DELETE /api/notes/{id} : 删除笔记

7. 【智能 AI 实训助手】
    - POST /api/ai/chat : 教师与学生的智能助教对话生成接口，接入大语言模型流式输出
    - 集成功能: 全局左侧栏滑动抽屉随时唤出，利用 SSE (Server-Sent Events) 打字机效果呈现思考过程
    - 注：当前 AI 聊天接口仅做登录校验，不做敏感词过滤；敏感词检测仅作用于写入数据库的接口。

8. 【管理员后台】
    - GET /api/admin/overview : 获取管理员首页概览统计
    - GET /api/admin/analytics : 获取管理员视角的全课程选修/评分总览
    - GET /api/admin/users : 分页获取用户列表（支持关键词、角色、状态筛选）
    - PATCH /api/admin/users/{id}/status : 启用或停用指定账号
    - GET /api/admin/invite-codes : 分页获取教师邀请码列表（支持按状态、邀请码、创建人、使用人关键词筛选）
    - POST /api/admin/invite-codes : 管理员生成自定义有效天数的教师邀请码（一邀请码仅限注册一个教师账号）

七、系统流转与突破功能点总结

  本系统围绕“教与学”的双向闭环展开，提供了一站式的在线教育解决方案。除了基础的注册登录、建课与选课、播放视频及文档等常规操作以外，本毕设着重实现并打通了以下能力：

1. 防恶意注册与邀请机制（JWT / 密码 Hash）：配合邮箱验证码实现防刷，独创限时 1 天的教师邀请码裂变机制（定时失效策略）。
2. 沉浸式笔记体验（Vue 3 全局侧边栏）：不需跳脱画面，学生观看时可随时唤出侧边栏，生成并保存个人全局笔记（当前不绑定课程）。
3. 强级联的评价社区生态（MySQL 关联查询）：打分系统伴随评论，其他学生均可阅览并点赞（具有防止重复点赞约束），授课教师进行官方回复。
4. 完备的数据与进度统计（大模块聚合查询）：支持学生个人的单门课进度概览和授课老师对全班的学习进度汇总信息洞察。
5. 永不离线的贴身 AI 助教（硅基流动模型接口 / SSE 通信）：利用 Server-Sent Events 流式协议直连大语言模型，并将其封装为全局悬浮抽屉随时提供答疑。
6. 剧场级内嵌阅览体验（Vue 3 / 多媒体适配）：重构了新标签页跳转的割裂逻辑，真正在课程核心区内嵌了兼容视频、音频、图片与 PDF 在线预览的响应式预览器，并为其他常见文档提供下载查看入口，配合平滑滚动特效，形成了“中心大屏学习、左侧AI答疑、右侧唤出笔记”的三屏协同学习微环境。
7. 轻量管理员治理后台（管理员路由 / 全站统计）：补充独立管理员角色与后台入口，支持通过标签切换管理账号与教师邀请码、分页筛选用户、违规账号停用、全课程选修评分总览，提升系统上线后的运维与治理能力。

八、答辩可直接讲的 6 条创新点

  下面这 6 条更适合在论文答辩、项目汇报或 PPT 讲解时直接展开，不是单纯罗列功能，而是从场景、交互、架构和治理角度总结本系统的创新点。

1. 面向学习场景的三屏协同交互设计
  本系统不是简单把 AI、笔记、课件拆成多个页面，而是围绕真实学习流程，把中央课件预览、左侧 AI 助教、右侧全局笔记放在同一学习上下文中，减少页面跳转带来的割裂感，提高连续学习效率。

2. 面向学习过程的细粒度进度反馈机制
  系统不仅提供课程总进度，还细化到单个课件的学习状态标记。学生端可以直接看到“已学习”内容，教师端可以查看课程内所有学生的进度汇总，管理员端还可以看到全课程选修与评分总览，形成从个人到全局的分层数据反馈链路。

3. 课程详情页的标签化聚合交互
  针对课件、留言、评价、学生进度内容变多后页面过长的问题，系统将课程详情页改造为“课程内容 / 学生进度 / 留言 / 评价”横向标签切换结构，既降低了滚动成本，也为后续继续扩展作业、测验、资料统计等模块预留了统一入口。

4. 轻量化但完整的三角色治理体系
  系统在学生、教师基础上补充了管理员角色，并实现账号停用、邀请码管理、全课程统计等能力，使系统从“教学功能演示”进一步提升为“具备基本运营与治理能力的在线学习平台”。

5. 轻量前后端分离与可部署工程化方案
  相比常见的模板化毕设，本系统采用 Flask + Vue 3 + MySQL 的轻量化前后端分离架构，结合 Docker Compose、版本号管理、数据库快照、storage 文件同步、部署文档等工程实践，体现了从开发、部署到维护的完整闭环，而不仅是页面和接口功能堆叠。

6. 学习平台中的安全与治理前置设计
  系统将邮箱验证码、教师邀请码、敏感词过滤、管理员封禁账号、数据快照管理等机制前置到实际业务流程中，不是等出现问题后再补，而是在注册、登录、内容发布、平台治理等多个环节做了约束设计，增强了系统的可控性与可持续运行能力。


