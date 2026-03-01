<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import AuthModal from '../components/AuthModal.vue'
import MemoSidebar from '../components/MemoSidebar.vue'
import AiChatSidebar from '../components/AiChatSidebar.vue'

const router = useRouter()
const me = ref(null)
const authVisible = ref(false)
const authMode = ref('login')

function goHome() {
  router.push('/')
}

function openLogin() {
  authMode.value = 'login'
  authVisible.value = true
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

function goDashboard() {
  router.push('/dashboard')
}

function logout() {
  sessionStorage.removeItem('token')
  me.value = null
  window.dispatchEvent(new Event('user-auth-changed'))
  router.push('/')
}

onMounted(() => {
  loadMe().then(() => {
    if(me.value) {
       window.dispatchEvent(new Event('user-auth-changed'))
    }
  })
})
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <div class="brand" @click="goHome">智能学习网站</div>

      <div class="right">
        <template v-if="me">
          <span class="user">{{ me.username }}（{{ me.role }}）</span>
          <button class="btn" @click="goDashboard">📊 数据总览</button>
          <button class="btn" @click="logout" style="margin-left:8px;">退出登录</button>
        </template>
        <template v-else>
          <button class="btn btn-primary" @click="openLogin">登录 / 注册</button>
        </template>
      </div>
    </header>

    <main class="main">
      <slot />
    </main>
    
    <!-- 全局挂载右侧抽屉云笔记系统 -->
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
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand {
  font-weight: 800;
  font-size: 18px;
  cursor: pointer;
  color: var(--text);
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
  /* 留出边缘不被覆盖 */
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
</style>