<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import http from "../api/http";

const router = useRouter();
const me = ref(null);
const courses = ref([]);

const enrolledCourses = computed(() =>
  courses.value.filter((c) => c.is_enrolled || c.enrollment_status === "enrolled")
);
const availableCourses = computed(() =>
  courses.value.filter((c) => !(c.is_enrolled || c.enrollment_status === "enrolled"))
);

// 教师视角的课程分类
const teacherMyDraftCourses = computed(() =>
  courses.value.filter(c => c.status === "draft" && c.teacher_id === me.value?.id)
);
const teacherMyPublishedCourses = computed(() =>
  courses.value.filter(c => c.status === "published" && c.teacher_id === me.value?.id)
);
const teacherOtherPublishedCourses = computed(() =>
  courses.value.filter(c => c.status === "published" && c.teacher_id !== me.value?.id)
);// [功能说明]: 页面初始化时检查是否有 Token 并加载当前用户信息，判断是学生还是教师
async function loadMe() {
  const token = sessionStorage.getItem("token");
  if (!token) {
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

// [功能说明]: 请求后端获取课程列表，供下方卡片渲染
async function loadCourses() {
  const res = await http.get("/courses");
  courses.value = res.data.data || [];
}

// [功能说明]: 卡片里的 "查看详情" / "进入课程" 按钮触发，跳转到 CourseDetailView
function openDetail(id) {
  router.push(`/courses/${id}`);
}

// [功能说明]: 学生点击 "选课" 按钮触发，后端建立绑定关系后刷新列表
async function enroll(courseId) {
  try {
    await http.post(`/courses/${courseId}/enroll`);
    await loadCourses();
  } catch (e) {
    alert(e?.response?.data?.message || "选课失败");
  }
}

// [功能说明]: 学生点击 "退课" 按钮触发，解除选修绑定
async function drop(courseId) {
  try {
    await http.delete(`/courses/${courseId}/enroll`);
    await loadCourses();
  } catch (e) {
    alert(e?.response?.data?.message || "退课失败");
  }
}

// [功能说明]: 教师点击 "发布课程" 按钮触发，把草稿状态变为上架
async function publishCourse(courseId) {
  try {
    await http.put(`/courses/${courseId}/publish`);
    await loadCourses();
  } catch (e) {
    alert(e?.response?.data?.message || "发布失败");
  }
}

// [功能说明]: 教师点击 "下架课程" 按钮触发，使其变回草稿
async function unpublishCourse(courseId) {
  if (!confirm("确认下架该课程吗？下架后学生将无法选课。")) return;
  try {
    await http.put(`/courses/${courseId}/unpublish`);
    await loadCourses();
  } catch (e) {
    alert(e?.response?.data?.message || "下架失败");
  }
}

const showCreateModal = ref(false);
const newCourseTitle = ref("");
const newCourseDesc = ref("");

// [功能说明]: 教师确认 "创建新课程" 弹窗提交，向后端发送新课程数据
async function createCourse() {
  if (!newCourseTitle.value.trim()) {
    alert("课程标题不能为空");
    return;
  }
  try {
    await http.post("/courses", {
      title: newCourseTitle.value.trim(),
      description: newCourseDesc.value.trim(),
    });
    showCreateModal.value = false;
    newCourseTitle.value = "";
    newCourseDesc.value = "";
    await loadCourses();
  } catch (e) {
    alert(e?.response?.data?.message || "创建失败");
  }
}

  onMounted(async () => {
    await loadMe();
    await loadCourses();

    window.addEventListener('user-auth-changed', async () => {
      await loadMe();
      await loadCourses();
    });
  });
</script>

<template>
  <div class="page">
    
    <section class="hero">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1>课程广场</h1>
          <p class="muted">
            {{ me ? `当前用户：${me.username}（${me.role}）` : "未登录，可先浏览课程，登录后可学习" }}
          </p>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
          <button v-if="me && me.role === 'teacher'" class="btn btn-primary" @click="showCreateModal = true">
            + 创建新课程
          </button>
        </div>
      </div>
    </section>    <template v-if="me && me.role === 'student'">
      <section class="panel">
        <h2>已选课程（{{ enrolledCourses.length }}）</h2>
        <div class="grid">
          <!-- [视图结构]: 已选课程卡片列表，主要渲染拥有已选状态的课程块 -->
          <article class="card" v-for="c in enrolledCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <p>{{ c.description || "暂无简介" }}</p>
            <div class="actions">
              <button class="btn btn-primary" @click="openDetail(c.id)">进入课程</button>
              <button class="btn btn-danger" @click="drop(c.id)">退课</button>
            </div>
          </article>
          <p class="muted" v-if="!enrolledCourses.length">暂无已选课程</p>
        </div>
      </section>

      <section class="panel">
        <h2>可选课程（{{ availableCourses.length }}）</h2>
        <div class="grid">
          <article class="card" v-for="c in availableCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <p>{{ c.description || "暂无简介" }}</p>
            <div class="actions">
              <button class="btn" @click="openDetail(c.id)">查看详情</button>
              <button class="btn btn-primary" :disabled="c.status !== 'published'" @click="enroll(c.id)">
                {{ c.status === "published" ? "选课" : "未发布" }}
              </button>
            </div>
          </article>
          <p class="muted" v-if="!availableCourses.length">暂无未选课程</p>
        </div>
      </section>
    </template>

    <template v-else-if="me && me.role === 'teacher'">
      <section class="panel">
        <h2>我的草稿箱(仅自己可见)</h2>
        <div class="grid">
          <!-- [视图结构]: 教师特有的 "草稿课程" 区域，提供发布与内容的编辑权 -->
          <article class="card" v-for="c in teacherMyDraftCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <small style="display:block; margin-bottom:8px; color:#666">授课教师: {{ c.teacher_name }}</small>
            <p>{{ c.description || "暂无简介" }}</p>
            <div class="actions">
              <button class="btn" @click="openDetail(c.id)">查看详情/上传内容</button>
              <button class="btn btn-primary" @click="publishCourse(c.id)">发布课程</button>
            </div>
          </article>
          <p class="muted" v-if="!teacherMyDraftCourses.length">暂无草稿课程</p>
        </div>
      </section>

      <section class="panel">
        <h2>我发布的课程</h2>
        <div class="grid">
          <article class="card" v-for="c in teacherMyPublishedCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <small style="display:block; margin-bottom:8px; color:#666">授课教师: {{ c.teacher_name }}</small>
            <p>{{ c.description || "暂无简介" }}</p>
            <div class="actions">
              <button class="btn" @click="openDetail(c.id)">查看详情/管理</button>
              <button class="btn btn-danger" @click="unpublishCourse(c.id)">下架课程</button>
            </div>
          </article>
          <p class="muted" v-if="!teacherMyPublishedCourses.length">您暂未发布课程</p>
        </div>
      </section>

      <section class="panel">
        <h2>其他教师发布的课程</h2>
        <div class="grid">
          <article class="card" v-for="c in teacherOtherPublishedCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <small style="display:block; margin-bottom:8px; color:#666">授课教师: {{ c.teacher_name }}</small>
            <p>{{ c.description || "暂无简介" }}</p>
            <div class="actions">
              <button class="btn" @click="openDetail(c.id)">查看详情</button>
            </div>
          </article>
          <p class="muted" v-if="!teacherOtherPublishedCourses.length">暂无其他教师课程</p>
        </div>
      </section>
    </template>

    <section v-else class="panel">
      <h2>课程列表</h2>
      <div class="grid">
        <article class="card" v-for="c in courses" :key="c.id">
          <h3>{{ c.title }}</h3>
          <p>{{ c.description || "暂无简介" }}</p>
          <div class="actions">
            <button class="btn" @click="openDetail(c.id)">查看详情</button>
          </div>
        </article>
      </div>
    </section>

    <!-- [视图结构]: 点击顶部的 "+ 创建新课程" 后展示的悬浮表单(老师专用) -->
    <div v-if="showCreateModal" class="modal-mask" @click.self="showCreateModal = false">
      <div class="modal-card">
        <h3>创建新课程</h3>
        <div class="field">
          <label>课程名称</label>
          <input v-model="newCourseTitle" placeholder="输入课程标题" />
        </div>
        <div class="field">
          <label>课程简介</label>
          <textarea v-model="newCourseDesc" rows="3" placeholder="输入课程简介"></textarea>
        </div>
        <div class="actions" style="margin-top: 16px; justify-content: flex-end;">
          <button class="btn" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="createCourse">确定创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}
.hero {
  margin-bottom: 24px;
}
.panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 24px;
  background: var(--card);
  margin-bottom: 24px;
  box-shadow: var(--shadow);
}
.grid {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
}
.card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
  background: var(--card);
  transition: all .3s;
  box-shadow: var(--shadow);
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(15, 118, 110, 0.12);
  border-color: #cbd5e1;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
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
.muted {
  color: #64748b;
}

/* 弹窗样式 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-card {
  width: 400px;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
.field input, .field textarea {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
  font-family: inherit;
}
</style>