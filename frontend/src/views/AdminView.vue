<template>
  <div class="admin-page">
    <section class="hero admin-hero">
      <div>
        <h1>管理员后台</h1>
        <p class="muted">首页只保留账号管理。发现违规时，直接封禁账号即可。</p>
      </div>
      <div class="hero-actions">
        <button class="btn" @click="goHome">返回首页</button>
        <button class="btn btn-primary" :disabled="loading" @click="loadAll">刷新数据</button>
      </div>
    </section>

    <div v-if="loading" class="hint-card">正在加载管理员数据...</div>
    <div v-else-if="error" class="hint-card error">{{ error }}</div>

    <template v-else>
      <section class="stats-grid">
        <article class="stat-card">
          <span class="stat-label">用户总数</span>
          <strong>{{ overview.user_count || 0 }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">启用账号</span>
          <strong>{{ overview.active_user_count || 0 }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">停用账号</span>
          <strong>{{ overview.disabled_user_count || 0 }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">管理员</span>
          <strong>{{ overview.admin_count || 0 }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">教师</span>
          <strong>{{ overview.teacher_count || 0 }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">学生</span>
          <strong>{{ overview.student_count || 0 }}</strong>
        </article>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2>账号管理</h2>
            <p class="muted">支持关键词、角色、状态筛选，以及分页查看。</p>
          </div>
          <div class="summary-text">
            共 {{ pagination.total || 0 }} 条
          </div>
        </div>

        <div class="filter-bar">
          <input
            v-model.trim="filters.keyword"
            class="search-input"
            placeholder="搜索用户名或邮箱"
            @keyup.enter="applyFilters"
          />
          <select v-model="filters.role" class="filter-select" @change="applyFilters">
            <option value="">全部角色</option>
            <option value="admin">管理员</option>
            <option value="teacher">教师</option>
            <option value="student">学生</option>
          </select>
          <select v-model="filters.status" class="filter-select" @change="applyFilters">
            <option value="">全部状态</option>
            <option value="active">启用</option>
            <option value="disabled">停用</option>
          </select>
          <select v-model.number="filters.pageSize" class="filter-select" @change="applyFilters">
            <option :value="10">10 条/页</option>
            <option :value="20">20 条/页</option>
            <option :value="30">30 条/页</option>
            <option :value="50">50 条/页</option>
          </select>
          <button class="btn btn-primary" @click="applyFilters">筛选</button>
          <button class="btn" @click="resetFilters">重置</button>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>用户名</th>
                <th>邮箱</th>
                <th>角色</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id">
                <td>{{ user.id }}</td>
                <td>{{ user.username }}</td>
                <td>{{ user.email }}</td>
                <td>
                  <span class="badge">{{ user.role }}</span>
                </td>
                <td>
                  <span :class="['badge', user.status === 'active' ? 'badge-ok' : 'badge-warn']">
                    {{ user.status === 'active' ? '启用' : '停用' }}
                  </span>
                </td>
                <td>{{ formatTime(user.created_at) }}</td>
                <td>
                  <button
                    class="btn"
                    :disabled="pendingUserId === user.id"
                    @click="toggleUserStatus(user)"
                  >
                    {{ user.status === 'active' ? '封禁' : '解封' }}
                  </button>
                </td>
              </tr>
              <tr v-if="!users.length">
                <td colspan="7" class="empty-cell">当前筛选条件下没有数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination-bar">
          <div class="page-info">
            第 {{ pagination.page || 1 }} / {{ pagination.total_pages || 1 }} 页
          </div>
          <div class="page-actions">
            <button class="btn" :disabled="pagination.page <= 1" @click="changePage(pagination.page - 1)">
              上一页
            </button>
            <button
              v-for="page in pageButtons"
              :key="page"
              :class="['btn', page === pagination.page ? 'btn-primary' : '']"
              @click="changePage(page)"
            >
              {{ page }}
            </button>
            <button
              class="btn"
              :disabled="pagination.page >= pagination.total_pages"
              @click="changePage(pagination.page + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const pendingUserId = ref(null)

const overview = ref({})
const users = ref([])
const pagination = ref({
  page: 1,
  page_size: 10,
  total: 0,
  total_pages: 1,
})

const filters = ref({
  keyword: '',
  role: '',
  status: '',
  pageSize: 10,
})

function goHome() {
  router.push('/')
}

function formatTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

const pageButtons = computed(() => {
  const totalPages = pagination.value.total_pages || 1
  const current = pagination.value.page || 1
  const start = Math.max(1, current - 2)
  const end = Math.min(totalPages, start + 4)
  const realStart = Math.max(1, end - 4)
  const result = []
  for (let i = realStart; i <= end; i += 1) {
    result.push(i)
  }
  return result
})

async function loadOverview() {
  const res = await http.get('/admin/overview')
  overview.value = res.data.data || {}
}

async function loadUsers(page = 1) {
  const params = {
    page,
    page_size: filters.value.pageSize,
  }

  if (filters.value.keyword) params.keyword = filters.value.keyword
  if (filters.value.role) params.role = filters.value.role
  if (filters.value.status) params.status = filters.value.status

  const res = await http.get('/admin/users', { params })
  users.value = res.data.data?.items || []
  pagination.value = res.data.data?.pagination || {
    page: 1,
    page_size: filters.value.pageSize,
    total: 0,
    total_pages: 1,
  }
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadOverview(), loadUsers(pagination.value.page || 1)])
  } catch (e) {
    error.value = e?.response?.data?.message || '管理员数据加载失败'
  } finally {
    loading.value = false
  }
}

async function applyFilters() {
  loading.value = true
  error.value = ''
  try {
    await loadUsers(1)
  } catch (e) {
    error.value = e?.response?.data?.message || '筛选失败'
  } finally {
    loading.value = false
  }
}

async function resetFilters() {
  filters.value = {
    keyword: '',
    role: '',
    status: '',
    pageSize: 10,
  }
  await applyFilters()
}

async function changePage(page) {
  if (page < 1 || page > (pagination.value.total_pages || 1)) return
  loading.value = true
  error.value = ''
  try {
    await loadUsers(page)
  } catch (e) {
    error.value = e?.response?.data?.message || '分页加载失败'
  } finally {
    loading.value = false
  }
}

async function toggleUserStatus(user) {
  const nextStatus = user.status === 'active' ? 'disabled' : 'active'
  const actionText = nextStatus === 'disabled' ? '封禁' : '解封'
  if (!window.confirm(`确定要${actionText}账号 ${user.username} 吗？`)) return

  pendingUserId.value = user.id
  try {
    await http.patch(`/admin/users/${user.id}/status`, { status: nextStatus })
    await Promise.all([loadOverview(), loadUsers(pagination.value.page || 1)])
  } catch (e) {
    window.alert(e?.response?.data?.message || '账号状态更新失败')
  } finally {
    pendingUserId.value = null
  }
}

onMounted(loadAll)
</script>

<style scoped>
.admin-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 0 40px;
}

.admin-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 18px;
}

.stat-card strong {
  display: block;
  font-size: 28px;
  margin-top: 8px;
}

.stat-label {
  color: var(--muted);
  font-size: 13px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.section-head h2 {
  margin: 0 0 6px;
}

.section-head p,
.summary-text {
  margin: 0;
  color: var(--muted);
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.search-input,
.filter-select {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  color: var(--text);
  padding: 10px 12px;
  font-size: 14px;
}

.search-input {
  min-width: 260px;
  flex: 1 1 280px;
}

.filter-select {
  min-width: 120px;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: middle;
}

.data-table th {
  color: var(--muted);
  font-weight: 600;
  font-size: 13px;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 12px;
  font-weight: 600;
}

.badge-ok {
  background: #dcfce7;
  color: #166534;
}

.badge-warn {
  background: #fee2e2;
  color: #b91c1c;
}

.empty-cell {
  color: var(--muted);
  text-align: center;
  padding: 20px 0;
}

.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}

.page-info {
  color: var(--muted);
  font-size: 14px;
}

.page-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 900px) {
  .admin-hero,
  .section-head,
  .pagination-bar {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 640px) {
  .admin-page {
    padding-top: 16px;
  }

  .hero-actions,
  .page-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-bar {
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    min-width: 0;
    width: 100%;
  }
}
</style>
