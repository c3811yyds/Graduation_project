<template>
  <div class="page" v-if="course">
    <header class="head">
      <div>
        <h1>{{ course.title }}</h1>
        <p class="muted">{{ course.description || "暂无课程简介" }}</p>
        <div class="meta">
          <span class="tag">课程ID: {{ course.id }}</span>
            <span class="tag">授课老师: {{ course.teacher_name || "未知" }}</span>
            <span class="tag">状态: {{ course.status }}</span>
          <span class="tag rating-tag">综合评分: {{ course.rating > 0 ? course.rating + ' / 5.0' : '暂无评分' }} ({{ course.review_count || 0 }}条)</span>
          <span v-if="isStudent" class="tag">
            {{ isEnrolled ? "已选课程" : "未选课程" }}
          </span>
        </div>
      </div>

      <div class="actions">
        <button class="btn" @click="goHome">返回首页</button>

        <button v-if="isStudent && isEnrolled" class="btn btn-outline" @click="showReviewModal = true" :disabled="hasReviewed">
          {{ hasReviewed ? "已评价" : "评价课程" }}
        </button>

        <button
          v-if="isTeacherOwner && course.status === 'draft'"
          class="btn btn-primary"
          @click="publishCourse"
        >
          发布本课程
        </button>

        <button
          v-if="isTeacherOwner && course.status === 'draft'"
          class="btn btn-danger"
          @click="deleteCourse"
        >
          删除本课程
        </button>

        <button
          v-if="isTeacherOwner && course.status === 'published'"
          class="btn btn-danger"
          @click="unpublishCourse"
        >
          下架本课程
        </button>

        <button
          v-if="isStudent && !isEnrolled && course.status === 'published'"
          class="btn btn-primary"
          @click="enrollCourse"
        >
          立即选课
        </button>

        <button
          v-if="isStudent && isEnrolled"
          class="btn btn-danger"
          @click="dropCourse"
        >
          退课
        </button>
      </div>
    </header>

    <!-- 剧场播放模式 (Theather Mode) -->
    <section v-if="currentPlayingContent" class="panel theater-mode-panel" style="margin-top: 24px; padding: 24px; background: #1e293b; color: #fff; border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="margin: 0; display: flex; align-items: center; gap: 8px;">
          <span style="display: inline-block; padding: 4px 8px; background: #3b82f6; border-radius: 6px; font-size: 14px;">正在播放</span>
          {{ currentPlayingContent.title }}
        </h2>
        <button class="btn" style="background: rgba(255,255,255,0.1); color: #fff; border: 1px solid rgba(255,255,255,0.2);" @click="closePlayer">关闭播放器</button>
      </div>
      
      <div class="player-container" style="background: #000; border-radius: 8px; overflow: hidden; display: flex; justify-content: center; align-items: center; min-height: 480px; max-height: 70vh;">
        <!-- 视频/音频类 -->
        <video v-if="['video', 'audio'].includes(currentPlayingContent.type) || currentPlayingUrl.match(/\.(mp4|webm|ogg|mp3|wav)$/i)" 
               :src="currentPlayingUrl" 
               controls 
               autoplay 
               controlsList="nodownload"
               style="width: 100%; height: 100%; max-height: 70vh; outline: none;"></video>
        
        <!-- 文档/图片类 -->
        <iframe v-else-if="['doc', 'image'].includes(currentPlayingContent.type) || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(currentPlayingContent.type)"
                :src="currentPlayingUrl" 
                style="width: 100%; height: 70vh; border: none; background: #fff;"></iframe>
        
        <!-- 其他不支持在线预览的格式 -->
        <div v-else style="padding: 60px; color: #cbd5e1; text-align: center;">
          <div style="font-size: 48px; margin-bottom: 16px;">📁</div>
          <p style="margin-bottom: 24px; font-size: 16px;">该文件格式暂不支持在线预览，请下载后使用本地应用查看。</p>
          <button class="btn btn-primary" style="padding: 10px 24px; font-size: 16px;" @click="downloadContent(currentPlayingContent.id)">立即下载</button>
        </div>
      </div>
    </section>

    <!-- 学生未选课提示 -->
    <section v-if="isStudent && !isEnrolled" class="panel warn">
      <h3>你尚未选修本课程</h3>
      <p class="muted">可先查看课程信息；选课后可访问课件、留言和学习进度。</p>
    </section>

    <!-- 学习进度板 (学生可见) -->
    <section v-if="isStudent && isEnrolled" class="panel">
      <h2>我的学习进度</h2>
      <div class="progress-bg">
        <div class="progress-fill" :style="{ width: studentProgressData.progress + '%' }"></div>
      </div>
      <p class="progress-text">
        当前进度: <strong>{{ studentProgressData.progress }}%</strong> 
        <span class="muted">({{ studentProgressData.completed }} / {{ studentProgressData.total }} 个课件已学)</span>
      </p>
    </section>

    <!-- 学习进度板 (教师可见) -->
    <section v-if="isTeacherOwner" class="panel">
      <h2>学生学习进度概况</h2>
      <table v-if="enrolledStudentsData.length" class="progress-table">
        <thead>
          <tr>
            <th>学生姓名</th>
            <th>已学课件 / 总数</th>
            <th>进度百分比</th>
            <th>状态条</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="st in enrolledStudentsData" :key="st.id">
            <td>{{ st.real_name || st.username }}</td>
            <td>{{ st.completed }} / {{ st.total }}</td>
            <td style="font-weight: 600;">{{ st.progress }}%</td>
            <td>
              <div class="mini-progress-bg">
                <div class="mini-progress-fill" :style="{ width: st.progress + '%' }"></div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">暂无学生选修</p>
    </section>

    <!-- 课程内容 -->
    <section class="panel">
      <h2>课程内容</h2>

      <template v-if="true">
        <p class="muted" v-if="isStudent && !isEnrolled">（提示：选课后可参与进度记录，非选课状态也可浏览以下内容）</p>
        <!-- 教师上传 -->
        <div v-if="isTeacherOwner" class="upload-box">
          <h3>上传课件（教师）</h3>
          <p class="muted" style="margin-bottom: 12px; font-size: 13px;">
            支持格式：视频(mp4/webm等)、音频(mp3等)、图片(jpg/png等)、文档(pdf/doc/ppt等)以及压缩包。
          </p>
          <div class="upload-row">
            <input v-model="uploadTitle" placeholder="课件标题（留空自动生成：第X讲-文件名）" style="flex:1" />
            <input type="file" @change="pickFile" accept=".mp4,.webm,.ogg,.mov,.avi,.mp3,.wav,.flac,.aac,.m4a,.png,.jpg,.jpeg,.gif,.webp,.svg,.bmp,.ico,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.csv,.md,.zip,.rar,.7z,.tar,.gz" />
            <button class="btn btn-primary" :disabled="!uploadFile" @click="uploadContent">
              上传
            </button>
          </div>
        </div>

        <div class="list">
          <article v-for="item in contents" :key="item.id" class="item">
            <div>
              <h4>{{ item.title }}</h4>
              <p class="muted">类型：{{ item.type }}</p>
            </div>
            <div class="actions">
              <button class="btn" @click="openContent(item.id)">播放/预览</button>
              <button class="btn" @click="downloadContent(item.id)">下载</button>
              <button
                v-if="isTeacherOwner"
                class="btn"
                @click="renameContent(item.id, item.title)"
              >
                重命名
              </button>
              <button
                v-if="isTeacherOwner"
                class="btn btn-danger"
                @click="deleteContent(item.id)"
              >
                删除
              </button>
            </div>
          </article>
          <p v-if="!contents.length" class="muted">暂无课程内容</p>
        </div>
      </template>
    </section>

    <!-- 留言 -->
    <section class="panel" v-if="me">
      <h2>课程留言</h2>
      
      <p class="muted" v-if="isStudent && !isEnrolled">请先选课后参与留言，当前仅可查看。</p>

      <template v-if="true">
        <div class="msg-form" v-if="isTeacher || (isStudent && isEnrolled)">
          <textarea v-model="newMessage" rows="3" placeholder="输入留言内容..." />
          <button class="btn btn-primary" @click="sendMessage">发送留言</button>
        </div>

        <ul class="msg-list">
          <li v-for="m in messages" :key="m.id">
            <div class="msg-top">
              <strong>#{{ m.id }}</strong>
              <span class="muted">用户{{ m.sender_id }} · {{ formatTime(m.created_at) }}</span>
            </div>
            <div>{{ m.content }}</div>
          </li>
        </ul>

        <p v-if="!messages.length" class="muted">暂无留言</p>
      </template>
    </section>

    <!-- 课程评价模态框与列表区 -->
    <section class="card detail-section">
      <h3>课程评价 ({{ reviews.length }})</h3>
      
      <ul class="msg-list" v-if="reviews.length > 0">
        <li v-for="r in reviews" :key="r.id">
          <div class="msg-top">
            <strong>{{ r.username }}</strong>
            <span class="rating-stars">
              {{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}
            </span>
            <span class="muted">· {{ formatTime(r.created_at) }}</span>
            <div style="flex:1"></div>
            <button class="btn btn-sm" :class="{ 'btn-primary': r.liked }" @click="toggleReviewLike(r)">
              赞 {{ r.likes_count }}
            </button>
            <button v-if="isTeacherOwner" class="btn btn-sm" @click="replyReview(r)">回复</button>
            <button v-if="isTeacherOwner" class="btn btn-sm btn-danger" @click="deleteReview(r.id)">删除</button>
          </div>
          <div class="msg-body" style="margin-top:0.5rem">
            {{ r.comment || "没有留下文字评论" }}
          </div>
          <div v-if="r.reply_content" class="teacher-reply" style="margin-top: 1rem; padding: 12px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #3b82f6;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <strong style="color: #1e3a8a; font-size: 0.95rem;">{{ course.teacher_name || '老师' }} <span style="font-weight: normal; color: #64748b; font-size: 0.85rem;">(授课老师)</span></strong>
              <span class="muted" style="font-size: 0.8rem;">{{ formatTime(r.reply_time) }}</span>
            </div>
            <div style="font-size: 0.95rem; color: #334155; line-height: 1.5; white-space: pre-wrap;">{{ r.reply_content }}</div>
          </div>
        </li>
      </ul>
      <p v-else class="muted">还没有任何人评价该课程。</p>
    </section>

    <!-- 评价弹窗 -->
    <div v-if="showReviewModal" class="modal-overlay">
      <div class="modal card">
        <header class="modal-header">
          <h3>发表评价</h3>
          <button class="close-btn" @click="showReviewModal = false">×</button>
        </header>
        <div class="modal-body">
          <div style="margin-bottom: 1rem;">
             <label>评分 (1-5星):</label>
             <select v-model="newReviewRating" style="margin-left: 10px; padding:0.25rem;">
               <option :value="5">⭐⭐⭐⭐⭐ (5分)</option>
               <option :value="4">⭐⭐⭐⭐ (4分)</option>
               <option :value="3">⭐⭐⭐ (3分)</option>
               <option :value="2">⭐⭐ (2分)</option>
               <option :value="1">⭐ (1分)</option>
             </select>
          </div>
          <textarea v-model="newReviewComment" rows="4" style="width:100%" placeholder="说说你对这门课的感受...向其他同学分享（可选）" />
        </div>
        <div class="modal-actions" style="margin-top: 1rem; text-align:right;">
          <button class="btn btn-primary" @click="submitReview">提交评价</button>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="page">
    <p>课程不存在或加载失败。</p>
    <button class="btn" @click="goHome">返回首页</button>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";

const route = useRoute();
const router = useRouter();
const courseId = Number(route.params.id);

const me = ref(null);
const course = ref(null);
const contents = ref([]);
const messages = ref([]);

const studentProgressData = ref({ progress: 0, completed: 0, total: 0 });
const enrolledStudentsData = ref([]);

const reviews = ref([]);
const newReviewRating = ref(5);
const newReviewComment = ref("");
const showReviewModal = ref(false);

const newMessage = ref("");
const uploadFile = ref(null);
const uploadTitle = ref("");

const currentPlayingContent = ref(null);
const currentPlayingUrl = ref("");

const isStudent = computed(() => me.value?.role === "student");
const isTeacher = computed(() => me.value?.role === "teacher");

const isEnrolled = computed(() => {
  if (!isStudent.value || !course.value) return false;
  return !!(course.value.is_enrolled || course.value.enrollment_status === "enrolled");
});

const isTeacherOwner = computed(() => {
  if (!isTeacher.value || !me.value || !course.value) return false;
  return Number(course.value.teacher_id) === Number(me.value.id);
});

const hasReviewed = computed(() => {
  if (!isStudent.value || !me.value) return false;
  return reviews.value.some(r => r.user_id === me.value.id);
});

function goHome() {
  router.push("/");
}

function token() {
  return sessionStorage.getItem("token") || "";
}

function formatTime(v) {
  if (!v) return "-";
  try {
    return new Date(v).toLocaleString();
  } catch {
    return v;
  }
}

async function loadMe() {
  const t = token();
  if (!t) {
    me.value = null;
    return;
  }
  try {
    const res = await http.get("/users/me");
    me.value = res.data.data || null;
  } catch {
    me.value = null;
    sessionStorage.removeItem("token");
  }
}

// [后端映射]: GET /api/courses -> 如果本地暂缓了基本信息，直接做展示的兜底拿数据
async function loadCourseFromList() {
  const res = await http.get("/courses");
  const list = res.data.data || [];
  course.value = list.find((c) => Number(c.id) === courseId) || null;
}

// [后端映射]: 组合请求获取特定课程资源 (GET /api/courses/<id>/contents) 和 弹幕区评论等消息互动数据
async function loadLearningData() {
  if (!course.value) return;
  if (!me.value) {
    studentProgressData.value = { progress: 0, completed: 0, total: 0 };
    enrolledStudentsData.value = [];
  }
  if (isStudent.value && !isEnrolled.value) {
    studentProgressData.value = { progress: 0, completed: 0, total: 0 };
  }
  const reqs = [
    http.get(`/courses/${courseId}/contents`),
    http.get(`/courses/${courseId}/messages`),
    http.get(`/courses/${courseId}/reviews`),
  ];

  if (isStudent.value) {
    reqs.push(http.get(`/courses/${courseId}/progress`));
  } else if (isTeacherOwner.value) {
    reqs.push(http.get(`/courses/${courseId}/students`));
  }

  const results = await Promise.all(reqs);
  contents.value = results[0].data.data || [];
  messages.value = results[1].data.data || [];
  reviews.value = results[2].data.data || [];

  if (isStudent.value && results[3]) {
    studentProgressData.value = results[3].data.data || { progress: 0, completed: 0, total: 0 };
  } else if (isTeacherOwner.value && results[3]) {
    enrolledStudentsData.value = results[3].data.data?.students || [];
  }
}

async function refreshPage() {
  try {
    await loadMe();
    await loadCourseFromList();
    await loadLearningData();
  } catch (e) {
    alert(e?.response?.data?.message || "加载失败");
  }
}

// [后端映射]: POST /api/courses/<id>/enroll -> 学生端绑定该课的关系表
async function enrollCourse() {
  try {
    await http.post(`/courses/${courseId}/enroll`);
    await refreshPage();
  } catch (e) {
    alert(e?.response?.data?.message || "选课失败");
  }
}

// [后端映射]: DELETE /api/courses/<id>/enroll -> 学生端退课动作
async function dropCourse() {
  try {
    await http.delete(`/courses/${courseId}/enroll`);
    await refreshPage();
  } catch (e) {
    alert(e?.response?.data?.message || "退课失败");
  }
}

// [后端映射]: PUT /api/courses/<id>/publish -> 教师从详情页发品上线草稿
async function publishCourse() {
  try {
    await http.put(`/courses/${courseId}/publish`);
    await refreshPage();
  } catch (e) {
    alert(e?.response?.data?.message || "发布失败");
  }
}

// [后端映射]: PUT /api/courses/<id>/unpublish -> 教师强制冻结已发出的课程回退
async function unpublishCourse() {
  if (!confirm("确认下架该课程吗？下架后学生将无法选课。")) return;
  try {
    await http.put(`/courses/${courseId}/unpublish`);
    await refreshPage();
  } catch (e) {
    alert(e?.response?.data?.message || "下架失败");
  }
}

// [后端映射]: DELETE /api/courses/<id> -> 物理抹除属于自己的垃圾草稿课程
async function deleteCourse() {
  if (!confirm("警告：确认要永久删除该课程吗？相关数据和课件将全部清空，不可恢复！")) return;
  try {
    await http.delete(`/courses/${courseId}`);
    alert("课程已永久删除");
    goHome();
  } catch (e) {
    alert(e?.response?.data?.message || "删除失败");
  }
}

// [后端映射]: POST /api/courses/<id>/reviews -> 把带有星级和评语的内容塞回数据库评价区
async function submitReview() {
  if (!newReviewRating.value) {
    alert("请选择评分");
    return;
  }
  try {
    await http.post(`/courses/${courseId}/reviews`, {
      rating: newReviewRating.value,
      comment: newReviewComment.value,
    });
    alert("评价成功！");
    showReviewModal.value = false;
    newReviewComment.value = "";
    newReviewRating.value = 5;
    // reload data to see the new review
    await loadCourseFromList();
    await loadLearningData();
  } catch (e) {
    alert(e?.response?.data?.message || "评价失败");
  }
}

// [后端映射]: 点赞可能未直接在路由体现但也作为扩展动作属于交互部分
async function toggleReviewLike(r) {
  if (!me.value) {
    alert("请先登录");
    return;
  }
  try {
    const res = await http.post(`/courses/${courseId}/reviews/${r.id}/like`);
    r.liked = !r.liked;
    r.likes_count = res.data.data.likes_count;
    reviews.value.sort((a, b) => b.likes_count - a.likes_count || new Date(b.created_at) - new Date(a.created_at));
  } catch (e) {
    alert(e?.response?.data?.message || "操作失败");
  }
}

// [后端映射]: 教师对评论追加回复
async function replyReview(r) {
  const replyContent = prompt("请输入回复内容：", r.reply_content || "");
  if (replyContent === null) return;
  try {
    await http.put(`/courses/${courseId}/reviews/${r.id}/reply`, {
      reply_content: replyContent,
    });
    await loadLearningData();
  } catch (e) {
    alert(e?.response?.data?.message || "回复失败");
  }
}

// [后端映射]: 抹除掉特定的一条评论信息
async function deleteReview(reviewId) {
  if (!confirm("确认删除该评价吗？")) return;
  try {
    await http.delete(`/courses/${courseId}/reviews/${reviewId}`);
    await loadLearningData();
  } catch (e) {
    alert(e?.response?.data?.message || "删除失败");
  }
}

// [后端映射]: POST /api/courses/<id>/messages -> 发送学习讨论区的一条留言
async function sendMessage() {
  const txt = newMessage.value.trim();
  if (!txt) {
    alert("请输入留言内容");
    return;
  }
  try {
    await http.post(`/courses/${courseId}/messages`, { content: txt });
    newMessage.value = "";
    await loadLearningData();
  } catch (e) {
    alert(e?.response?.data?.message || "发送失败");
  }
}

function pickFile(e) {
  if (e.target.files && e.target.files.length > 0) {
    uploadFile.value = e.target.files[0];
  } else {
    uploadFile.value = null;
  }
}

  // [后端映射]: POST /api/courses/<id>/contents/upload -> 以 FormData 上传文件资料入 storage
async function uploadContent() {
    if (!uploadFile.value) return;
    const formData = new FormData();
    formData.append("file", uploadFile.value);
    
    // 智能标题设定逻辑：如果有填名字就用填的，没填就自动生成 "第 X 讲 - 文件名"
    let finalTitle = uploadTitle.value.trim();
    if (!finalTitle) {
      const nextIndex = contents.value.length + 1;
      const originalName = uploadFile.value.name.replace(/\.[^/.]+$/, ""); // 去掉扩展名
      finalTitle = `第 ${nextIndex} 讲 - ${originalName}`;
    }
    formData.append("title", finalTitle);

    try {
      await http.post(`/courses/${courseId}/contents/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      alert("上传成功");
      uploadFile.value = null;
      uploadTitle.value = "";
      await loadLearningData();
    } catch (e) {
      alert(e?.response?.data?.message || "上传失败");
    }
  }

  async function openContent(contentId) {
    try {
      if (isStudent.value) {
        await http.post(`/contents/${contentId}/view`);
        await loadLearningData();
      }
    } catch {}
    const t = token();
    const target = contents.value.find(c => c.id === contentId);
    if(target) {
        currentPlayingContent.value = target;
        currentPlayingUrl.value = `/api/contents/${contentId}/file?token=${t}`;
        // 平滑滚动回顶部以便观看
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        window.open(`/api/contents/${contentId}/file?token=${t}`, "_blank");
    }
  }

  function closePlayer() {
    currentPlayingContent.value = null;
    currentPlayingUrl.value = "";
  }

  // [后端映射]: GET /api/contents/<id>/file -> 按资源 ID 流式下载实体资料文件
async function downloadContent(contentId) {
    try {
      if (isStudent.value) {
        await http.post(`/contents/${contentId}/view`);
        await loadLearningData();
      }
    } catch {}
    const t = token();
    const a = document.createElement("a");
    a.href = `/api/contents/${contentId}/file?download=1&token=${t}`;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  // [后端映射]: DELETE /api/contents/<id> -> 教师删除此课时文件节点
async function deleteContent(contentId) {
    if (!confirm("确认删除该课件吗？")) return;
    try {
      await http.delete(`/contents/${contentId}`);
      await loadLearningData();
    } catch (e) {
      alert(e?.response?.data?.message || "删除失败");
    }
  }

  async function renameContent(contentId, oldTitle) {
    const newTitle = prompt("修改课件名称", oldTitle);
    if (!newTitle || newTitle.trim() === "" || newTitle === oldTitle) return;
    try {
      await http.put(`/contents/${contentId}`, { title: newTitle });
      await loadLearningData();
    } catch (e) {
      alert(e?.response?.data?.message || "重命名失败");
    }
  }

onMounted(refreshPage);
</script>

<style scoped>
.page {
  max-width: 1000px;
  margin: 0 auto;
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 20px;
}
.head h1 {
  margin: 0 0 10px;
  font-weight: 800;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 20px;
  background: var(--card);
  box-shadow: var(--shadow);
}
.warn {
  border-color: #D97706;
  background: #FEF3C7;
  color: #92400E;
}
.tag {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  background: var(--card);
  box-shadow: none;
}
.upload-box {
  margin-bottom: 10px;
}
.upload-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.upload-row input {
  border: 1.5px solid var(--line);
  border-radius: 8px;
  padding: 8px 12px;
  font-family: inherit;
  transition: all .2s;
  outline: none;
}
.upload-row input:focus {
  border-color: var(--primary);
}
.list .item {
  border: 1.5px solid var(--text); /* 加粗内部小块边框 */
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  background: var(--card);
  box-shadow: 2px 2px 0px rgba(168, 162, 158, 0.2);
}
.msg-form textarea {
  width: 100%;
  border: 1.5px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  font-family: inherit;
  margin-bottom: 10px;
  outline: none;
  resize: vertical;
}
.msg-form textarea:focus {
  border-color: var(--primary);
}
.msg-list {
  list-style: none;
  padding: 0;
  margin-top: 10px;
}
.msg-list li {
  border-top: 1.5px dashed var(--line);
  padding: 12px 0;
}
.msg-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.btn {
  border: 1px solid #d0d7de;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}
.btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.btn-danger {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}
.btn-outline {
  border-color: #2563eb;
  color: #2563eb;
  background: transparent;
}
.muted {
  color: #64748b;
}

/* 进度条样式 */
.progress-bg {
  width: 100%;
  height: 24px;
  background: var(--line);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 16px;
  border: 1px solid var(--text);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #14B8A6, #0F766E);
  transition: width 0.5s ease-out;
}
.progress-text {
  margin-top: 12px;
  font-size: 15px;
}
.progress-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
  font-size: 14px;
}
.progress-table th, .progress-table td {
  border: 1px solid var(--line);
  padding: 12px 16px;
  text-align: left;
}
.progress-table th {
  background: var(--bg);
  font-weight: 600;
  color: var(--text);
}
.mini-progress-bg {
  width: 100%;
  height: 8px;
  background: #E2E8F0;
  border-radius: 4px;
  overflow: hidden;
}
.mini-progress-fill {
  height: 100%;
  background: #0F766E;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.rating-tag {
  background-color: #FEF3C7;
  color: #D97706;
  border-color: #FCD34D;
  font-weight: 500;
}

.rating-stars {
  color: #F59E0B;
  margin: 0 0.5rem;
  font-size: 1.1rem;
  letter-spacing: 2px;
}

/* 模态框基础样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
}
.modal {
  width: 90%;
  max-width: 400px;
  padding: 1.5rem;
  position: relative;
  background: white;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border);
  padding-bottom: 1rem;
  margin-bottom: 1rem;
}
.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
}
.close-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--muted);
}
.close-btn:hover {
  color: var(--text);
}
</style>
