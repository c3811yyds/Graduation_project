SET FOREIGN_KEY_CHECKS=0;

-- ========================================================
-- 表：users （用户表）
-- 说明：存储系统中所有用户（如教师、学生、管理员）的基本信息及认证数据
-- ========================================================
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '用户唯一标识 ID，主键',
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '登录用户名，全局唯一',
  `email` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户电子邮箱（可选），全局唯一',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '加密后的登录密码哈希值',
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户角色（如 student, teacher, admin 等）',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '账号状态（active 表示正常启用，inactive 禁用）',
  `created_at` datetime NOT NULL COMMENT '账号记录创建时间',
  `updated_at` datetime NOT NULL COMMENT '账号信息最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`) COMMENT '用户名全局唯一索引',
  UNIQUE KEY `email` (`email`) COMMENT '邮箱全局唯一索引'
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：courses （课程表）
-- 说明：存储平台上的课程基础信息，关联到授课教师ID
-- ========================================================
CREATE TABLE `courses` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '课程唯一标识 ID，主键',
  `title` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '课程标题',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '课程详细描述或简介文本',
  `teacher_id` int NOT NULL COMMENT '外键：关联 users 表的 id，表示授课教师',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '课程状态（例如 draft 草稿、published 已发布）',
  `created_at` datetime NOT NULL COMMENT '课程记录创建时间',
  `updated_at` datetime NOT NULL COMMENT '课程信息最后编辑时间',
  PRIMARY KEY (`id`),
  KEY `ix_courses_teacher_id` (`teacher_id`) COMMENT '授课教师ID索引',
  KEY `ix_courses_title` (`title`) COMMENT '课程名称索引',
  CONSTRAINT `courses_ibfk_1` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`) COMMENT '外键约束：必须是真实存在的用户'
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：contents （课程内容章节表）
-- 说明：存储课程内的具体章节媒体内容（如图片、视频、PDF文档等），由 course_id 关联至课程
-- ========================================================
CREATE TABLE `contents` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '内容节点唯一标识 ID，主键',
  `course_id` int NOT NULL COMMENT '外键：关联 courses 表的 id，表示所属课程',
  `type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '媒体类型（如 video, image, document 等）',
  `title` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '内容章节或节点的标题',
  `url_or_path` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '资源在服务器中的本地相对路径或外部 URL',
  `duration_seconds` int DEFAULT NULL COMMENT '音视频时长统计（单位：秒）',
  `size_bytes` bigint DEFAULT NULL COMMENT '资源文件大小统计（单位：字节）',
  `created_at` datetime NOT NULL COMMENT '本章节内容创建时间',
  PRIMARY KEY (`id`),
  KEY `ix_contents_course_id` (`course_id`) COMMENT '关联课程ID索引',
  CONSTRAINT `contents_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) COMMENT '外键约束：必须关联已有课程'
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：enrollments （选课报名记录表）
-- 说明：连接学生和课程（多对多关系），记录哪些学生选修了哪些课程及其相关状态
-- ========================================================
CREATE TABLE `enrollments` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '报名记录唯一标识 ID，主键',
  `course_id` int NOT NULL COMMENT '外键：关联 courses 表的 id，用户被报名的课程',
  `student_id` int NOT NULL COMMENT '外键：关联 users 表的 id，报名该课程的学生',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '选修状态（如 enrolled 在学, dropped 退出）',
  `enrolled_at` datetime NOT NULL COMMENT '最近一次选修/报名的时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_course_student` (`course_id`,`student_id`) COMMENT '联合唯一约束：同一名学生不能对同一门课程重复产生选修记录',
  KEY `ix_enrollments_student_id` (`student_id`) COMMENT '关联学生ID索引',
  KEY `ix_enrollments_course_id` (`course_id`) COMMENT '关联课程ID索引',
  CONSTRAINT `enrollments_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) COMMENT '外键约束：关联有效课程',
  CONSTRAINT `enrollments_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) COMMENT '外键约束：关联有效用户'
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：messages （课程互动消息表）
-- 说明：记录课程内的沟通留言记录，包括学生提问和教师回复
-- ========================================================
CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '消息记录唯一标识 ID，主键',
  `course_id` int NOT NULL COMMENT '外键：该消息归属于哪门课程（即在哪个课程页面发出的）',
  `sender_id` int NOT NULL COMMENT '外键：消息发送方的用户 id',
  `receiver_id` int DEFAULT NULL COMMENT '外键（可选）：非公开或直接回复时的接收方 用户 id',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息或留言的实际文本内容',
  `created_at` datetime NOT NULL COMMENT '消息产生时间',
  PRIMARY KEY (`id`),
  KEY `ix_messages_sender_id` (`sender_id`) COMMENT '发送者ID索引',
  KEY `ix_messages_course_id` (`course_id`) COMMENT '课程ID索引',
  KEY `ix_messages_receiver_id` (`receiver_id`) COMMENT '接收者ID索引',
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) COMMENT '外键约束：关联有效课程',
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`) COMMENT '外键约束：发送者必须为有效用户',
  CONSTRAINT `messages_ibfk_3` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`id`) COMMENT '外键约束：接收者必须为有效用户'
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：notes （个人学习笔记表）
-- 说明：记录学生等用户自己主动增加的、归属个人的专属笔记本记录
-- ========================================================
CREATE TABLE `notes` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '笔记记录唯一标识 ID，主键',
  `user_id` int NOT NULL COMMENT '外键：这条笔记的所有者用户 id',
  `title` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '笔记简明标题',
  `content` text COLLATE utf8mb4_unicode_ci COMMENT '笔记内文格式的具体文本或 markdown',
  `created_at` datetime NOT NULL COMMENT '笔记最原始创建时间',
  `updated_at` datetime NOT NULL COMMENT '笔记文本的最近编辑更新时间',
  PRIMARY KEY (`id`),
  KEY `ix_notes_user_id` (`user_id`) COMMENT '关联用户ID索引',
  CONSTRAINT `notes_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) COMMENT '外键约束：笔记必须绑定存在的用户'
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：progress （学习内容进度记录表）
-- 说明：追踪每个学生学习特定某个章节（content）的完成进度（如观看时长记录、百分比）
-- ========================================================
CREATE TABLE `progress` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '进度条目唯一标识 ID，主键',
  `content_id` int NOT NULL COMMENT '外键：具体的哪个课程章节节点的 id',
  `student_id` int NOT NULL COMMENT '外键：产生这笔进度的学生用户 id',
  `progress_percent` int NOT NULL COMMENT '学习进度的百分比数字（例如 100 代表完成）',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '此章节的最终完成状态（例如 completed 已处理）',
  `last_viewed_at` datetime NOT NULL COMMENT '最后一次访问/观看此时的时刻',
  `completed_at` datetime DEFAULT NULL COMMENT '达到100%完成的时间戳',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_content_student_progress` (`content_id`,`student_id`) COMMENT '联合唯一约束：同一学生针对同一个课时节点，仅会存在一天进度条记录',
  KEY `ix_progress_content_id` (`content_id`) COMMENT '对应内容节点的索引',
  KEY `ix_progress_student_id` (`student_id`) COMMENT '对应学生的索引',
  CONSTRAINT `progress_ibfk_1` FOREIGN KEY (`content_id`) REFERENCES `contents` (`id`) COMMENT '外键约束：必须关联到具体存在的内容',
  CONSTRAINT `progress_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) COMMENT '外键约束：必须关联正确学生存在'
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：reviews （课程综合评价打分表）
-- 说明：记录学生针对于已选课程或公开课程给出的打星评价与评语情况
-- ========================================================
CREATE TABLE `reviews` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '评价条目唯一标识 ID，主键',
  `course_id` int NOT NULL COMMENT '外键：被评价目标所在的课程 id',
  `user_id` int NOT NULL COMMENT '外键：作出此次评价判定的用户 id',
  `rating` int NOT NULL COMMENT '星级等打分数值（如 1 - 5）',
  `comment` text COLLATE utf8mb4_unicode_ci COMMENT '可选的系统详细评价文本内容',
  `created_at` datetime DEFAULT NULL COMMENT '进行系统评价的时间戳',
  `reply_content` text COLLATE utf8mb4_unicode_ci COMMENT '该授课教师针对此差评/好评所做的额外回复文字',
  `reply_time` datetime DEFAULT NULL COMMENT '授课教师回复的时间节点',
  `likes_count` int DEFAULT '0' COMMENT '用于内部统计评价被“其他同学”点赞的数量缓存（支持排序）',
  PRIMARY KEY (`id`),
  KEY `ix_reviews_user_id` (`user_id`) COMMENT '对应评价发起者的索引',
  KEY `ix_reviews_course_id` (`course_id`) COMMENT '对应目标课程的索引',
  CONSTRAINT `reviews_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) COMMENT '外键约束：指向的课程结构正常存在',
  CONSTRAINT `reviews_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) COMMENT '外键约束：评价者身份可靠保障关联'
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 表：review_likes （评论点赞人次清单表）
-- 说明：明细记录存储谁点赞了谁写的评价，避免学生作弊反复多次为同一个评价点赞刷数据
-- ========================================================
CREATE TABLE `review_likes` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '点赞日志记录唯一标识 ID，主键',
  `review_id` int NOT NULL COMMENT '外键：发生被点赞事件的课程评价自身 id',
  `user_id` int NOT NULL COMMENT '外键：执行主动点赞动作的用户 id',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '触发最终点赞时刻的时间戳',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_review_user_like` (`review_id`,`user_id`) COMMENT '联合唯一约束：同一名学生不支持对同一条评论刷二次支持',
  KEY `user_id` (`user_id`) COMMENT '对应点赞实施者的索引',
  CONSTRAINT `review_likes_ibfk_1` FOREIGN KEY (`review_id`) REFERENCES `reviews` (`id`) ON DELETE CASCADE COMMENT '级联外键：如果某评价被删去了所有对应点赞关联一起全丢弃清理',
  CONSTRAINT `review_likes_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE COMMENT '级联外键：同上述用户删号操作'
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
-- 以下为 各个初始化表结构中的基础测试数据插入 (INSERT INTO)
-- <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
-- ========================================================

INSERT INTO `users` VALUES 
(1,'stu2',NULL,'scrypt:32768:8:1$L2y3y5KQVGDUmzeR$cdeff6deb40ed5aa297f266bc440dd7c1fa2fffd22979aeaf4289c4579dfcfdaaff1a2cb2d1c58d98f2a672e09278c6a267b39bf4d98e56d589ee1c7bd2d20ab','student','active','2026-02-27 17:16:20','2026-02-27 17:16:20'),
(2,'tea1',NULL,'scrypt:32768:8:1$ZdIPsaiiawhj48LK$2f7928360787b3365b1aa8ee0d2a0cc6b83f935a538dc0fa6d81569e192bfbf084c9256561fe5846a7e984d0a14839ae9b8e355e8ddeb66605aec3273b8b1090','teacher','active','2026-02-27 17:45:28','2026-02-27 17:45:28'),
(3,'stu1',NULL,'scrypt:32768:8:1$5MoK2vcXRXciP562$b62ac89d937572f8c62dbdb828b9516c8f4770cd3b23bdc4e4e57c74d85401650172f0df40ff7f010ac3a4c7bc5be23a4274a69592d71b7ad5d57fdc1fe2967b','student','active','2026-02-28 12:32:35','2026-02-28 12:32:35'),
(4,'stu3','3526712486@qq.com','scrypt:32768:8:1$2CNRSHK3YSVyCm9D$fb41330dab023ea989791e02fa96382d8180021b24d175c64992217e400757ed00818166fe5c843c1313a690c66cadbe7a651b6235f2fbd2dd35b77fe781ed33','student','active','2026-03-01 11:42:10','2026-03-01 11:42:10');

INSERT INTO `courses` VALUES 
(1,'高等数学','极限、导数与积分的系统学习',2,'draft','2026-02-28 20:48:39','2026-02-28 18:07:51'),
(2,'Python 数据分析','Pandas、NumPy 与可视化实战',2,'draft','2026-02-28 20:48:39','2026-02-28 18:07:49'),
(3,'数据库原理','关系模型、SQL 与索引优化',2,'published','2026-02-28 20:48:39','2026-03-01 06:09:02'),
(5,'操作系统基础','进程线程、内存与文件系统',2,'published','2026-02-28 20:48:39','2026-03-01 05:49:26');

INSERT INTO `contents` VALUES 
(10,3,'image','第一讲','fdf0816d2f334917803c9e8021b3c586.png',NULL,75773,'2026-03-01 06:29:23'),
(11,3,'image','第二讲','7d2833a95d874b0886524e993a05ecd3.png',NULL,63617,'2026-03-01 06:29:45'),
(12,3,'image','第三讲','f8c90a5a6e6540649731c5c7d454bbb0.png',NULL,47834,'2026-03-01 06:29:57'),
(13,3,'image','第四讲','e022d34c4bb54204949219cd0a391c99.png',NULL,46275,'2026-03-01 06:30:12'),
(14,3,'image','第五讲','8cf12cca0c2a4bea93308d765a6880ca.png',NULL,53245,'2026-03-01 06:30:26'),
(15,3,'image','第六讲','ec23c9fe546b4ee285b2883037b5fefa.png',NULL,49716,'2026-03-01 06:30:35'),
(16,3,'image','第七讲','f9a2f684219e4bc48aa3c3c5823ceb30.png',NULL,46065,'2026-03-01 06:30:51'),
(17,3,'image','第八讲','33d940f8fbe94bcaaa28fd7ba0789993.png',NULL,56918,'2026-03-01 06:31:12'),
(18,3,'image','第九讲','6c43605590ef44209e0a231da9fc7d7f.png',NULL,48930,'2026-03-01 06:31:30'),
(19,3,'image','第十讲','ef3e7e10fe4246769e36c8a7ad1a9c0a.png',NULL,56073,'2026-03-01 06:31:41'),
(20,5,'image','第一讲','1f5e6a0ac10f4b9bb6ab8a5ac02aa2b9.png',NULL,72721,'2026-03-01 06:50:01'),
(21,5,'image','期末复习1','20675e02fb0346f0b34f50e8a00a2fbe.png',NULL,72721,'2026-03-01 06:50:57');

INSERT INTO `enrollments` VALUES 
(1,1,1,'dropped','2026-02-28 20:48:39'),
(2,2,1,'dropped','2026-02-28 20:48:39'),
(4,5,1,'enrolled','2026-02-28 17:02:23');

INSERT INTO `messages` VALUES 
(1,1,1,NULL,'老师好，极限这块我还想再练几道题。','2026-02-28 20:48:39'),
(2,1,2,1,'没问题，我稍后补充练习题。','2026-02-28 20:48:39'),
(3,2,1,NULL,'Pandas 的 groupby 有推荐资料吗？','2026-02-28 20:48:39'),
(4,5,2,NULL,'123','2026-02-28 15:34:04'),
(5,1,2,NULL,'123','2026-02-28 15:34:27'),
(6,5,2,NULL,'123','2026-02-28 17:07:09');

INSERT INTO `notes` VALUES 
(1,1,'数据库1','数据库知识：\n1.123\n2.\n3.','2026-03-01 10:39:19','2026-03-01 11:00:08');

INSERT INTO `progress` VALUES 
(6,21,1,100,'completed','2026-03-01 09:56:01','2026-03-01 09:56:01'),
(7,20,1,100,'completed','2026-03-01 09:56:04','2026-03-01 09:56:04');

INSERT INTO `reviews` VALUES 
(1,5,1,4,'很可以，能学到不少有用的东西','2026-03-01 05:40:49',NULL,NULL,2);

INSERT INTO `review_likes` VALUES 
(1,1,2,'2026-03-01 07:25:52'),
(3,1,1,'2026-03-01 07:26:05');

SET FOREIGN_KEY_CHECKS=1;