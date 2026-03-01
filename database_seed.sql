/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `contents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_id` int NOT NULL,
  `type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `url_or_path` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `duration_seconds` int DEFAULT NULL,
  `size_bytes` bigint DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_contents_course_id` (`course_id`),
  CONSTRAINT `contents_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `contents` VALUES (10,3,'image','第一讲','fdf0816d2f334917803c9e8021b3c586.png',NULL,75773,'2026-03-01 06:29:23'),(11,3,'image','第二讲','7d2833a95d874b0886524e993a05ecd3.png',NULL,63617,'2026-03-01 06:29:45'),(12,3,'image','第三讲','f8c90a5a6e6540649731c5c7d454bbb0.png',NULL,47834,'2026-03-01 06:29:57'),(13,3,'image','第四讲','e022d34c4bb54204949219cd0a391c99.png',NULL,46275,'2026-03-01 06:30:12'),(14,3,'image','第五讲','8cf12cca0c2a4bea93308d765a6880ca.png',NULL,53245,'2026-03-01 06:30:26'),(15,3,'image','第六讲','ec23c9fe546b4ee285b2883037b5fefa.png',NULL,49716,'2026-03-01 06:30:35'),(16,3,'image','第七讲','f9a2f684219e4bc48aa3c3c5823ceb30.png',NULL,46065,'2026-03-01 06:30:51'),(17,3,'image','第八讲','33d940f8fbe94bcaaa28fd7ba0789993.png',NULL,56918,'2026-03-01 06:31:12'),(18,3,'image','第九讲','6c43605590ef44209e0a231da9fc7d7f.png',NULL,48930,'2026-03-01 06:31:30'),(19,3,'image','第十讲','ef3e7e10fe4246769e36c8a7ad1a9c0a.png',NULL,56073,'2026-03-01 06:31:41'),(20,5,'image','第一讲','1f5e6a0ac10f4b9bb6ab8a5ac02aa2b9.png',NULL,72721,'2026-03-01 06:50:01'),(21,5,'image','期末复习1','20675e02fb0346f0b34f50e8a00a2fbe.png',NULL,72721,'2026-03-01 06:50:57');
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `courses` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `teacher_id` int NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_courses_teacher_id` (`teacher_id`),
  KEY `ix_courses_title` (`title`),
  CONSTRAINT `courses_ibfk_1` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `courses` VALUES (1,'高等数学','极限、导数与积分的系统学习',2,'draft','2026-02-28 20:48:39','2026-02-28 18:07:51'),(2,'Python 数据分析','Pandas、NumPy 与可视化实战',2,'draft','2026-02-28 20:48:39','2026-02-28 18:07:49'),(3,'数据库原理','关系模型、SQL 与索引优化',2,'published','2026-02-28 20:48:39','2026-03-01 06:09:02'),(5,'操作系统基础','进程线程、内存与文件系统',2,'published','2026-02-28 20:48:39','2026-03-01 05:49:26');
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `enrollments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_id` int NOT NULL,
  `student_id` int NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `enrolled_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_course_student` (`course_id`,`student_id`),
  KEY `ix_enrollments_student_id` (`student_id`),
  KEY `ix_enrollments_course_id` (`course_id`),
  CONSTRAINT `enrollments_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `enrollments_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `enrollments` VALUES (1,1,1,'dropped','2026-02-28 20:48:39'),(2,2,1,'dropped','2026-02-28 20:48:39'),(4,5,1,'enrolled','2026-02-28 17:02:23');
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_id` int NOT NULL,
  `sender_id` int NOT NULL,
  `receiver_id` int DEFAULT NULL,
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_messages_sender_id` (`sender_id`),
  KEY `ix_messages_course_id` (`course_id`),
  KEY `ix_messages_receiver_id` (`receiver_id`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`),
  CONSTRAINT `messages_ibfk_3` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `messages` VALUES (1,1,1,NULL,'老师好，极限这块我还想再练几道题。','2026-02-28 20:48:39'),(2,1,2,1,'没问题，我稍后补充练习题。','2026-02-28 20:48:39'),(3,2,1,NULL,'Pandas 的 groupby 有推荐资料吗？','2026-02-28 20:48:39'),(4,5,2,NULL,'123','2026-02-28 15:34:04'),(5,1,2,NULL,'123','2026-02-28 15:34:27'),(6,5,2,NULL,'123','2026-02-28 17:07:09');
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `title` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_notes_user_id` (`user_id`),
  CONSTRAINT `notes_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `notes` VALUES (1,1,'数据库1','数据库知识：\n1.123\n2.\n3.','2026-03-01 10:39:19','2026-03-01 11:00:08');
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `progress` (
  `id` int NOT NULL AUTO_INCREMENT,
  `content_id` int NOT NULL,
  `student_id` int NOT NULL,
  `progress_percent` int NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_viewed_at` datetime NOT NULL,
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_content_student_progress` (`content_id`,`student_id`),
  KEY `ix_progress_content_id` (`content_id`),
  KEY `ix_progress_student_id` (`student_id`),
  CONSTRAINT `progress_ibfk_1` FOREIGN KEY (`content_id`) REFERENCES `contents` (`id`),
  CONSTRAINT `progress_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `progress` VALUES (6,21,1,100,'completed','2026-03-01 09:56:01','2026-03-01 09:56:01'),(7,20,1,100,'completed','2026-03-01 09:56:04','2026-03-01 09:56:04');
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `review_likes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `review_id` int NOT NULL,
  `user_id` int NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_review_user_like` (`review_id`,`user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `review_likes_ibfk_1` FOREIGN KEY (`review_id`) REFERENCES `reviews` (`id`) ON DELETE CASCADE,
  CONSTRAINT `review_likes_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `review_likes` VALUES (1,1,2,'2026-03-01 07:25:52'),(3,1,1,'2026-03-01 07:26:05');
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reviews` (
  `id` int NOT NULL AUTO_INCREMENT,
  `course_id` int NOT NULL,
  `user_id` int NOT NULL,
  `rating` int NOT NULL,
  `comment` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT NULL,
  `reply_content` text COLLATE utf8mb4_unicode_ci,
  `reply_time` datetime DEFAULT NULL,
  `likes_count` int DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `ix_reviews_user_id` (`user_id`),
  KEY `ix_reviews_course_id` (`course_id`),
  CONSTRAINT `reviews_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `reviews_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `reviews` VALUES (1,5,1,4,'很可以，能学到不少有用的东西','2026-03-01 05:40:49',NULL,NULL,2);
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
INSERT INTO `users` VALUES (1,'stu2',NULL,'scrypt:32768:8:1$L2y3y5KQVGDUmzeR$cdeff6deb40ed5aa297f266bc440dd7c1fa2fffd22979aeaf4289c4579dfcfdaaff1a2cb2d1c58d98f2a672e09278c6a267b39bf4d98e56d589ee1c7bd2d20ab','student','active','2026-02-27 17:16:20','2026-02-27 17:16:20'),(2,'tea1',NULL,'scrypt:32768:8:1$ZdIPsaiiawhj48LK$2f7928360787b3365b1aa8ee0d2a0cc6b83f935a538dc0fa6d81569e192bfbf084c9256561fe5846a7e984d0a14839ae9b8e355e8ddeb66605aec3273b8b1090','teacher','active','2026-02-27 17:45:28','2026-02-27 17:45:28'),(3,'stu1',NULL,'scrypt:32768:8:1$5MoK2vcXRXciP562$b62ac89d937572f8c62dbdb828b9516c8f4770cd3b23bdc4e4e57c74d85401650172f0df40ff7f010ac3a4c7bc5be23a4274a69592d71b7ad5d57fdc1fe2967b','student','active','2026-02-28 12:32:35','2026-02-28 12:32:35'),(4,'stu3','3526712486@qq.com','scrypt:32768:8:1$2CNRSHK3YSVyCm9D$fb41330dab023ea989791e02fa96382d8180021b24d175c64992217e400757ed00818166fe5c843c1313a690c66cadbe7a651b6235f2fbd2dd35b77fe781ed33','student','active','2026-03-01 11:42:10','2026-03-01 11:42:10');
