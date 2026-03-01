<script setup>
import { ref, watch } from 'vue'
import http from '../api/http'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  mode: { type: String, default: 'login' }, // login | register
})
const emit = defineEmits(['update:modelValue', 'success', 'switch-mode'])

const username = ref('')
const password = ref('')
const role = ref('student')
const loading = ref(false)
const error = ref('')

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      error.value = ''
      loading.value = false
    }
  }
)

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (props.mode === 'register') {
      await http.post('/auth/register', {
        username: username.value,
        password: password.value,
        role: role.value,
      })
    }
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
</script>

<template>
  <div v-if="modelValue" class="modal-mask" @click.self="close">
    <div class="modal-card">
      <div class="modal-head">
        <h3>{{ mode === 'login' ? '登录' : '注册' }}</h3>
        <button class="ghost" @click="close">✕</button>
      </div>

      <div class="field">
        <label>用户名</label>
        <input v-model="username" placeholder="请输入用户名" />
      </div>

      <div class="field">
        <label>密码</label>
        <input v-model="password" type="password" placeholder="请输入密码" />
      </div>

      <div v-if="mode === 'register'" class="field">
        <label>角色</label>
        <select v-model="role">
          <option value="student">学生</option>
          <option value="teacher">教师</option>
        </select>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="btn btn-primary" style="width: 100%; margin-top: 8px;" :disabled="loading" @click="submit">
        {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册并登录') }}
      </button>

      <p class="switcher">
        <span v-if="mode === 'login'">
          还没有账号？
          <a href="#" @click.prevent="$emit('switch-mode', 'register')">去注册</a>
        </span>
        <span v-else>
          已有账号？
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