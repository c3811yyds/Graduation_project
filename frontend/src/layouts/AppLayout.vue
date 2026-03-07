<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import AuthModal from '../components/AuthModal.vue'
import MemoSidebar from '../components/MemoSidebar.vue'
import AiChatSidebar from '../components/AiChatSidebar.vue'

const router = useRouter()
const me = ref(null)
const version = ref('')
const authVisible = ref(false)
const authMode = ref('login')

// 返回课程大厅首页。
function goHome() {
  router.push('/')
}

// 进入个人中心页。
function goProfile() {
  router.push('/profile')
}

// 打开数据总览页。
function goDashboard() {
  router.push('/dashboard')
}

// 进入管理员后台。
function goAdmin() {
  router.push('/admin')
}

// 打开登录弹窗并默认切到登录模式。
function openLogin() {
  authMode.value = 'login'
  authVisible.value = true
}

// 读取当前部署版本号，显示在顶部导航。
async function loadVersion() {
  try {
    const res = await http.get('/version')
    version.value = res.data?.data?.version || ''
  } catch {
    version.value = ''
  }
}

// 根据本地 token 拉取当前登录用户信息。
async function loadMe() {
  const token = sessionStorage.getItem('token')
  if (!token) {
    me.value = null
    return
  }

  try {
    const res = await http.get('/users/me')
    me.value = res.data.data || null
  } catch {
    me.value = null
    sessionStorage.removeItem('token')
  }
}

// 登录或注册成功后刷新用户态，并通知其他悬浮组件同步状态。
async function onAuthSuccess() {
  await loadMe()
  window.dispatchEvent(new Event('user-auth-changed'))
  router.push('/').then(() => {
    window.location.reload()
  })
}

// 退出登录并清理本地登录态。
function logout() {
  sessionStorage.removeItem('token')
  me.value = null
  window.dispatchEvent(new Event('user-auth-changed'))
  router.push('/')
}

// 页面首次加载时同步版本号和登录用户信息。
onMounted(() => {
  loadVersion()
  loadMe().then(() => {
    if (me.value) {
      window.dispatchEvent(new Event('user-auth-changed'))
    }
  })
})
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <div class="brand-wrap">
        <div class="brand" @click="goHome">智能学习网站</div>
        <span v-if="version" class="version-chip">{{ version }}</span>
      </div>

      <div class="right">
        <template v-if="me">
          <span class="user">{{ me.username }} ({{ me.role }})</span>
          <button class="btn" @click="goProfile">个人中心</button>
          <button class="btn" @click="goDashboard">数据总览</button>
          <button v-if="me.role === 'admin'" class="btn" @click="goAdmin">管理员后台</button>
          <button class="btn" @click="logout">退出登录</button>
        </template>
        <template v-else>
          <button class="btn btn-primary" @click="openLogin">登录 / 注册</button>
        </template>
      </div>
    </header>

    <main class="main">
      <slot />
    </main>

    <MemoSidebar />
    <AiChatSidebar />

    <AuthModal
      v-if="authVisible"
      v-model="authVisible"
      :mode="authMode"
      @switch-mode="authMode = $event"
      @success="onAuthSuccess"
    />
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}

.topbar {
  height: 66px;
  border-bottom: 2px solid var(--text);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.brand-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand {
  font-weight: 800;
  font-size: 18px;
  cursor: pointer;
  color: var(--text);
}

.version-chip {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 12px;
  font-weight: 700;
}

.right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.main {
  padding: 24px;
  max-width: 100%;
}

.btn {
  border: 1px solid #d0d7de;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}

.btn:hover {
  background: #f6f8fa;
}

.btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.btn-primary:hover {
  background: #1d4ed8;
}

@media (max-width: 720px) {
  .topbar {
    height: auto;
    padding: 14px 16px;
    align-items: flex-start;
    gap: 12px;
    flex-direction: column;
  }

  .brand-wrap,
  .right {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
