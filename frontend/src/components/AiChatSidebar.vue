<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const isOpen = ref(false)

const forceUpdate = ref(1)
const isLoggedIn = computed(() => {
  forceUpdate.value
  return !!sessionStorage.getItem('token')
})

// 聊天记录 [{ role: 'user' | 'ai', text: '...', loading: false }]
const messages = ref([
  { role: 'ai', text: '你好！我是你的 AI 学习助教。有什么学习上的问题想探讨吗？' }
])

const inputStr = ref('')
const isLoading = ref(false)
const chatBodyRef = ref(null)

// 增加可选模型的逻辑
const selectedModel = ref('Qwen/Qwen2.5-7B-Instruct')
const availableModels = [
  { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen 2.5 (7B基础版)' },
  { id: 'Qwen/Qwen3-8B', name: 'Qwen 3 (8B新版)' }
]

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

// 监听打开时滚动底部
watch(isOpen, (val) => {
  if (val) {
    scrollToBottom()
  }
})

const handleAuthChanged = () => {
  forceUpdate.value++
  if (!isLoggedIn.value) {
    messages.value = [
      { role: 'ai', text: '你好！我是你的 AI 学习助教。有什么学习上的问题想探讨吗？' }
    ]
    isOpen.value = false
  }
}

async function sendMessage() {
  const text = inputStr.value.trim()
  if (!text || isLoading.value) return

  // 用户发言加入消息列表
  messages.value.push({ role: 'user', text })
  inputStr.value = ''
  
  // AI占位符加入消息列表，准备显示打字机效果
  const replyIndex = messages.value.push({ role: 'ai', text: '', loading: true }) - 1
  isLoading.value = true
  scrollToBottom()

  try {
    const token = sessionStorage.getItem('token')
    
    // 使用相对路径以支持Nginx反向代理和Server-Sent Events
    // [后端映射]: POST /api/ai/chat -> 发起 AI 聊天并接收流式回复
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ 
        message: text,
        model: selectedModel.value 
      })
    })

    if (!res.ok) {
      let msg = `请求失败(${res.status})`
      try {
        const data = await res.json()
        msg = data?.message || data?.msg || msg
      } catch (_) {}
      if (res.status === 401 && (!msg || msg.startsWith('请求失败'))) {
        msg = '请先登录或重新登录后再使用 AI 助教'
      }
      throw new Error(msg)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let done = false

    messages.value[replyIndex].loading = false

    while (!done) {
      const { value, done: doneReading } = await reader.read()
      done = doneReading
      if (value) {
        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')
        
        for (let line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6)
            if (dataStr === '[DONE]') {
              done = true
              break
            }
            try {
              const dataObj = JSON.parse(dataStr)
              if(dataObj.error) {
                 messages.value[replyIndex].text += `\n[系统错误：${dataObj.error}]`
              } else if (dataObj.content) {
                 // 打字机效果将字符推入
                 messages.value[replyIndex].text += dataObj.content
                 scrollToBottom()
              }
            } catch(e) {
              console.error("JSON解析流失败", e, dataStr)
            }
          }
        }
      }
    }
  } catch (err) {
    console.error('AI Reply Error:', err)
    messages.value[replyIndex].loading = false
    messages.value[replyIndex].text = err?.message || '网络连接异常或服务未启动，请重试。'
  } finally {
    isLoading.value = false
    messages.value[replyIndex].loading = false
  }
}

// 登录态变化后同步刷新助教面板状态，退出登录时重置会话内容。
onMounted(() => {
  window.addEventListener('user-auth-changed', handleAuthChanged)
})

onUnmounted(() => {
  window.removeEventListener('user-auth-changed', handleAuthChanged)
})
</script>

<template>
  <div class="ai-drawer" :class="{ 'is-open': isOpen }">
    <div class="toggle-btn" @click="isOpen = !isOpen" title="AI助教">
      AI 助教
    </div>
    <div class="ai-header">
      <div>
        <h4>智能学习助教</h4>
        <select v-if="isLoggedIn" v-model="selectedModel" class="model-selector">
          <option v-for="m in availableModels" :key="m.id" :value="m.id">
            {{ m.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- 未登录状态 -->
    <div v-if="!isLoggedIn" class="ai-empty">
      <p>登录后即可使用 AI 智能学习助教功能</p>
    </div>

    <!-- 已登录状态 -->
    <template v-else>
      <!-- 聊天内容区 -->
      <div class="ai-body" ref="chatBodyRef">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="msg-row"
          :class="msg.role === 'user' ? 'row-right' : 'row-left'"
        >
          <div class="msg-bubble" :class="msg.role">
            <span v-if="msg.loading" class="dot-typing">思考中...</span>
            <span v-else style="white-space: pre-wrap;">{{ msg.text }}</span>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="ai-footer">
        <textarea
          v-model="inputStr"
          class="ai-input"
          placeholder="向AI提问，例如：‘解释一下微积分’...按回车发送"
          @keydown.enter.prevent="sendMessage"
        ></textarea>
        <button class="send-btn" :disabled="isLoading || !inputStr.trim()" @click="sendMessage">
          发送
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ai-drawer {
  position: fixed;
  top: 68px; /* 紧贴顶部 */
  left: -350px; /* 默认隐藏 */
  width: 350px;
  height: calc(100vh - 68px);
  background-color: #ffffff;
  border-right: 1px solid #e1e4e8;
  box-shadow: 6px 0 20px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  z-index: 110;
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.ai-drawer.is-open {
  left: 0;
  z-index: 130;
}

.toggle-btn {
  position: absolute;
  top: 24px;
  right: -42px;
  width: 42px;
  height: 100px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  cursor: pointer;
  border-radius: 0 12px 12px 0;
  font-weight: bold;
  font-size: 15px;
  letter-spacing: 4px;
  box-shadow: 4px 4px 10px rgba(16,185,129,0.2);
  user-select: none;
  z-index: 120;
}

.toggle-btn:hover {
  background: #059669;
}

.ai-drawer.is-open .toggle-btn {
  z-index: 140;
}

.ai-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f8fafc;
}

.ai-header h4 {
  margin: 0;
  color: #1e293b;
  font-size: 16px;
  margin-bottom: 4px;
}

.ai-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;
  color: #94a3b8;
  font-size: 15px;
  background: #f1f5f9;
}

.model-selector {
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #475569;
  outline: none;
}
.ai-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #f1f5f9;
}

.msg-row {
  display: flex;
  width: 100%;
}

.row-left {
  justify-content: flex-start;
}

.row-right {
  justify-content: flex-end;
}

.msg-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
}

.msg-bubble.ai {
  background-color: #ffffff;
  color: #334155;
  border-top-left-radius: 2px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.msg-bubble.user {
  background-color: #3b82f6;
  color: #ffffff;
  border-top-right-radius: 2px;
}

.ai-footer {
  padding: 12px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-input {
  width: 100%;
  height: 60px;
  resize: none;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  font-family: inherit;
}

.ai-input:focus {
  border-color: #3b82f6;
}

.send-btn {
  align-self: flex-end;
  padding: 6px 16px;
  background-color: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.send-btn:hover {
  background-color: #2563eb;
}

.send-btn:disabled {
  background-color: #94a3b8;
  cursor: not-allowed;
}

.dot-typing {
  animation: blink 1.4s infinite both;
  color: #94a3b8;
}

@keyframes blink {
  0% { opacity: .2; }
  20% { opacity: 1; }
  100% { opacity: .2; }
}

@media (max-width: 768px) {
  .toggle-btn {
    top: 24px;
    height: 88px;
  }
}
</style>
