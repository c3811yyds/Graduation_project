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

function goHome() {
  router.push('/')
}

function goProfile() {
  router.push('/profile')
}

function goDashboard() {
  router.push('/dashboard')
}

function goAdmin() {
  router.push('/admin')
}

function openLogin() {
  authMode.value = 'login'
  authVisible.value = true
}

async function loadVersion() {
  try {
    const res = await http.get('/version')
    version.value = res.data?.data?.version || ''
  } catch {
    version.value = ''
  }
}

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

async function onAuthSuccess() {
  await loadMe()
  window.dispatchEvent(new Event('user-auth-changed'))
  router.push('/').then(() => {
    window.location.reload()
  })
}

function logout() {
  sessionStorage.removeItem('token')
  me.value = null
  window.dispatchEvent(new Event('user-auth-changed'))
  router.push('/')
}

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
