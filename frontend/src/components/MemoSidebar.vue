<template>
  <div class="memo-sidebar" :class="{ 'memo-open': isOpen }">
    <!-- Toggle Button -->
    <div class="toggle-btn" @click="toggleSidebar" title="备忘薄">
      备忘薄
    </div>

    <div class="memo-content" v-if="isOpen">
      <div class="memo-header">
        <h3>我的云端笔记</h3>
        <button class="btn btn-sm btn-primary" @click="createNote">新建</button>
      </div>

      <!-- Not logged in state -->
      <div v-if="!isLoggedIn" class="memo-empty">
        <p>登录后即可使用云端同步备忘录功能</p>
      </div>

      <div v-else class="memo-body">
        <!-- Error or Loading -->
        <div v-if="error" class="error-msg">{{ error }}</div>

        <!-- Note List Selector -->
        <div class="note-selector" v-if="notes.length > 0">
          <label>选择文档：</label>
          <div class="flex-row">
            <select v-model="activeNoteId" @change="switchNote" class="select-box">
              <option v-for="n in notes" :key="n.id" :value="n.id">
                {{ n.title }} 
              </option>
            </select>
            <button class="btn btn-sm btn-danger" @click="deleteNote" :disabled="!activeNote">删除</button>
          </div>
        </div>
        
        <!-- Empty list state -->
        <div v-if="notes.length === 0" class="memo-empty">
          <p>暂无笔记档案，点击上方新建</p>
        </div>

        <!-- Active Note Editor -->
        <div class="note-editor" v-if="activeNote">
          <input 
            type="text" 
            class="note-title-input" 
            v-model="editTitle" 
            @blur="saveNote" 
            @keyup.enter="saveNote"
            placeholder="笔记标题" 
          />
          <textarea 
            class="note-textarea" 
            v-model="editContent" 
            @blur="saveNote" 
            placeholder="在这里记录您的听课灵感或备忘录... (失焦自动保存)"
          ></textarea>
          
          <div class="save-status">
            <span v-if="isSaving" class="status-text saving">正在同步云端...</span>
            <span v-else-if="saveSuccess" class="status-text success">已保存至云端</span>
            <span v-else class="status-text muted">最近更新：{{ formatTime(activeNote.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import http from '../api/http'

// 侧边栏与笔记列表基础状态。
const isOpen = ref(false)
const notes = ref([])
const activeNoteId = ref(null)
const error = ref('')
const forceUpdate = ref(1)

// 当前正在编辑的标题、正文以及保存提示状态。
const editTitle = ref('')
const editContent = ref('')
const isSaving = ref(false)
const saveSuccess = ref(false)

const isLoggedIn = computed(() => {
  forceUpdate.value
  return !!sessionStorage.getItem('token')
})

const activeNote = computed(() => {
  return notes.value.find(n => n.id === activeNoteId.value)
})

function toggleSidebar() {
  isOpen.value = !isOpen.value
  if (isOpen.value && isLoggedIn.value && notes.value.length === 0) {
    loadNotes()
  }
}

async function loadNotes() {
  if (!isLoggedIn.value) return
  error.value = ''
  try {
    // [后端映射]: GET /api/notes -> 获取当前用户笔记列表
    const res = await http.get('/notes')
    notes.value = res.data.data || []
    
    // 首次加载后自动选中第一篇笔记，避免右侧编辑区为空。
    if (notes.value.length > 0 && !activeNoteId.value) {
      activeNoteId.value = notes.value[0].id
      syncEditState()
    } else if (notes.value.length === 0) {
        activeNoteId.value = null
        editTitle.value = ''
        editContent.value = ''
    }
  } catch (e) {
    error.value = '无法获取笔记列表'
  }
}

function syncEditState() {
  if (activeNote.value) {
    editTitle.value = activeNote.value.title
    editContent.value = activeNote.value.content || ''
    saveSuccess.value = false
  }
}

function switchNote() {
  syncEditState()
}

async function createNote() {
  if (!isLoggedIn.value) return
  try {
    const title = '新建笔记 ' + (notes.value.length + 1)
    // [后端映射]: POST /api/notes -> 创建新笔记
    const res = await http.post('/notes', { title })
    const newNote = res.data.data
    notes.value.unshift(newNote) // Add to top
    activeNoteId.value = newNote.id
    syncEditState()
  } catch (e) {
    error.value = e?.response?.data?.message || '创建笔记失败'
  }
}

let saveTimeout = null
async function saveNote() {
  if (!activeNote.value || !isLoggedIn.value) return
  
  // 标题和正文都没变时，不重复请求后端。
  if (editTitle.value === activeNote.value.title && editContent.value === activeNote.value.content) {
    return
  }

  isSaving.value = true
  saveSuccess.value = false
  error.value = ''
  
  try {
    // [后端映射]: PUT /api/notes/<id> -> 更新笔记标题与正文
    const res = await http.put(`/notes/${activeNoteId.value}`, {
      title: editTitle.value,
      content: editContent.value
    })
    
    // 直接回写本地状态，避免每次保存都整列表重载。
    activeNote.value.title = res.data.data.title
    activeNote.value.content = res.data.data.content
    activeNote.value.updated_at = res.data.data.updated_at
    
    isSaving.value = false
    saveSuccess.value = true
    
    // 保存成功提示 3 秒后自动消失。
    clearTimeout(saveTimeout)
    saveTimeout = setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
    
  } catch (e) {
    isSaving.value = false
    const msg = e?.response?.data?.message || '保存云端失败，请检查网络'
    error.value = msg
    alert(msg)
  }
}

async function deleteNote() {
  if (!activeNote.value || !confirm('确定要永久删除这篇笔记吗？')) return
  
  try {
    // [后端映射]: DELETE /api/notes/<id> -> 删除指定笔记
    await http.delete(`/notes/${activeNoteId.value}`)
    notes.value = notes.value.filter(n => n.id !== activeNoteId.value)
    
    if (notes.value.length > 0) {
      activeNoteId.value = notes.value[0].id
      syncEditState()
    } else {
      activeNoteId.value = null
    }
  } catch (e) {
    alert('删除失败')
  }
}

function formatTime(iso) {
    if(!iso) return ''
    const d = new Date(iso)
    return `${d.getMonth()+1}-${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`
}

const handleAuthChanged = () => {
  forceUpdate.value++
  if (isLoggedIn.value) {
    loadNotes()
  } else {
    notes.value = []
    activeNoteId.value = null
    editTitle.value = ''
    editContent.value = ''
    isOpen.value = false
  }
}

// 监听登录态变化，登录后自动拉取笔记，退出后清空本地状态。
onMounted(() => {
  if (isLoggedIn.value) {
    loadNotes()
  }
  window.addEventListener('user-auth-changed', handleAuthChanged)
})

onUnmounted(() => {
  window.removeEventListener('user-auth-changed', handleAuthChanged)
  clearTimeout(saveTimeout)
})
</script>

<style scoped>
.memo-sidebar {
  position: fixed;
  top: 68px; /* 紧贴顶部导航栏的黑线下方 */
  right: -340px; /* 默认隐藏 */
  width: 340px; /* 加宽一点点看起来更大气 */
  height: calc(100vh - 68px);
  background: #ffffff;
  border-left: 1px solid #e1e4e8;
  box-shadow: -6px 0 20px rgba(0,0,0,0.06);
  transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 110;
  display: flex;
  flex-direction: column;
}

.memo-sidebar.memo-open {
  right: 0;
  z-index: 130;
}

.toggle-btn {
  position: absolute;
  top: 24px;
  left: -42px;
  width: 42px;
  height: 100px;
  background: #2563eb;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  cursor: pointer;
  border-radius: 12px 0 0 12px;
  font-weight: bold;
  font-size: 15px;
  letter-spacing: 4px;
  box-shadow: -4px 4px 10px rgba(37,99,235,0.2);
  user-select: none;
  z-index: 120;
}

.toggle-btn:hover {
  background: #1d4ed8;
}

.memo-sidebar.memo-open .toggle-btn {
  z-index: 140;
}

.memo-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.memo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #f1f5f9;
  padding-bottom: 16px;
  margin-bottom: 20px;
}
.memo-header h3 {
  margin: 0;
  font-size: 18px;
  color: #1e293b;
  font-weight: 700;
}

.memo-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.flex-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.note-selector {
  margin-bottom: 20px;
}
.note-selector label {
  display: block;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
  font-weight: 500;
}
.select-box {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  outline: none;
  font-size: 14px;
  background: #f8fafc;
  color: #334155;
  transition: all 0.2s;
}
.select-box:focus {
  border-color: #3b82f6;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.note-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.note-title-input {
  width: 100%;
  padding: 8px 0;
  border: 1px solid transparent;
  border-bottom: 2px dashed #cbd5e1;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
  outline: none;
  background: transparent;
  transition: border 0.3s ease;
}
.note-title-input:focus {
  border-bottom: 2px solid #2563eb;
}

.note-textarea {
  flex: 1;
  width: 100%;
  resize: none;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  outline: none;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #334155;
  background: #f8fafc;
  transition: all 0.2s;
}
.note-textarea:focus {
  border-color: #cbd5e1;
  background: #ffffff;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}

.save-status {
  text-align: right;
  font-size: 13px;
}
.muted { color: #94a3b8; }
.saving { color: #d97706; font-weight: 500;}
.success { color: #059669; font-weight: 500;}

.error-msg { color: #dc2626; font-size: 13px; margin-bottom: 12px; }
.memo-empty {
  text-align: center;
  color: #94a3b8;
  margin-top: 60px;
  font-size: 15px;
}

.btn { cursor: pointer; border-radius: 8px; border: 1px solid transparent; font-weight: 600; transition: all 0.2s; }
.btn-sm { padding: 6px 14px; font-size: 13px; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-primary:hover { background: #1d4ed8; box-shadow: 0 4px 6px rgba(37,99,235,0.2); }
.btn-danger { background: #fee2e2; color: #dc2626; border-color: #fecaca; }
.btn-danger:hover { background: #fecaca; color: #b91c1c; }
@media (max-width: 768px) {
  .toggle-btn {
    top: 128px;
    height: 88px;
  }
}
</style>
