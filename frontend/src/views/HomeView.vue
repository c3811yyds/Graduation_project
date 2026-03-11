<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import http from "../api/http";

const router = useRouter();
const me = ref(null);
const courses = ref([]);
const advice = ref(null);
const guestSearchInput = ref("");
const guestSearchKeyword = ref("");
const studentAvailableSearchInput = ref("");
const studentAvailableSearchKeyword = ref("");
const teacherOtherSearchInput = ref("");
const teacherOtherSearchKeyword = ref("");

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
);

// [功能说明]: 课程搜索统一匹配课程标题、授课教师和课程简介三个字段。
function courseMatchesKeyword(course, keyword) {
  const normalizedKeyword = (keyword || "").trim().toLowerCase();
  if (!normalizedKeyword) return true;

  const haystack = [
    course.title,
    course.teacher_name,
    course.description,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return haystack.includes(normalizedKeyword);
}

const filteredAvailableCourses = computed(() =>
  availableCourses.value.filter((c) =>
    courseMatchesKeyword(c, studentAvailableSearchKeyword.value)
  )
);

const filteredTeacherOtherPublishedCourses = computed(() =>
  teacherOtherPublishedCourses.value.filter((c) =>
    courseMatchesKeyword(c, teacherOtherSearchKeyword.value)
  )
);

const filteredGuestCourses = computed(() =>
  courses.value.filter((c) => courseMatchesKeyword(c, guestSearchKeyword.value))
);

const advicePanelTitle = computed(() => {
  const role = advice.value?.role || me.value?.role;
  if (role === "teacher") return "智能教学建议";
  if (role === "admin") return "智能运营建议";
  return "智能学习建议";
});

const adviceQuickStats = computed(() => (advice.value?.stats || []).slice(0, 3));
const adviceBriefText = computed(() => {
  return advice.value?.focus?.description || advice.value?.summary || "";
});

// [功能说明]: 页面初始化时检查是否有 Token 并加载当前用户信息，判断是学生还是教师。
async function loadMe() {
  const token = sessionStorage.getItem("token");
  if (!token) {
    me.value = null;
    return;
  }
  try {
    // [后端映射]: GET /api/users/me -> 获取当前登录用户信息
    const res = await http.get("/users/me");
    me.value = res.data.data || null;
  } catch {
    me.value = null;
    sessionStorage.removeItem("token");
  }
}

// [功能说明]: 请求后端获取课程列表，供下方卡片渲染
async function loadCourses() {
  // [后端映射]: GET /api/courses -> 获取课程大厅列表
  const res = await http.get("/courses");
  courses.value = res.data.data || [];
}

// [功能说明]: 卡片里的 "查看详情" / "进入课程" 按钮触发，跳转到 CourseDetailView
function openDetail(id) {
  router.push(`/courses/${id}`);
}

// 课程大厅仅展示轻量建议，详细分析仍进入数据总览查看
async function loadAdvice() {
  const token = sessionStorage.getItem("token");
  if (!token) {
    advice.value = null;
    return;
  }
  try {
    const res = await http.get("/users/learning-advice");
    advice.value = res.data?.data || null;
  } catch {
    advice.value = null;
  }
}

function goDashboard() {
  router.push("/dashboard");
}

function openAdviceAction(path) {
  if (!path) return;
  router.push(path);
}

// [功能说明]: 学生点击 "选课" 按钮触发，后端建立绑定关系后刷新列表
async function enroll(courseId) {
  try {
    // [后端映射]: POST /api/courses/<id>/enroll -> 学生选课
    await http.post(`/courses/${courseId}/enroll`);
    await loadCourses();
    await loadAdvice();
  } catch (e) {
    alert(e?.response?.data?.message || "选课失败");
  }
}

// [功能说明]: 学生点击 "退课" 按钮触发，解除选修绑定
async function drop(courseId) {
  try {
    // [后端映射]: DELETE /api/courses/<id>/enroll -> 学生退课
    await http.delete(`/courses/${courseId}/enroll`);
    await loadCourses();
    await loadAdvice();
  } catch (e) {
    alert(e?.response?.data?.message || "退课失败");
  }
}

// [功能说明]: 教师点击 "发布课程" 按钮触发，把草稿状态变为上架
async function publishCourse(courseId) {
  try {
    // [后端映射]: PUT /api/courses/<id>/publish -> 教师发布课程
    await http.put(`/courses/${courseId}/publish`);
    await loadCourses();
    await loadAdvice();
  } catch (e) {
    alert(e?.response?.data?.message || "发布失败");
  }
}

// [功能说明]: 教师点击 "下架课程" 按钮触发，使其变回草稿
async function unpublishCourse(courseId) {
  if (!confirm("确认下架该课程吗？下架后学生将无法选课。")) return;
  try {
    // [后端映射]: PUT /api/courses/<id>/unpublish -> 教师下架课程
    await http.put(`/courses/${courseId}/unpublish`);
    await loadCourses();
    await loadAdvice();
  } catch (e) {
    alert(e?.response?.data?.message || "下架失败");
  }
}

const showInviteModal = ref(false);
const inviteCodes = ref([]);
const inviteLoading = ref(false);
const inviteError = ref("");
const isGenerating = ref(false);

// [功能说明]: 把邀请码过期时间统一格式化，供教师邀请码弹窗列表展示。
function formatInviteTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

// [功能说明]: 教师打开邀请码弹窗后，读取自己当前未使用且未过期的邀请码列表。
async function loadTeacherInviteCodes() {
  inviteLoading.value = true;
  inviteError.value = "";
  try {
    const res = await http.get("/auth/invite-codes");
    inviteCodes.value = res.data.data?.items || [];
  } catch (e) {
    inviteError.value = e?.response?.data?.message || "读取邀请码失败";
  } finally {
    inviteLoading.value = false;
  }
}

// [功能说明]: 打开教师邀请码弹窗，并立即刷新当前可用邀请码。
async function openInviteModal() {
  showInviteModal.value = true;
  await loadTeacherInviteCodes();
}

// [功能说明]: 教师在弹窗内继续生成新的邀请码，生成后刷新列表保留当前可见邀请码。
async function generateInvite() {
  if (isGenerating.value) return;
  isGenerating.value = true;
  inviteError.value = "";
  try {
    await http.post("/auth/generate-invite");
    await loadTeacherInviteCodes();
  } catch (e) {
    inviteError.value = e?.response?.data?.message || "生成邀请码失败";
  } finally {
    isGenerating.value = false;
  }
}

// [功能说明]: 一键复制邀请码，方便教师直接发给待注册教师使用。
async function copyInviteCode(code) {
  try {
    await navigator.clipboard.writeText(code);
    alert("邀请码已复制");
  } catch (e) {
    alert("复制失败，请手动复制");
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
    // [后端映射]: POST /api/courses -> 教师创建课程草稿
    await http.post("/courses", {
      title: newCourseTitle.value.trim(),
      description: newCourseDesc.value.trim(),
    });
    showCreateModal.value = false;
    newCourseTitle.value = "";
    newCourseDesc.value = "";
    await loadCourses();
    await loadAdvice();
  } catch (e) {
    alert(e?.response?.data?.message || "创建失败");
  }
}

// [功能说明]: 学生在“可选课程”区域点击搜索后，仅筛选该分区课程卡片。
function applyStudentAvailableSearch() {
  studentAvailableSearchKeyword.value = studentAvailableSearchInput.value.trim();
}

// [功能说明]: 教师在“其他教师发布的课程”区域点击搜索后，仅筛选该分区课程卡片。
function applyTeacherOtherSearch() {
  teacherOtherSearchKeyword.value = teacherOtherSearchInput.value.trim();
}

// [功能说明]: 游客或未登录用户在课程大厅搜索公开课程。
function applyGuestSearch() {
  guestSearchKeyword.value = guestSearchInput.value.trim();
}

// [功能说明]: 登录态发生变化后，同步刷新当前用户信息和首页课程列表。
const handleAuthChanged = async () => {
  await loadMe();
  await Promise.all([loadCourses(), loadAdvice()]);
};

// [功能说明]: 首页挂载时初始化用户身份和课程大厅数据，并监听登录态变更。
onMounted(async () => {
  await loadMe();
  await Promise.all([loadCourses(), loadAdvice()]);
  window.addEventListener('user-auth-changed', handleAuthChanged);
});

// [功能说明]: 页面卸载时移除登录态监听，避免重复绑定。
onUnmounted(() => {
  window.removeEventListener('user-auth-changed', handleAuthChanged);
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
          <button v-if="me && me.role === 'teacher'" class="btn btn-primary" style="background:#10b981; border-color:#10b981;" @click="openInviteModal">
            生成邀请码
          </button>
          <button v-if="me && me.role === 'teacher'" class="btn btn-primary" @click="showCreateModal = true">
            + 创建新课程
          </button>
        </div>
      </div>
    </section>

    <section v-if="me && advice" class="advice-strip">
      <div class="advice-strip-main">
        <p class="advice-strip-kicker">{{ advicePanelTitle }}</p>
        <h2 class="advice-strip-title">{{ advice.headline }}</h2>
        <p class="advice-strip-summary">{{ adviceBriefText }}</p>
        <div v-if="adviceQuickStats.length" class="advice-strip-stats">
          <span v-for="item in adviceQuickStats" :key="item.label" class="advice-strip-stat">
            {{ item.label }}：{{ item.value }}
          </span>
        </div>
      </div>
      <div class="advice-strip-actions">
        <button
          v-if="advice.focus?.action_path"
          class="btn btn-primary"
          @click="openAdviceAction(advice.focus.action_path)"
        >
          {{ advice.focus.action_label || "立即处理" }}
        </button>
        <button class="btn" @click="goDashboard">查看详细总览</button>
      </div>
    </section>

    <template v-if="me && me.role === 'student'">
      <section class="panel">
        <h2>已选课程（{{ enrolledCourses.length }}）</h2>
        <div class="grid">
          <!-- [视图结构]: 已选课程卡片列表，主要渲染拥有已选状态的课程块 -->
          <article class="card" v-for="c in enrolledCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <small style="display:block; margin-bottom:8px; color:#666">授课教师: {{ c.teacher_name }}</small>
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
        <div class="panel-head">
          <h2>可选课程（{{ filteredAvailableCourses.length }}）</h2>
          <div class="search-bar">
            <input
              v-model.trim="studentAvailableSearchInput"
              class="search-input"
              placeholder="搜索课程名 / 教师名 / 课程简介"
              @keyup.enter="applyStudentAvailableSearch"
            />
            <button class="btn" @click="applyStudentAvailableSearch">搜索</button>
          </div>
        </div>
        <div class="grid">
          <article class="card" v-for="c in filteredAvailableCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <small style="display:block; margin-bottom:8px; color:#666">授课教师: {{ c.teacher_name }}</small>
            <p>{{ c.description || "暂无简介" }}</p>
            <div class="actions">
              <button class="btn" @click="openDetail(c.id)">查看详情</button>
              <button class="btn btn-primary" :disabled="c.status !== 'published'" @click="enroll(c.id)">
                {{ c.status === "published" ? "选课" : "未发布" }}
              </button>
            </div>
          </article>
          <p class="muted" v-if="!filteredAvailableCourses.length">
            {{ studentAvailableSearchKeyword ? "没有匹配的可选课程" : "暂无未选课程" }}
          </p>
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
        <div class="panel-head">
          <h2>其他教师发布的课程（{{ filteredTeacherOtherPublishedCourses.length }}）</h2>
          <div class="search-bar">
            <input
              v-model.trim="teacherOtherSearchInput"
              class="search-input"
              placeholder="搜索课程名 / 教师名 / 课程简介"
              @keyup.enter="applyTeacherOtherSearch"
            />
            <button class="btn" @click="applyTeacherOtherSearch">搜索</button>
          </div>
        </div>
        <div class="grid">
          <article class="card" v-for="c in filteredTeacherOtherPublishedCourses" :key="c.id">
            <h3>{{ c.title }}</h3>
            <small style="display:block; margin-bottom:8px; color:#666">授课教师: {{ c.teacher_name }}</small>
            <p>{{ c.description || "暂无简介" }}</p>
            <div class="actions">
              <button class="btn" @click="openDetail(c.id)">查看详情</button>
            </div>
          </article>
          <p class="muted" v-if="!filteredTeacherOtherPublishedCourses.length">
            {{ teacherOtherSearchKeyword ? "没有匹配的课程" : "暂无其他教师课程" }}
          </p>
        </div>
      </section>
    </template>

    <section v-else class="panel">
      <div class="panel-head">
        <h2>课程列表（{{ filteredGuestCourses.length }}）</h2>
        <div class="search-bar">
          <input
            v-model.trim="guestSearchInput"
            class="search-input"
            placeholder="搜索课程名 / 教师名 / 课程简介"
            @keyup.enter="applyGuestSearch"
          />
          <button class="btn" @click="applyGuestSearch">搜索</button>
        </div>
      </div>
      <div class="grid">
        <article class="card" v-for="c in filteredGuestCourses" :key="c.id">
          <h3>{{ c.title }}</h3>
          <small style="display:block; margin-bottom:8px; color:#666">授课教师: {{ c.teacher_name }}</small>
          <p>{{ c.description || "暂无简介" }}</p>
          <div class="actions">
            <button class="btn" @click="openDetail(c.id)">查看详情</button>
          </div>
        </article>
        <p class="muted" v-if="!filteredGuestCourses.length">
          {{ guestSearchKeyword ? "没有匹配的课程" : "暂无课程" }}
        </p>
      </div>
    </section>

    <!-- [视图结构]: 教师生成邀请码的悬浮表单 -->
    <div v-if="showInviteModal" class="modal-mask">
      <div class="modal-card invite-modal-card">
        <h3>教师邀请码</h3>
        <p class="muted invite-modal-tip">当前只展示未使用且未过期的邀请码。一邀请码只能注册一个教师账号，新生成的邀请码固定 1 天有效。</p>

        <div class="invite-toolbar">
          <button class="btn btn-primary" style="background:#10b981; border-color:#10b981;" @click="generateInvite" :disabled="isGenerating || inviteLoading">
            {{ isGenerating ? "生成中..." : "生成新邀请码" }}
          </button>
          <button class="btn" @click="loadTeacherInviteCodes" :disabled="inviteLoading || isGenerating">刷新列表</button>
        </div>

        <div v-if="inviteError" class="invite-empty">{{ inviteError }}</div>
        <div v-else-if="inviteLoading" class="invite-empty">正在读取邀请码...</div>
        <div v-else-if="!inviteCodes.length" class="invite-empty">当前没有可用邀请码，点击上方按钮即可生成。</div>
        <div v-else class="invite-list">
          <div class="invite-list-head">
            <span>邀请码</span>
            <span>到期时间</span>
            <span>操作</span>
          </div>
          <div v-for="item in inviteCodes" :key="item.id" class="invite-list-row">
            <span class="invite-code">{{ item.code }}</span>
            <span>{{ formatInviteTime(item.expires_at) }}</span>
            <button class="btn" @click="copyInviteCode(item.code)">复制</button>
          </div>
        </div>

        <div class="actions" style="margin-top: 16px; justify-content: flex-end;">
          <button class="btn" @click="showInviteModal = false">关闭</button>
        </div>
      </div>
    </div>
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
.advice-strip {
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 16px;
  padding: 18px 20px;
  background: linear-gradient(135deg, #f8fffc 0%, #ffffff 55%, #f4faff 100%);
  box-shadow: var(--shadow);
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
}
.advice-strip-main {
  min-width: 0;
}
.advice-strip-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #0f766e;
  text-transform: uppercase;
}
.advice-strip-title {
  margin: 0;
  font-size: 24px;
  color: var(--text);
}
.advice-strip-summary {
  margin: 8px 0 0;
  color: #52606d;
  line-height: 1.6;
}
.advice-strip-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.advice-strip-stat {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(37, 99, 235, 0.12);
  color: #334155;
  font-size: 13px;
}
.advice-strip-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.panel-head h2 {
  margin: 0;
}
.grid {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
}
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.search-input {
  min-width: 260px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-family: inherit;
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
.invite-modal-card {
  width: min(760px, calc(100vw - 32px));
}
.invite-modal-tip {
  margin-bottom: 16px;
}
.invite-toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.invite-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 360px;
  overflow-y: auto;
}
.invite-list-head,
.invite-list-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}
.invite-list-head {
  font-size: 13px;
  color: #64748b;
}
.invite-list-row {
  border: 1px solid #dbe3ec;
  border-radius: 10px;
  padding: 10px 12px;
  background: #f8fafc;
}
.invite-code {
  font-weight: 700;
  color: #b91c1c;
  word-break: break-all;
}
.invite-empty {
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 18px;
  color: #64748b;
  background: #f8fafc;
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

@media (max-width: 768px) {
  .advice-strip {
    flex-direction: column;
    align-items: stretch;
  }
  .advice-strip-actions {
    width: 100%;
  }
  .panel-head {
    flex-direction: column;
    align-items: stretch;
  }
  .search-bar {
    width: 100%;
  }
  .search-input {
    min-width: 0;
    flex: 1;
  }
  .invite-list-head,
  .invite-list-row {
    grid-template-columns: 1fr;
  }
}
</style>
