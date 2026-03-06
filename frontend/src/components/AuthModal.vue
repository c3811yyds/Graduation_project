<script setup>
import { onUnmounted, ref, watch } from 'vue'
import http from '../api/http'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  mode: { type: String, default: 'login' }, // login | register | forgot
})
const emit = defineEmits(['update:modelValue', 'success', 'switch-mode'])

const username = ref('')
const email = ref('')
const password = ref('')
const role = ref('student')
const verifyCode = ref('')
const inviteCode = ref('')
const loading = ref(false)
const error = ref('')
const cooldown = ref(0)
let timer = null

// 弹窗每次重新打开时，重置输入状态和验证码倒计时。
watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      error.value = ''
      loading.value = false
      username.value = ''
      email.value = ''
      password.value = ''
      verifyCode.value = ''
      inviteCode.value = ''
      cooldown.value = 0
      if (timer) clearInterval(timer)
    }
  }
)

// 登录 / 注册 / 找回密码互相切换时，清掉上一个模式遗留的临时输入。
watch(
  () => props.mode,
  () => {
    error.value = ''
    loading.value = false
    verifyCode.value = ''
    inviteCode.value = ''
    cooldown.value = 0
    if (timer) clearInterval(timer)
  }
)

async function sendCode() {
  if (!email.value || !email.value.includes('@')) {
    error.value = '请输入有效的邮箱地址'
    return
  }
  error.value = ''
  try {
    // [后端映射]: register -> POST /api/auth/send-code；forgot -> POST /api/auth/send-reset-code
    const endpoint = props.mode === 'forgot' ? '/auth/send-reset-code' : '/auth/send-code'
    await http.post(endpoint, { email: email.value })
    cooldown.value = 60
    timer = setInterval(() => {
      cooldown.value--
      if (cooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) {
    error.value = e?.response?.data?.message || '发送失败'
  }
}

function close() {
  emit('update:modelValue', false)
  if (timer) clearInterval(timer)
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (props.mode === 'forgot') {
      // [后端映射]: POST /api/auth/reset-password -> 忘记密码重置
      await http.post('/auth/reset-password', {
        email: email.value,
        verify_code: verifyCode.value,
        new_password: password.value,
      })
      alert('密码重置成功，请使用新密码登录')
      username.value = email.value
      password.value = ''
      verifyCode.value = ''
      emit('switch-mode', 'login')
      return
    }
    if (props.mode === 'register') {
      // [后端映射]: POST /api/auth/register -> 新用户注册
      await http.post('/auth/register', {
        username: username.value,
        email: email.value,
        password: password.value,
        role: role.value,
        verify_code: verifyCode.value,
        invite_code: inviteCode.value,
      })
    }
    // [后端映射]: POST /api/auth/login -> 登录并获取 JWT
    const res = await http.post('/auth/login', {
      username: username.value,
      password: password.value,
    })
    const token = res.data.data.token
    sessionStorage.setItem('token', token)
    emit('success', res.data.data.user)
    close()
  } catch (e) {
    error.value = e?.response?.data?.message || e.message || '请求失败'
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div v-if="modelValue" class="modal-mask">
    <div class="modal-card">
      <div class="modal-head">
        <h3>{{ mode === 'login' ? '登录' : (mode === 'register' ? '注册' : '忘记密码') }}</h3>
        <button class="ghost" @click="close">✕</button>
      </div>

      <div v-if="mode !== 'forgot'" class="field">
        <label v-if="mode === 'login'">用户名 / 邮箱</label>
        <label v-else>用户名</label>
        <input v-model="username" :placeholder="mode === 'login' ? '请输入用户名或邮箱' : '请输入用户名'" />
      </div>

      <div v-if="mode === 'register' || mode === 'forgot'" class="field">
        <label>邮箱</label>
        <input v-model="email" type="email" placeholder="请输入唯一邮箱地址" />
      </div>

      <div class="field">
        <label>{{ mode === 'forgot' ? '新密码' : '密码' }}</label>
        <input v-model="password" type="password" :placeholder="mode === 'forgot' ? '请输入新密码（至少6位）' : '请输入密码'" />
      </div>

      <div v-if="mode === 'register'" class="field">
        <label>角色</label>
        <select v-model="role">
          <option value="student">学生</option>
          <option value="teacher">教师</option>
        </select>
      </div>

      <div v-if="mode === 'register' || mode === 'forgot'" class="field">
        <label>验证码</label>
        <div style="display: flex; gap: 8px;">
          <input v-model="verifyCode" placeholder="请输入验证码" style="flex: 1" />
          <button class="btn" @click="sendCode" :disabled="cooldown > 0">
            {{ cooldown > 0 ? `${cooldown}秒` : '发送验证码' }}
          </button>
        </div>
        <span class="hint" style="margin-top: 6px; display: block; font-size: 12px; color: #94a3b8;">验证码 2 分钟有效，60 秒后可重新发送</span>
      </div>

      <div v-if="mode === 'register' && role === 'teacher'" class="field">
        <label>教师专属邀请码</label>
        <input v-model="inviteCode" placeholder="请输入系统发放的教师邀请码" />
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="btn btn-primary" style="width: 100%; margin-top: 8px;" :disabled="loading" @click="submit">
        {{ loading ? '处理中...' : (mode === 'login' ? '登录' : (mode === 'register' ? '注册并登录' : '重置密码')) }}
      </button>

      <p class="switcher">
        <span v-if="mode === 'login'">
          还没有账号？
          <a href="#" @click.prevent="$emit('switch-mode', 'register')">去注册</a>
          <span style="margin: 0 8px; color: #94a3b8;">|</span>
          <a href="#" @click.prevent="$emit('switch-mode', 'forgot')">忘记密码？</a>
        </span>
        <span v-else-if="mode === 'register'">
          已有账号？
          <a href="#" @click.prevent="$emit('switch-mode', 'login')">去登录</a>
        </span>
        <span v-else>
          想起密码了？
          <a href="#" @click.prevent="$emit('switch-mode', 'login')">去登录</a>
        </span>
      </p>
    </div>
  </div>
</template>

<style scoped>
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
  width: 360px;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 12px 0;
}
.field input,
.field select {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
}
.error {
  color: #b91c1c;
  min-height: 20px;
  font-size: 13px;
}
.switcher {
  margin-top: 8px;
  text-align: center;
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
</style>
