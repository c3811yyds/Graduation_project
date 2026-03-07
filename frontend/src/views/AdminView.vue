<template>
  <div class="admin-page">
    <section class="hero admin-hero">
      <div>
        <h1>管理员后台</h1>
        <p class="muted">
          集中管理账号状态与教师邀请码，方便完成筛选、封禁、查询和发放操作。
        </p>
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
          <span class="stat-label">账号总数</span>
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
        <article class="stat-card">
          <span class="stat-label">可用邀请码</span>
          <strong>{{ overview.unused_invite_count || 0 }}</strong>
        </article>
      </section>

      <div class="tab-bar">
        <button
          :class="['tab-btn', activeTab === 'users' ? 'tab-btn-active' : '']"
          @click="activeTab = 'users'"
        >
          账号管理
        </button>
        <button
          :class="['tab-btn', activeTab === 'invites' ? 'tab-btn-active' : '']"
          @click="activeTab = 'invites'"
        >
          教师邀请码
        </button>
      </div>

      <section v-if="activeTab === 'users'" class="panel">
        <div class="section-head">
          <div>
            <h2>账号管理</h2>
            <p class="muted">支持按关键词、角色、状态筛选账号，并直接启用或停用账号。</p>
          </div>
          <div class="summary-text">共 {{ pagination.total || 0 }} 条</div>
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
                <td>{{ user.email || '-' }}</td>
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
                    {{ user.status === 'active' ? '停用' : '启用' }}
                  </button>
                </td>
              </tr>
              <tr v-if="!users.length">
                <td colspan="7" class="empty-cell">当前筛选条件下没有账号数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination-bar">
          <div class="page-info">第 {{ pagination.page || 1 }} / {{ pagination.total_pages || 1 }} 页</div>
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

      <section v-else class="panel">
        <div class="section-head">
          <div>
            <h2>教师邀请码</h2>
            <p class="muted">支持生成邀请码、分页查看状态，并按创建人、使用人或邀请码关键词查询。</p>
          </div>
          <div class="summary-text">共 {{ invitePagination.total || 0 }} 条</div>
        </div>

        <div class="invite-toolbar">
          <select v-model.number="inviteFilters.expireDays" class="filter-select">
            <option :value="1">1 天有效</option>
            <option :value="3">3 天有效</option>
            <option :value="7">7 天有效</option>
            <option :value="15">15 天有效</option>
            <option :value="30">30 天有效</option>
          </select>
          <button class="btn btn-primary" :disabled="generatingInvite" @click="createInviteCode">
            {{ generatingInvite ? '正在生成...' : '生成邀请码' }}
          </button>
          <span class="invite-rule">一个邀请码只能注册一个教师账号，可按有效天数单独生成。</span>
        </div>

        <div class="filter-bar invite-filter-bar">
          <input
            v-model.trim="inviteFilters.keyword"
            class="search-input"
            placeholder="搜索邀请码、创建人或使用人"
            @keyup.enter="applyInviteFilters"
          />
          <select v-model="inviteFilters.status" class="filter-select" @change="applyInviteFilters">
            <option value="">全部状态</option>
            <option value="active">可用</option>
            <option value="unused">未使用</option>
            <option value="used">已使用</option>
            <option value="expired">已过期</option>
          </select>
          <select
            v-model.number="inviteFilters.pageSize"
            class="filter-select"
            @change="applyInviteFilters"
          >
            <option :value="10">10 条/页</option>
            <option :value="20">20 条/页</option>
            <option :value="30">30 条/页</option>
            <option :value="50">50 条/页</option>
          </select>
          <button class="btn btn-primary" @click="applyInviteFilters">筛选</button>
          <button class="btn" @click="resetInviteFilters">重置</button>
        </div>

        <div v-if="inviteError" class="hint-card error compact-hint">{{ inviteError }}</div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>邀请码</th>
                <th>状态</th>
                <th>创建人</th>
                <th>使用人</th>
                <th>过期时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in inviteCodes" :key="item.id">
                <td>{{ item.id }}</td>
                <td class="code-cell">{{ item.code }}</td>
                <td>
                  <span
                    :class="[
                      'badge',
                      item.is_used || item.is_expired ? 'badge-warn' : 'badge-ok',
                    ]"
                  >
                    {{ item.is_used ? '已使用' : item.is_expired ? '已过期' : '可用' }}
                  </span>
                </td>
                <td>{{ item.created_by_name || '历史数据' }}</td>
                <td>{{ item.used_by_name || '-' }}</td>
                <td>{{ formatTime(item.expires_at) }}</td>
                <td>
                  <button class="btn" @click="copyInviteCode(item.code)">复制</button>
                </td>
              </tr>
              <tr v-if="!inviteCodes.length">
                <td colspan="7" class="empty-cell">当前筛选条件下没有邀请码数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination-bar">
          <div class="page-info">
            第 {{ invitePagination.page || 1 }} / {{ invitePagination.total_pages || 1 }} 页
          </div>
          <div class="page-actions">
            <button
              class="btn"
              :disabled="invitePagination.page <= 1"
              @click="changeInvitePage(invitePagination.page - 1)"
            >
              上一页
            </button>
            <button
              v-for="page in invitePageButtons"
              :key="page"
              :class="['btn', page === invitePagination.page ? 'btn-primary' : '']"
              @click="changeInvitePage(page)"
            >
              {{ page }}
            </button>
            <button
              class="btn"
              :disabled="invitePagination.page >= invitePagination.total_pages"
              @click="changeInvitePage(invitePagination.page + 1)"
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

const activeTab = ref('users')
const loading = ref(true)
const error = ref('')
const pendingUserId = ref(null)
const generatingInvite = ref(false)

const overview = ref({})
const users = ref([])
const inviteCodes = ref([])
const pagination = ref({
  page: 1,
  page_size: 10,
  total: 0,
  total_pages: 1,
})
const invitePagination = ref({
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
const inviteFilters = ref({
  keyword: '',
  status: '',
  pageSize: 10,
  expireDays: 1,
})
const inviteError = ref('')

// 返回首页，方便管理员从后台回到主站继续操作。
function goHome() {
  router.push('/')
}

// 统一格式化时间展示，接口缺值时显示占位符。
function formatTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

// 账号列表分页按钮最多展示当前页附近 5 个页码。
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

// 邀请码列表分页按钮与账号列表保持同一交互规则。
const invitePageButtons = computed(() => {
  const totalPages = invitePagination.value.total_pages || 1
  const current = invitePagination.value.page || 1
  const start = Math.max(1, current - 2)
  const end = Math.min(totalPages, start + 4)
  const realStart = Math.max(1, end - 4)
  const result = []
  for (let i = realStart; i <= end; i += 1) {
    result.push(i)
  }
  return result
})

// 拉取后台概览卡片数据。
async function loadOverview() {
  const res = await http.get('/admin/overview')
  overview.value = res.data.data || {}
}

// 按筛选条件拉取账号列表和分页信息。
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

// 按筛选条件拉取邀请码列表和分页信息。
async function loadInviteCodes(page = 1) {
  const params = {
    page,
    page_size: inviteFilters.value.pageSize,
  }

  if (inviteFilters.value.keyword) params.keyword = inviteFilters.value.keyword
  if (inviteFilters.value.status) params.status = inviteFilters.value.status

  const res = await http.get('/admin/invite-codes', { params })
  inviteCodes.value = res.data.data?.items || []
  invitePagination.value = res.data.data?.pagination || {
    page: 1,
    page_size: inviteFilters.value.pageSize,
    total: 0,
    total_pages: 1,
  }
}

// 后台首屏统一加载概览、账号和邀请码数据。
async function loadAll() {
  loading.value = true
  error.value = ''
  inviteError.value = ''
  try {
    await Promise.all([loadOverview(), loadUsers(pagination.value.page || 1), loadInviteCodes(invitePagination.value.page || 1)])
  } catch (e) {
    error.value = e?.response?.data?.message || '管理员数据加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 应用账号筛选条件并回到第一页。
async function applyFilters() {
  loading.value = true
  error.value = ''
  try {
    await loadUsers(1)
  } catch (e) {
    error.value = e?.response?.data?.message || '账号筛选失败'
  } finally {
    loading.value = false
  }
}

// 重置账号筛选项，并重新加载第一页列表。
async function resetFilters() {
  filters.value = {
    keyword: '',
    role: '',
    status: '',
    pageSize: 10,
  }
  await applyFilters()
}

// 切换账号管理分页。
async function changePage(page) {
  if (page < 1 || page > (pagination.value.total_pages || 1)) return
  loading.value = true
  error.value = ''
  try {
    await loadUsers(page)
  } catch (e) {
    error.value = e?.response?.data?.message || '账号分页加载失败'
  } finally {
    loading.value = false
  }
}

// 切换账号启用状态，管理员自己不能停用自己。
async function toggleUserStatus(user) {
  const nextStatus = user.status === 'active' ? 'disabled' : 'active'
  const actionText = nextStatus === 'disabled' ? '停用' : '启用'
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

// 应用邀请码筛选条件并回到第一页。
async function applyInviteFilters() {
  inviteError.value = ''
  try {
    await loadInviteCodes(1)
  } catch (e) {
    inviteError.value = e?.response?.data?.message || '邀请码筛选失败'
  }
}

// 重置邀请码筛选项，并保留默认 1 天有效配置。
async function resetInviteFilters() {
  inviteFilters.value = {
    keyword: '',
    status: '',
    pageSize: 10,
    expireDays: 1,
  }
  await applyInviteFilters()
}

// 切换邀请码列表分页。
async function changeInvitePage(page) {
  if (page < 1 || page > (invitePagination.value.total_pages || 1)) return
  inviteError.value = ''
  try {
    await loadInviteCodes(page)
  } catch (e) {
    inviteError.value = e?.response?.data?.message || '邀请码分页加载失败'
  }
}

// 按当前有效天数生成教师邀请码，并刷新概览和列表。
async function createInviteCode() {
  generatingInvite.value = true
  inviteError.value = ''
  try {
    await http.post('/admin/invite-codes', {
      expire_days: inviteFilters.value.expireDays,
    })
    await Promise.all([loadOverview(), loadInviteCodes(1)])
    activeTab.value = 'invites'
  } catch (e) {
    inviteError.value = e?.response?.data?.message || '邀请码生成失败'
  } finally {
    generatingInvite.value = false
  }
}

// 一键复制邀请码，方便管理员发给教师。
async function copyInviteCode(code) {
  try {
    await navigator.clipboard.writeText(code)
    window.alert('邀请码已复制')
  } catch (e) {
    window.alert('复制失败，请手动复制邀请码')
  }
}

// 页面加载后同步后台所需的全部基础数据。
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

.tab-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.tab-btn {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  color: var(--text);
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.2s ease;
}

.tab-btn:hover {
  border-color: rgba(59, 130, 246, 0.35);
  color: #2563eb;
}

.tab-btn-active {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
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

.invite-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.invite-rule {
  color: var(--muted);
  font-size: 14px;
}

.compact-hint {
  margin-bottom: 12px;
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

.code-cell {
  font-family: 'Consolas', 'Courier New', monospace;
  letter-spacing: 0.04em;
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

  .filter-bar,
  .invite-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input,
  .filter-select {
    min-width: 0;
    width: 100%;
  }
}
</style>
