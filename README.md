# 毕设 - 智能学习网站

## 概述

**论文主题**：基于 Flask 的智能学习网站用户管理模块设计与实现。
**技术栈**：Flask + Vue 3 + MySQL 8.0，前后端分离，模块化设计。

本系统旨在为高校师生提供一个互动性强、支持课程管理、课件上传、学习进度追踪及双向评价的在线学习平台。

## 开发流程

1. 需求与范围
   - 明确用户角色（学生、教师）、核心功能与数据流。
   - 编写用户故事与验收标准。

2. 系统设计
   - 架构：REST API（Flask）+ SPA（Vue 3）+ MySQL 8.0。
   - 模块：认证、用户信息、课程、内容（视频/文档）、进度、留言交流。
   - 数据模型：用户、角色、课程、选课、内容、进度、消息。
   - 绘制 ER 图并规范化核心表。
   - 为用户查询、课程查询、进度统计设置索引。

3. 数据库设计
   - 执行 database_seed.sql 导入初始数据与表结构。

4. 后端实现（Flask）
   - 项目结构：应用工厂、蓝图按模块拆分、服务层、DAO/仓储层。
   - 认证：JWT/Session、密码加密、基于角色的权限控制。
   - 接口：登录、注册、课程列表、选课、内容上传、进度统计、留言交流、随堂笔记。

5. 前端实现（Vue 3）
   - 基于角色的路由与布局（学生/教师）。
   - 页面：登录、仪表盘、课程列表/详情、内容播放、上传、留言、侧边栏笔记。
   - 接口层：axios，状态管理（Pinia）。

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

## 快速开始🔥

### 1. 环境依赖
- Python 3.11+
- Node.js 18+ (推荐)
- MySQL 8.0+

### 2. 后端运行 (Flask)
请确保您的机器已经安装了 MySQL，并使用根目录提供的 .sql 文件导入数据库结构和初始数据：

```bash
# 登录 MySQL
mysql -u root -p

# 创建并选择数据库
CREATE DATABASE graduation_project DEFAULT CHARACTER SET utf8mb4;
USE graduation_project;

# 导入数据（注意您的实际路径）
source /您的路径/database_seed.sql;
```

```bash
cd backend
# 1. 创建并激活虚拟环境
python -m venv venv
# Windows 命令提示符 (cmd): venv\Scripts\activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
# 复制示例环境变量文件，并修改其中的数据库连接和硅基流动 API Key
cp env.example .env

# 4. 运行服务 (默认监听在 5000 端口)
python app.py
```

### 3. 前端运行 (Vue 3)
新开一个终端：

```bash
cd frontend
# 1. 安装模块（首次运行）
npm install

# 2. 启动服务 (默认监听在 5173 端口)
npm run dev
```

打开浏览器访问 `http://localhost:5173` 即可开始体验！

## 基础功能清单

### 认证模块
- 登录/注册，学生/教师 角色分离
- 基于 SessionStorage 的跨 Tab 页独立登录环境机制
- 登录/退出
- 学生/教师角色区分

### 学生端
- 课程列表与自主选课
- 观看视频、阅读文档
- 与教师留言交流
- **在线随堂笔记**：通过右侧侧边栏随时记录学习心得。
- 查看课程进度与完成度
- 课程大厅自主选课与退课。
- 播放在线视频、预览与下载教师下发教学文档。
- 系统自动记录文档阅读/视频观看进度。
- 课程互动机制：只能对已选课程**发布评价一次**，支持点赞老师或其他同学评价。

### 教师端
- 上传视频与文档
- 留言回复
- 管理选课学生
- 查看观看情况与完成度统计
- 从草稿箱创建课程、上架课程与下线保护功能。
- 上传教学材料，支持系统智能重命名“第X讲”，亦支持手动单条重命名。
- 实时掌控选课学生的名单与实际学习推进量。
- 回复学生的课程评价，删除恶意评论。

## 数据库表设计
核心数据表采用级联及多对多关联设计。总共包含 **9 张表**。

### Table 1: `users` (用户表)
- `id` (PK)
- `username` (唯一)
- `password_hash`
- `role` (student/teacher)
- `status` (active/disabled)
- 其他信息: `email`, `phone`, `created_at`, `updated_at` 等

### Table 2: `courses` (课程表)
- `id` (PK)
- `title`, `description`
- `teacher_id` (FK -> users.id)
- `status` (draft/published/archived)
- `created_at`, `updated_at`

### Table 3: `enrollments` (选课表)
- `id` (PK)
- `course_id` (FK -> courses.id)
- `student_id` (FK -> users.id)
- `status` (enrolled/dropped/completed)
- `enrolled_at`

### Table 4: `contents` (课件内容表)
- `id` (PK)
- `course_id` (FK -> courses.id)
- `title` (智能命名的课件名)
- `type` (video/doc)
- `url_or_path` (静态服务器文件标识)
- `duration_seconds` (视频可用)
- `size_bytes`

### Table 5: `progress` (学习进度记录表)
- `id` (PK)
- `content_id` (FK -> contents.id)
- `student_id` (FK -> users.id)
- `progress_percent` (0-100)
- `status` (not_started/in_progress/completed)
- `last_viewed_at`, `completed_at`

### Table 6: `reviews` (课程评价表)
- `id` (PK)
- `course_id` (FK -> courses.id)
- `user_id` (FK -> users.id)
- `rating` (1-5星), `comment` (文字评价)
- `reply_content` (教师回复内容), `reply_time`
- `likes_count` (累计获赞总数)

### Table 7: `review_likes` (评价点赞连接表)
- `id` (PK)
- `review_id` (FK -> reviews.id)
- `user_id` (FK -> users.id)
- *拥有联合唯一约束防止重复点赞*

### Table 8: `messages` (留言交流表)
- `id` (PK)
- `course_id` (FK -> courses.id)
- `sender_id` (FK -> users.id)
- `receiver_id` (FK -> users.id, 可选)
- `content`
- `created_at`

### Table 9: `notes` (随堂笔记表)
- `id` (PK)
- `user_id` (FK -> users.id)
- `course_id` (FK -> courses.id)
- `content` (长文本格式笔记内容)
- `created_at`, `updated_at`

### 关系说明
*   **users(teacher)** `1-N` **courses**
*   **users(student)** `M-N` **courses** (通过 `enrollments` 桥接)
*   **courses** `1-N` **contents**
*   **contents** `N-M` **users(student)** (通过 `progress`)
*   **courses** `1-N` **reviews**
*   **users(student/teacher)** `M-N` **reviews** (通过 `review_likes` 桥接)
*   **courses** `1-N` **messages**
*   **users** `1-N` **notes**

## 接口清单（REST + JWT）
包含认证保护头 `Authorization: Bearer <token>`

### 【认证及用户】
- `POST /api/auth/register` : 用户身份注册
- `POST /api/auth/login` : 用户认证换取 Token (前端清除 token 即退出)
- `GET /api/users/me` : 获取当前凭证所有者信息
- `PATCH /api/users/me` : 更新个人资料

### 【课程模块】
- `GET /api/courses` : 获取已发布/自己的课程列表
- `POST /api/courses` : 创建草稿课程
- `GET /api/courses/<id>` : 课程数据大屏及详细内容
- `PATCH /api/courses/<id>` : 教师更新课程信息
- `POST /api/courses/<id>/publish` : 发布课程
- `DELETE /api/courses/<id>` : 删除废弃课程
- `GET /api/courses/<id>/students` : 教师查看选课学生

### 【选课/进度模块】
- `POST /api/courses/<id>/enroll` : 学生确认报名
- `DELETE /api/courses/<id>/enroll` : 学生退课
- `GET /api/courses/<id>/progress` : 学生查看课程进度
- `GET /api/courses/<id>/progress/students` : 教师查看学生进度汇总
- `POST /api/contents/<id>/progress` : 端测推送学习进度

### 【课件内容模块】
- `GET /api/courses/<id>/contents` : 内容列表
- `POST /api/courses/<id>/contents` : 断点/批量上传新教案
- `GET /api/contents/<id>` : 内容详情
- `PUT /api/contents/<id>` : 重命名修改某个课件名称
- `DELETE /api/contents/<id>` : 删除课件

### 【课程评价与交流模块】
- `GET /api/courses/<id>/reviews` : 获取某门课的评论列表，按“点赞+时间”降序
- `POST /api/courses/<id>/reviews` : 提交课程打分与评价
- `POST /api/courses/<id>/reviews/<id>/like` : 切换点赞状态
- `PUT /api/courses/<id>/reviews/<id>/reply` : 授课教师填写官方回复
- `DELETE /api/courses/<id>/reviews/<id>` : 移除评论
- `GET /api/courses/<id>/messages` : 课程留言列表
- `POST /api/courses/<id>/messages` : 发送留言

### 【笔记模块】 (新增)
- `GET /api/notes` : 获取用户的笔记，支持基于 `course_id` 过滤
- `POST /api/notes` : 新增或更新某门课程的随堂笔记

### 【智能 AI 实训助手】 (新增)
- `POST /api/ai/chat` : 教师与学生的智能助教对话生成接口，接入大语言模型流式输出
- **集成功能**: 全局左侧栏滑动抽屉随时唤出，利用 SSE (Server-Sent Events) 打字机效果呈现思考过程

### 💡业务流转总结：
> 老师(`Users`)建立门课(`Courses`) -> 塞入课件资料(`Contents`) -> 学生(`Users`)报名选课(`Enrollments`) -> 学生阅读/刷课，系统记录更新进度(`Progress`) -> 学生边看视频边记录笔记(`Notes`) -> 学生写下期末小作(`Reviews`) -> 老师官方回帖，并且全班同学可对此点赞(`Review_likes`)。
