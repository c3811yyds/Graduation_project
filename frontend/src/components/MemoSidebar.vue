<template>
  <div class="memo-sidebar" :class="{ 'memo-open': isOpen }">
    <!-- Toggle Button -->
    <div class="toggle-btn" @click="toggleSidebar" title="备忘录">
      📝 设置 / 笔记本
    </div>

    <div class="memo-content" v-if="isOpen">
      <div class="memo-header">
        <h3>我的云端笔记</h3>
        <button class="btn btn-sm btn-primary" @click="createNote">➕ 新建</button>
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
            <button class="btn btn-sm btn-danger" title="删除" @click="deleteNote" :disabled="!activeNote">🗑️</button>
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
            <span v-else-if="saveSuccess" class="status-text success">已保存至云端 ✓</span>
            <span v-else class="status-text muted">最近更新：{{ formatTime(activeNote.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import http from '../api/http'

// State
const isOpen = ref(false)
const notes = ref([])
const activeNoteId = ref(null)
const error = ref('')

// Editing state
const editTitle = ref('')
const editContent = ref('')
const isSaving = ref(false)
const saveSuccess = ref(false)

const isLoggedIn = computed(() => {
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
    const res = await http.get('/notes')
    notes.value = res.data.data || []
    
    // Auto select first note if none selected
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
    const res = await http.post('/notes', { title })
    const newNote = res.data.data
    notes.value.unshift(newNote) // Add to top
    activeNoteId.value = newNote.id
    syncEditState()
  } catch (e) {
    error.value = '创建笔记失败'
  }
}

let saveTimeout = null
async function saveNote() {
  if (!activeNote.value || !isLoggedIn.value) return
  
  // If nothing changed, don't ping backend
  if (editTitle.value === activeNote.value.title && editContent.value === activeNote.value.content) {
    return
  }

  isSaving.value = true
  saveSuccess.value = false
  
  try {
    const res = await http.put(`/notes/${activeNoteId.value}`, {
      title: editTitle.value,
      content: editContent.value
    })
    
    // Update local state directly to avoid full reload jump
    activeNote.value.title = res.data.data.title
    activeNote.value.content = res.data.data.content
    activeNote.value.updated_at = res.data.data.updated_at
    
    isSaving.value = false
    saveSuccess.value = true
    
    // Hide success message after 3 secs
    clearTimeout(saveTimeout)
    saveTimeout = setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
    
  } catch (e) {
    isSaving.value = false
    alert('保存云端失败，请检查网络')
  }
}

async function deleteNote() {
  if (!activeNote.value || !confirm('确定要永久删除这篇笔记吗？')) return
  
  try {
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

// Global Custom Event listener pattern to refresh on Login/Logout
onMounted(() => {
    // If the user lands while logged in, pre-fetch
    if (isLoggedIn.value) {
        loadNotes()
    }
    
    // Simple window event hook to listen if AppLayout fires a login event
    window.addEventListener('user-auth-changed', () => {
        if(isLoggedIn.value) {
            loadNotes()
        } else {
            notes.value = []
            activeNoteId.value = null
        }
    })
})
</script>

<style scoped>
.memo-sidebar {
  position: fixed;
  top: 60px; /* Below topbar */
  right: -320px; /* Hidden by default */
  width: 320px;
  height: calc(100vh - 60px);
  background: #ffffff;
  border-left: 1px solid #e1e4e8;
  box-shadow: -4px 0 15px rgba(0,0,0,0.05);
  transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 99;
  display: flex;
  flex-direction: column;
}

.memo-sidebar.memo-open {
  right: 0;
}

.toggle-btn {
  position: absolute;
  top: 20px;
  left: -40px;
  width: 40px;
  height: 120px;
  background: #2563eb;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  cursor: pointer;
  border-radius: 8px 0 0 8px;
  font-weight: bold;
  box-shadow: -2px 2px 5px rgba(0,0,0,0.1);
  user-select: none;
}
.toggle-btn:hover {
  background: #1d4ed8;
}

.memo-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}

.memo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 12px;
  margin-bottom: 16px;
}
.memo-header h3 {
  margin: 0;
  font-size: 16px;
  color: #24292f;
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
  margin-bottom: 16px;
}
.note-selector label {
  display: block;
  font-size: 12px;
  color: #57606a;
  margin-bottom: 4px;
}
.select-box {
  flex: 1;
  padding: 6px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  outline: none;
}

.note-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.note-title-input {
  width: 100%;
  padding: 8px;
  border: 1px solid transparent;
  border-bottom: 1px dashed #d0d7de;
  font-size: 16px;
  font-weight: bold;
  outline: none;
  transition: border 0.2s;
}
.note-title-input:focus {
  border-bottom: 1px solid #2563eb;
}

.note-textarea {
  flex: 1;
  width: 100%;
  resize: none;
  padding: 12px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  outline: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  background: #fdfdfd;
}
.note-textarea:focus {
  border-color: #2563eb;
  background: #fff;
}

.save-status {
  text-align: right;
  font-size: 12px;
}
.muted { color: #8c959f; }
.saving { color: #f59e0b; font-weight: bold;}
.success { color: #10b981; font-weight: bold;}

.error-msg { color: #cf222e; font-size: 12px; margin-bottom: 10px; }
.memo-empty {
  text-align: center;
  color: #8c959f;
  margin-top: 40px;
  font-size: 14px;
}

.btn { cursor: pointer; border-radius: 6px; border: 1px solid transparent; font-weight: 600; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-primary:hover { background: #1d4ed8; }
.btn-danger { background: #cf222e; color: white; }
.btn-danger:hover { background: #a41e25; }
</style>
