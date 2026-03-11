<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http'

const route = useRoute()

const isOpen = ref(false)
const forceUpdate = ref(1)
const inputStr = ref('')
const isLoading = ref(false)
const chatBodyRef = ref(null)
const analysisContext = ref(null)
const contextLoading = ref(false)

const isLoggedIn = computed(() => {
  forceUpdate.value
  return !!sessionStorage.getItem('token')
})

const routeCourseId = computed(() => {
  if (route.name !== 'course-detail') return null
  const id = Number(route.params.id)
  return Number.isFinite(id) ? id : null
})

const requestScope = computed(() => (routeCourseId.value ? 'course-detail' : 'global'))

const messages = ref([
  {
    role: 'ai',
    text: '你好，我是平台里的 AI 助手。你可以直接提问，也可以让我结合当前页面和站内数据生成更具体的分析建议。'
  }
])

const selectedModel = ref('Qwen/Qwen2.5-7B-Instruct')
const availableModels = [
  { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen 2.5（7B）' },
  { id: 'Qwen/Qwen3-8B', name: 'Qwen 3（8B）' }
]

const currentRole = computed(() => analysisContext.value?.role || 'student')
const pageContext = computed(() => analysisContext.value?.page_context || null)

const analysisButtonText = computed(() => {
  if (requestScope.value === 'course-detail' && pageContext.value?.course_title) {
    if (currentRole.value === 'teacher') return '生成当前课程教学分析'
    if (currentRole.value === 'admin') return '生成当前课程运营分析'
    return '生成当前课程学习分析'
  }

  if (currentRole.value === 'teacher') return '生成大厅总览教学分析'
  if (currentRole.value === 'admin') return '生成大厅总览运营分析'
  return '生成大厅总览学习分析'
})

const analysisTip = computed(() => {
  if (pageContext.value?.scope === 'course-detail' && pageContext.value?.course_title) {
    if (currentRole.value === 'teacher') {
      return `当前将围绕《${pageContext.value.course_title}》的学生平均进展、选课人数和教学优先级生成分析建议。`
    }
    if (currentRole.value === 'admin') {
      return `当前将围绕《${pageContext.value.course_title}》的课程建设、选课表现和运营风险生成分析建议。`
    }
    return `当前将围绕《${pageContext.value.course_title}》的学习进度、下一课件和优先任务生成分析建议。`
  }

  if (currentRole.value === 'teacher') {
    return '当前将综合你全部课程的学生学习进展、草稿课程和低活跃课程，生成大厅总览教学分析。'
  }
  if (currentRole.value === 'admin') {
    return '当前将综合平台课程建设、空课程和零选课课程等数据，生成大厅总览运营分析。'
  }
  return '当前将综合你的全部选课、学习进度和停滞课程数据，生成大厅总览学习分析。'
})

const quickAnalysisPrompt = computed(() => {
  if (pageContext.value?.scope === 'course-detail' && pageContext.value?.course_title) {
    if (currentRole.value === 'teacher') {
      return `请结合当前课程《${pageContext.value.course_title}》的学生学习进展数据，分析这门课现在最值得优先关注的教学问题，并给出可执行建议。`
    }
    if (currentRole.value === 'admin') {
      return `请结合当前课程《${pageContext.value.course_title}》的课程建设和选课数据，分析这门课当前最值得优先处理的运营问题，并给出建议。`
    }
    return `请结合当前课程《${pageContext.value.course_title}》的学习数据，分析我在这门课里现在最值得优先处理的学习任务，并给出下一步建议。`
  }

  if (currentRole.value === 'teacher') {
    return '请结合我当前全部课程和学生学习进展数据，分析目前最值得优先关注的教学问题，并给出可执行建议。'
  }
  if (currentRole.value === 'admin') {
    return '请结合当前平台运营数据，分析最值得优先处理的问题，并给出明确可执行的运营建议。'
  }
  return '请结合我当前的学习数据，分析我现在最值得优先处理的学习任务，并给出具体下一步建议。'
})

const analysisDisplayText = computed(() => {
  if (pageContext.value?.scope === 'course-detail' && pageContext.value?.course_title) {
    return `${analysisButtonText.value}：${pageContext.value.course_title}`
  }
  return analysisButtonText.value
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

watch(isOpen, (val) => {
  if (val) scrollToBottom()
})

watch(
  () => route.fullPath,
  () => {
    if (isLoggedIn.value) {
      loadAnalysisContext(true)
    }
  }
)

const handleAuthChanged = () => {
  forceUpdate.value++
  if (!isLoggedIn.value) {
    messages.value = [
      {
        role: 'ai',
        text: '你好，我是平台里的 AI 助手。你可以直接提问，也可以让我结合当前页面和站内数据生成更具体的分析建议。'
      }
    ]
    analysisContext.value = null
    isOpen.value = false
    return
  }

  loadAnalysisContext(true)
}

function buildContextUrl() {
  if (requestScope.value === 'course-detail' && routeCourseId.value) {
    return `/users/learning-advice-context?scope=course-detail&course_id=${routeCourseId.value}`
  }
  return '/users/learning-advice-context?scope=global'
}

async function loadAnalysisContext(force = false) {
  if (!isLoggedIn.value) return null
  if (analysisContext.value && !force) return analysisContext.value

  contextLoading.value = true
  try {
    const res = await http.get(buildContextUrl())
    analysisContext.value = res.data?.data || null
    return analysisContext.value
  } catch {
    return null
  } finally {
    contextLoading.value = false
  }
}

async function streamChatMessage(payload, userDisplayText = payload.message) {
  if (isLoading.value) return

  messages.value.push({ role: 'user', text: userDisplayText })
  const replyIndex = messages.value.push({ role: 'ai', text: '', loading: true }) - 1
  isLoading.value = true
  scrollToBottom()

  try {
    const token = sessionStorage.getItem('token')
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        model: selectedModel.value,
        ...payload
      })
    })

    if (!res.ok) {
      let msg = `请求失败（${res.status}）`
      try {
        const data = await res.json()
        msg = data?.message || data?.msg || msg
      } catch (_) {}
      if (res.status === 401 && (!msg || msg.startsWith('请求失败'))) {
        msg = '登录状态已失效，请重新登录后再使用 AI 助手。'
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
      if (!value) continue

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const dataStr = line.substring(6)
        if (dataStr === '[DONE]') {
          done = true
          break
        }
        try {
          const dataObj = JSON.parse(dataStr)
          if (dataObj.error) {
            messages.value[replyIndex].text += `\n[分析异常：${dataObj.error}]`
          } else if (dataObj.content) {
            messages.value[replyIndex].text += dataObj.content
            scrollToBottom()
          }
        } catch (error) {
          console.error('解析 AI 返回内容失败', error, dataStr)
        }
      }
    }
  } catch (error) {
    console.error('AI Reply Error:', error)
    messages.value[replyIndex].loading = false
    messages.value[replyIndex].text = error?.message || '当前无法完成分析，请稍后重试。'
  } finally {
    isLoading.value = false
    messages.value[replyIndex].loading = false
  }
}

async function sendMessage() {
  const text = inputStr.value.trim()
  if (!text || isLoading.value) return
  inputStr.value = ''
  await streamChatMessage({ message: text }, text)
}

async function runContextAnalysis() {
  if (contextLoading.value || isLoading.value) return
  const context = await loadAnalysisContext(true)
  if (!context) {
    messages.value.push({
      role: 'ai',
      text: '当前无法读取分析上下文，请稍后重试。'
    })
    scrollToBottom()
    return
  }

  await streamChatMessage(
    {
      message: quickAnalysisPrompt.value,
      analysis_context: context,
      analysis_scene: requestScope.value === 'course-detail' ? 'course_detail_sidebar' : 'hall_sidebar'
    },
    analysisDisplayText.value
  )
}

onMounted(() => {
  window.addEventListener('user-auth-changed', handleAuthChanged)
  if (isLoggedIn.value) {
    loadAnalysisContext(true)
  }
})

onUnmounted(() => {
  window.removeEventListener('user-auth-changed', handleAuthChanged)
})
</script>

<template>
  <div class="ai-drawer" :class="{ 'is-open': isOpen }">
    <div class="toggle-btn" @click="isOpen = !isOpen" title="AI 助手">
      AI 助手
    </div>

    <div class="ai-header">
      <div>
        <h4>智能 AI 助手</h4>
        <select v-if="isLoggedIn" v-model="selectedModel" class="model-selector">
          <option v-for="m in availableModels" :key="m.id" :value="m.id">
            {{ m.name }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="isLoggedIn" class="smart-tools">
      <button class="smart-tool-btn" :disabled="contextLoading || isLoading" @click="runContextAnalysis">
        {{ contextLoading ? '分析中...' : analysisButtonText }}
      </button>
      <p class="smart-tool-tip">{{ analysisTip }}</p>
    </div>

    <div v-if="!isLoggedIn" class="ai-empty">
      <p>登录后即可使用 AI 助手，并结合当前页面和站内学习数据生成建议。</p>
    </div>

    <template v-else>
      <div class="ai-body" ref="chatBodyRef">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="msg-row"
          :class="msg.role === 'user' ? 'row-right' : 'row-left'"
        >
          <div class="msg-bubble" :class="msg.role">
            <span v-if="msg.loading" class="dot-typing">正在生成...</span>
            <span v-else style="white-space: pre-wrap;">{{ msg.text }}</span>
          </div>
        </div>
      </div>

      <div class="ai-footer">
        <textarea
          v-model="inputStr"
          class="ai-input"
          placeholder="你可以直接提问，也可以点击上方按钮生成结合当前页面的 AI 分析。"
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
  top: 68px;
  left: -350px;
  width: 350px;
  height: calc(100vh - 68px);
  background-color: #ffffff;
  border-right: 1px solid #e1e4e8;
  box-shadow: 6px 0 20px rgba(0, 0, 0, 0.06);
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
  box-shadow: 4px 4px 10px rgba(16, 185, 129, 0.2);
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
  margin: 0 0 4px;
  color: #1e293b;
  font-size: 16px;
}

.smart-tools {
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.smart-tool-btn {
  width: 100%;
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #0f766e 0%, #0ea5e9 100%);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  font-size: 14px;
}

.smart-tool-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.smart-tool-tip {
  margin: 8px 0 0;
  color: #52606d;
  font-size: 12px;
  line-height: 1.5;
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
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
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
  0% {
    opacity: 0.2;
  }
  20% {
    opacity: 1;
  }
  100% {
    opacity: 0.2;
  }
}

@media (max-width: 768px) {
  .toggle-btn {
    top: 24px;
    height: 88px;
  }
}
</style>
