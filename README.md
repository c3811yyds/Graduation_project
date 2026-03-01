# 毕设 - 智能学习网站# 毕设 - 智能学习网站

## 概述## 概述

**论文主题**：基于 Flask 的智能学习网站用户管理模块设计与实现。

**技术栈**：Flask + Vue 3 + MySQL 8.0，前后端分离，模块化设计。


本系统旨在为高校师生提供一个互动性强、支持课程管理、课件上传、学习进度追踪及双向评价的在线学习平台。## 开发流程

1. 需求与范围

---   - 明确用户角色（学生、教师）、核心功能与数据流。

   - 编写用户故事与验收标准。

## 快速开始🔥

2. 系统设计

### 1. 环境依赖   - 架构：REST API（Flask）+ SPA（Vue 3）+ MySQL 8.0。

- Python 3.11+   - 模块：认证、用户信息、课程、内容（视频/文档）、进度、留言交流。

- Node.js 18+ (推荐)   - 数据模型：用户、角色、课程、选课、内容、进度、消息。

- MySQL 8.0+

3. 数据库设计

### 2. 后端运行 (Flask)   - 绘制 ER 图并规范化核心表。

请确保您的机器已经安装了 MySQL，并使用根目录提供的 .sql 文件导入数据库结构和初始数据：

**导入数据库方式**
# 登录 MySQL
mysql -u root -p

# 创建并选择数据库
CREATE DATABASE graduation_project DEFAULT CHARACTER SET utf8mb4;
USE graduation_project;

# 导入数据（注意您的实际路径）
source /您的路径/database_seed.sql;
`

   - 为用户查询、课程查询、进度统计设置索引。

```bash

cd backend4. 后端实现（Flask）

# 1. 创建并激活虚拟环境   - 项目结构：应用工厂、蓝图按模块拆分、服务层、DAO/仓储层。

python -m venv venv   - 认证：JWT/Session、密码加密、基于角色的权限控制。

# Windows下激活: venv\Scripts\activate  (Mac/Linux: source venv/bin/activate)   - 接口：登录、注册、课程列表、选课、内容上传、进度统计、留言交流。



# 2. 安装依赖5. 前端实现（Vue 3）

pip install -r requirements.txt   - 基于角色的路由与布局（学生/教师）。

   - 页面：登录、仪表盘、课程列表/详情、内容播放、上传、留言。

# 3. 运行服务 (默认监听在 5000 端口)   - 接口层：axios，状态管理（Pinia）。

python app.py

```6. 联调

   - CORS 配置、接口契约对齐、错误处理。

### 3. 前端运行 (Vue 3)   - 端到端流程：登录 -> 角色首页 -> 课程 -> 内容 -> 进度。

新开一个终端：

```bash7. 测试

cd frontend   - 后端：服务层单测、API 测试。

# 1. 安装模块（首次运行）   - 前端：关键页面组件测试。

npm install   - 集成测试：主流程验证。



# 2. 启动服务 (默认监听在 5173 端口)8. 部署

npm run dev   - 开发：本地 .env，Docker 可选。

```   - 生产：Nginx + Gunicorn + MySQL，打包 Vue 静态文件。



打开浏览器访问 `http://localhost:5173` 即可开始体验！## 基础功能清单

- 认证

---  - 登录/退出

  - 学生/教师角色区分

## 基础功能清单- 学生端

### 认证模块  - 课程列表与自主选课

- 登录/注册，学生/教师 角色分离  - 观看视频、阅读文档

- 基于 SessionStorage 的跨 Tab 页独立登录环境机制  - 与教师留言交流

  - 查看课程进度与完成度

### 学生端- 教师端

- 课程大厅自主选课与退课。  - 上传视频与文档

- 播放在线视频、预览与下载教师下发的教学文档。  - 留言回复

- 系统自动记录文档阅读/视频观看进度。  - 管理选课学生

- 课程互动机制：只能对已选课程**发布评价一次**，支持点赞老师或其他同学的评价。  - 查看观看情况与完成度统计



### 教师端## 数据库表设计（建议）

- 从草稿箱创建课程、上架课程与下线保护功能。以下为核心表的建议字段与用途，可根据实际业务细化。

- 上传教学材料，支持系统智能重命名“第X讲”，亦支持手动单条重命名。

- 实时掌控选课学生的名单与实际学习推进量。### users（用户）

- 回复学生的课程评价，删除恶意评论。- id (PK)

- username（唯一）

---- password_hash

- role（student/teacher）

## 数据库表设计- email（可选）

核心数据表采用级联及多对多关联设计。- phone（可选）

- status（active/disabled）

### `users` (用户表)- created_at, updated_at

- `id` (PK)

- `username` (唯一)### courses（课程）

- `password_hash`- id (PK)

- `role` (student/teacher)- title

- 其他信息: `status`, `created_at` 等- description

- teacher_id (FK -> users.id)

### `courses` (课程表)- status（draft/published/archived）

- `id` (PK)- created_at, updated_at

- `title`, `description`

- `teacher_id` (FK -> users.id)### enrollments（选课）

- `status` (draft/published/archived)- id (PK)

- course_id (FK -> courses.id)

### `enrollments` (选课表)- student_id (FK -> users.id)

- `id` (PK)- status（enrolled/dropped/completed）

- `course_id` (FK -> courses.id)- enrolled_at

- `student_id` (FK -> users.id)

### contents（课程内容）

### `contents` (课件内容表)- id (PK)

- `id` (PK)- course_id (FK -> courses.id)

- `course_id` (FK -> courses.id)- type（video/doc）

- `title` (智能命名的课件名)- title

- `type` (video/doc)- url_or_path（文件或存储地址）

- `url_or_path` (静态服务器文件标识)- duration_seconds（视频可用）

- size_bytes（可选）

### `progress` (学习进度记录表)- created_at

- `id` (PK)

- `content_id` (FK -> contents.id)### progress（内容学习进度）

- `student_id` (FK -> users.id)- id (PK)

- `progress_percent` (0-100)，自动与 `status` 关联- content_id (FK -> contents.id)

- student_id (FK -> users.id)

### `reviews` (课程评价表)- progress_percent（0-100）

- `id` (PK)- status（not_started/in_progress/completed）

- `course_id` (FK -> courses.id)- last_viewed_at

- `user_id` (FK -> users.id)- completed_at（可选）

- `rating` (1-5星), `comment` (文字评价)

- `reply_content` (教师回复内容), `reply_time`### messages（留言交流）

- `likes_count` (累计获赞总数)- id (PK)

- course_id (FK -> courses.id)

### `review_likes` (评价点赞连接表)- sender_id (FK -> users.id)

- `id` (PK)- receiver_id (FK -> users.id, 可选)

- `review_id` (FK -> reviews.id)- content

- `user_id` (FK -> users.id)- created_at

- *拥有联合唯一约束防止重复点赞*

### 关系说明

### 核心关联关系- users(teacher) 1 - N courses

*   **users(teacher)** `1-N` **courses**- users(student) N - M courses（通过 enrollments）

*   **users(student)** `M-N` **courses** (通过 `enrollments` 桥接)- courses 1 - N contents

*   **courses** `1-N` **contents**- contents N - M users(student)（通过 progress）

*   **courses** `1-N` **reviews**- courses 1 - N messages（可用于课程内交流）

*   **users(student/teacher)** `M-N` **reviews** (通过 `review_likes` 桥接)




## 接口清单（REST + JWT）

---以下为核心接口建议，路径可按实际约定调整。



## 核心接口路由清单 (RESTful + JWT)### 认证与用户

包含认证保护头 `Authorization: Bearer <token>`- POST /api/auth/register

   - 说明：开放注册

### 【认证及用户】   - 请求：username, password, role

- `POST /api/auth/register` : 用户身份注册   - 响应：token, user

- `POST /api/auth/login` : 用户认证换取 Token - POST /api/auth/login

- `GET /api/users/me` : 获取当前凭证所有者信息   - 请求：username, password

   - 响应：token, user

### 【课程模块】- POST /api/auth/logout

- `GET /api/courses` : 获取已发布/自己的课程列表   - 说明：前端清除 token，后端可选黑名单

- `POST /api/courses` : 创建草稿课程- GET /api/users/me

- `GET /api/courses/<id>` : 课程数据大屏及详细内容   - 说明：获取当前用户信息

- `DELETE /api/courses/<id>` : 删除废弃课程- PATCH /api/users/me

   - 说明：更新个人资料

### 【选课/上报模块】

- `POST /api/courses/<id>/enroll` : 学生确认报名

- `POST /api/contents/<id>/progress` : 端测推送学习进度

### 课程

### 【课件内容模块】- GET /api/courses

- `POST /api/courses/<id>/contents` : 断点/批量上传新教案   - 说明：课程列表（支持关键字/教师/状态筛选）

- `PUT /api/contents/<id>` : 重命名修改某个课件名称- POST /api/courses

- `DELETE /api/contents/<id>` : 删除课件   - 说明：教师创建课程

- GET /api/courses/{courseId}

### 【课程评价与互动模块】   - 说明：课程详情

- `GET /api/courses/<id>/reviews` : 获取某门课的评论列表，按“点赞+时间”降序- PATCH /api/courses/{courseId}

- `POST /api/courses/<id>/reviews` : 提交课程打分与评价   - 说明：教师更新课程信息

- `POST /api/courses/<id>/reviews/<id>/like` : 切换点赞状态- POST /api/courses/{courseId}/publish

- `PUT /api/courses/<id>/reviews/<id>/reply` : 授课教师填写官方回复   - 说明：发布课程

- `DELETE /api/courses/<id>/reviews/<id>` : 移除评论

### 选课

---- POST /api/courses/{courseId}/enroll

   - 说明：学生选课

## 目录结构- DELETE /api/courses/{courseId}/enroll

```text   - 说明：学生退课

GraduationProject/- GET /api/courses/{courseId}/students

├── backend/                # Flask 后端目录   - 说明：教师查看选课学生

│   ├── app.py              # 主调度路由/服务器入口

│   ├── models.py           # SQLAlchemy 数据模型定义### 课程内容（视频/文档）

│   ├── routes_auth.py      # 用户/业务视图/API处理- GET /api/courses/{courseId}/contents

│   ├── extensions.py       # SQL与JWT绑定库   - 说明：内容列表

│   ├── requirements.txt    # 依赖声明- POST /api/courses/{courseId}/contents

│   └── storage/            # 媒体/课件静态托管目录   - 说明：教师上传内容（视频/文档）

├── frontend/               # Vue 3 前端目录- GET /api/contents/{contentId}

│   ├── package.json        # 依赖与脚本   - 说明：内容详情

│   ├── vite.config.js      # 本地反向代理配置- DELETE /api/contents/{contentId}

│   └── src/   - 说明：教师删除内容

│       ├── api/http.js     # Axios拦截器

│       ├── views/          # 仪表板与详细核心业务视图### 进度统计

│       └── router/         # Vue-Router- POST /api/contents/{contentId}/progress

└── README.md               # 本文档说明   - 说明：学生上报进度（百分比/状态）

```- GET /api/courses/{courseId}/progress
   - 说明：学生查看课程进度
- GET /api/courses/{courseId}/progress/students
   - 说明：教师查看学生进度汇总

### 留言交流
- GET /api/courses/{courseId}/messages
   - 说明：课程留言列表
- POST /api/courses/{courseId}/messages
   - 说明：发送留言

### 通用约定
- 鉴权：Authorization: Bearer <token>
- 返回：统一 { code, message, data }
- 分页：page, pageSize, total

## 开发与运行环境
以下为建议环境配置，可按学校/实验室要求微调。

### 开发环境（本地）
- OS：Windows 10/11
- Python：3.11.x
- Node.js：18.x 或 20.x（建议 18 LTS）
- 数据库：MySQL 8.0（本机安装）
- Python 包管理：venv（建议配合虚拟环境）
- 前端包管理：npm（如需可改用 pnpm）

### 运行环境（服务器）
- OS：Linux（Ubuntu 20.04/22.04）
- Python：3.11.x
- Web Server：Nginx
- WSGI：Gunicorn
- 数据库：MySQL 8.0

### 目录结构建议（简版）
- backend/  Flask 后端
- frontend/ Vue 3 前端
- docs/     论文与设计文档

## 关键词
Flask，Vue 3，MySQL 8.0，前后端分离，模块化开发，
用户管理，基于角色的权限控制，学生/教师角色，课程管理，
视频/文档内容，进度统计，留言交流，REST API，JWT，SPA

## 数据库架构与业务流转说明

本项目采用结构化的现代关系型数据库设计，包含 8 张核心表。  
以下是它们在业务逻辑中的层级划分与实际运作流转方式：

### 【第一层：核心实体表】
这三张表存放了最基本的实体。
#### 1. `users` (用户表)
- **业务作用**：系统里所有的自然人都在这一张表，不管你是老师还是学生。
- **关联逻辑**：依赖 `role` 字段来严格区分权限层级。
  - `id` (PK), `username` (唯一), `password_hash`, `role`, `status`

#### 2. `courses` (课程表)
- **业务作用**：存放老师创建的独立课程（如“高等数学”）。
- **关联逻辑**：内含 `teacher_id`，建立 **1个老师 -> N门课程** 的关系。
  - `id` (PK), `title`, `description`, `teacher_id` (FK), `status`

#### 3. `contents` (课件内容表)
- **业务作用**：即每门课里的具体播放内容，例如“第1讲 绪论视频”。
- **关联逻辑**：包含 `course_id`，建立 **1门课 -> N个课件** 的归属关系。
  - `id` (PK), `course_id` (FK), `title`, `type`, `url_or_path`

---

### 【第二层：多对多桥接表】
一个学生可多选课，一门课可被多学生选，依托以下联列表进行多对多映射。
#### 4. `enrollments` (选课关联表)
- **业务作用**：记录“谁(Student) 报名了 哪门课(Course)”。
- **关联逻辑**：连接 `users` 表与 `courses` 表，支持选课与退课状态变更。
  - `id` (PK), `course_id` (FK), `student_id` (FK)

#### 5. `progress` (学习进度表)
- **业务作用**：极其重要！系统在后端随时记录：**【某一个学生】在【某一个课件下】，目前观看了百分之多少**。前端展示的学生个人雷达图以及教师端数据大屏全是基于此动态计算的。
  - `id` (PK), `content_id` (FK), `student_id` (FK), `progress_percent`

---

### 【第三层：课程互动拓展表】
外围功能的解耦设计，不干涉核心选课流程。
#### 6. `messages` (留言交流表)
- **业务作用**：“谁”对“哪个课程”发起了提问或常规交流记录。

#### 7. `reviews` (课程评价表)
- **业务作用**：学生结课后对课程的主观意见与打分。
- **关联逻辑**：包含了星级(`rating`)、学生留言(`comment`)，同时加入了防止并发冲突的 **累计受赞数(`likes_count`)** 与 **教师官方下场回复(`reply_content`)**。
  - `id` (PK), `course_id` (FK), `user_id` (FK), `rating`, `reply_content`, `likes_count`

#### 8. `review_likes` (防刷赞的评价点赞中间表)
- **业务作用**：【最核心防作弊设计】单独分离的一张表，严格记录“**谁** 点赞了 **哪条评价**”。
- **关联逻辑**：底层数据库设有 **复合唯一约束(UniqueConstraint)**，强行拒绝同一个 user_id 对同一 review_id 提交第二次，保障系统公正性。当客户端渲染高亮大拇指时，也来源于此表的状态。
  - `id` (PK), `review_id` (FK -> reviews.id), `user_id` (FK -> users.id)


### 💡业务流转总结：
> 老师(`Users`)建立门课(`Courses`) ➡️ 塞入课件资料(`Contents`) ➡️ 学生(`Users`)报名选课(`Enrollments`) ➡️ 学生阅读/刷课，系统记录更新进度(`Progress`) ➡️ 学生写下期末小作文(`Reviews`) ➡️ 老师官方回帖，并且全班同学可对此点赞(`Review_likes`)。
