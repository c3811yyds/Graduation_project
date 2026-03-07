<template>
  <div class="dashboard-page">
    <header class="head">
      <div class="head-row">
        <div>
          <h1 class="page-title">数据总览分析系统</h1>
          <p class="muted page-subtitle">{{ subtitleText }}</p>
        </div>
        <button class="btn" @click="goHome">返回首页</button>
      </div>
    </header>

    <div v-if="loading" class="center-msg">正在加载数据总览...</div>
    <div v-else-if="error" class="center-msg error-text">{{ error }}</div>

    <template v-else>
      <section v-if="showCoursePager" class="course-pager panel-lite">
        <div class="pager-row">
          <div class="pager-info">
            <strong>课程切换</strong>
            <p class="muted pager-desc">
              当前第 {{ coursePage }} / {{ totalCoursePages }} 组
              (课程 ID {{ visibleCourseStartId }} - {{ visibleCourseEndId }})
            </p>
            <p class="muted pager-desc">当前课程：{{ visibleCourseNamesText }}</p>
          </div>

          <div class="pager-actions">
            <button class="btn" :disabled="coursePage <= 1" @click="prevCoursePage">上一组</button>
            <button class="btn" :disabled="coursePage >= totalCoursePages" @click="nextCoursePage">下一组</button>
            <select v-model.number="coursePage" class="page-select">
              <option v-for="item in coursePageOptions" :key="item.page" :value="item.page">
                {{ item.label }}
              </option>
            </select>
          </div>
        </div>
      </section>

      <div class="charts-grid">
        <div class="chart-card">
          <h3>{{ isStudent ? '学习进度对比' : '课程选修人数分布' }}</h3>
          <v-chart class="chart" :option="barChartOption" autoresize />
        </div>

        <div class="chart-card">
          <h3>{{ isStudent ? '各课程完成数量分布' : '课程综合评分对比' }}</h3>
          <v-chart class="chart chart-pie" :option="pieChartOption" autoresize />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

const COURSE_PAGE_SIZE = 8

const loading = ref(true)
const error = ref('')
const data = ref({})
const coursePage = ref(1)

const router = useRouter()

const isStudent = computed(() => data.value?.role === 'student')
const isAdmin = computed(() => data.value?.role === 'admin')

const subtitleText = computed(() => {
  if (isAdmin.value) return '全课程选修评分信息'
  return '实时监控你的教学/学习进度状态'
})

const allCourseNames = computed(() => data.value?.courseNames || [])
const allCourseIds = computed(() => data.value?.courseIds || [])
const allEnrollCounts = computed(() => data.value?.enrollCounts || [])
const allReviewAverages = computed(() => data.value?.reviewAverages || [])
const allProgressRates = computed(() => data.value?.progressRates || [])
const allCompletedCounts = computed(() => data.value?.completedCounts || [])

const totalCoursePages = computed(() => {
  if (isStudent.value) return 1
  return Math.max(1, Math.ceil(allCourseNames.value.length / COURSE_PAGE_SIZE))
})

const showCoursePager = computed(() => !isStudent.value && allCourseNames.value.length > COURSE_PAGE_SIZE)

const courseSliceStart = computed(() => {
  if (isStudent.value) return 0
  return (coursePage.value - 1) * COURSE_PAGE_SIZE
})

const courseSliceEnd = computed(() => {
  if (isStudent.value) return allCourseNames.value.length
  return courseSliceStart.value + COURSE_PAGE_SIZE
})

const visibleCourseNames = computed(() => {
  if (isStudent.value) return allCourseNames.value
  return allCourseNames.value.slice(courseSliceStart.value, courseSliceEnd.value)
})

const visibleCourseIds = computed(() => {
  if (isStudent.value) return allCourseIds.value
  return allCourseIds.value.slice(courseSliceStart.value, courseSliceEnd.value)
})

const visibleCourseLabels = computed(() =>
  visibleCourseNames.value.map((name, index) => {
    const courseId = visibleCourseIds.value[index]
    return courseId ? `${name} (${courseId})` : name
  })
)

const visibleEnrollCounts = computed(() => {
  if (isStudent.value) return allEnrollCounts.value
  return allEnrollCounts.value.slice(courseSliceStart.value, courseSliceEnd.value)
})

const visibleReviewAverages = computed(() => {
  if (isStudent.value) return allReviewAverages.value
  return allReviewAverages.value.slice(courseSliceStart.value, courseSliceEnd.value)
})

const visibleProgressRates = computed(() => allProgressRates.value)
const visibleCompletedCounts = computed(() => allCompletedCounts.value)

const visibleCourseStartId = computed(() => {
  if (!visibleCourseIds.value.length) return '-'
  return visibleCourseIds.value[0]
})

const visibleCourseEndId = computed(() => {
  if (!visibleCourseIds.value.length) return '-'
  return visibleCourseIds.value[visibleCourseIds.value.length - 1]
})

const visibleCourseNamesText = computed(() => {
  if (!visibleCourseLabels.value.length) return '暂无课程'
  return visibleCourseLabels.value.join('、')
})

const coursePageOptions = computed(() => {
  const result = []
  for (let page = 1; page <= totalCoursePages.value; page += 1) {
    const start = (page - 1) * COURSE_PAGE_SIZE
    const end = start + COURSE_PAGE_SIZE
    const ids = allCourseIds.value.slice(start, end)
    const startId = ids[0] ?? '-'
    const endId = ids[ids.length - 1] ?? '-'
    result.push({
      page,
      label: `第 ${page} 组 (课程 ID ${startId} - ${endId})`,
    })
  }
  return result
})

// [功能说明]: 点击右上角按钮返回首页。
function goHome() {
  router.push('/')
}

// [功能说明]: 切到上一组课程，配合教师/管理员的大屏分页浏览。
function prevCoursePage() {
  if (coursePage.value > 1) coursePage.value -= 1
}

// [功能说明]: 切到下一组课程，继续浏览后续课程数据。
function nextCoursePage() {
  if (coursePage.value < totalCoursePages.value) coursePage.value += 1
}

// [功能说明]: 页面初始化时按角色拉取学生、教师或管理员对应的大屏统计数据。
onMounted(async () => {
  try {
    const meRes = await http.get('/users/me')
    const role = meRes.data?.data?.role
    const endpoint = role === 'admin' ? '/admin/analytics' : '/users/analytics'
    const res = await http.get(endpoint)
    data.value = res.data.data || {}
    coursePage.value = 1
  } catch (e) {
    error.value = e?.response?.data?.message || '获取统计大盘失败'
  } finally {
    loading.value = false
  }
})

// [功能说明]: 生成左侧柱状图配置；学生显示学习进度，教师/管理员显示选修人数。
const barChartOption = computed(() => {
  if (isStudent.value) {
    return {
      tooltip: { formatter: '{b}: {c}%' },
      grid: { left: 40, right: 20, top: 20, bottom: 70, containLabel: true },
      xAxis: {
        type: 'category',
        data: visibleCourseLabels.value,
        axisLabel: {
          interval: 0,
          rotate: 28,
        },
      },
      yAxis: { type: 'value', max: 100 },
      series: [
        {
          data: visibleProgressRates.value,
          type: 'bar',
          itemStyle: { color: '#0ea5e9' },
          barWidth: '40%',
        },
      ],
    }
  }

  return {
    tooltip: { formatter: '{b}: {c} 人' },
    grid: { left: 40, right: 20, top: 20, bottom: 78, containLabel: true },
    xAxis: {
      type: 'category',
      data: visibleCourseLabels.value,
      axisLabel: {
        interval: 0,
        rotate: 28,
      },
    },
    yAxis: { type: 'value' },
    series: [
      {
        data: visibleEnrollCounts.value,
        type: 'bar',
        itemStyle: { color: '#10b981' },
        barWidth: '40%',
      },
    ],
  }
})

// [功能说明]: 生成右侧饼图配置；学生显示完成数量，教师/管理员显示课程评分。
const pieChartOption = computed(() => {
  if (isStudent.value) {
    const pieData = visibleCourseLabels.value.map((name, index) => ({
      name,
      value: visibleCompletedCounts.value[index] || 0,
    }))

    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        bottom: 0,
        left: 'center',
        itemGap: 12,
        textStyle: {
          width: 130,
          overflow: 'truncate',
        },
      },
      series: [
        {
          name: '完成数量',
          type: 'pie',
          radius: '44%',
          center: ['50%', '36%'],
          data: pieData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    }
  }

  const pieData = visibleCourseLabels.value.map((name, index) => ({
    name,
    value: visibleReviewAverages.value[index] || 0,
  }))

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 分' },
    legend: {
      bottom: 0,
      left: 'center',
      itemGap: 12,
      textStyle: {
        width: 130,
        overflow: 'truncate',
      },
    },
    series: [
      {
        name: '课程评分',
        type: 'pie',
        radius: ['26%', '48%'],
        center: ['50%', '33%'],
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        data: pieData,
      },
    ],
  }
})
</script>

<style scoped>
.dashboard-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.page-title {
  margin-bottom: 0.5rem;
}

.page-subtitle {
  margin-top: 0;
}

.center-msg {
  text-align: center;
  padding: 4rem;
  color: var(--muted);
  font-size: 1.25rem;
}

.error-text {
  color: var(--danger);
}

.panel-lite {
  background: white;
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.06);
  padding: 1rem 1.25rem;
  margin-top: 1.5rem;
}

.pager-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.pager-info {
  flex: 1;
  min-width: 0;
}

.pager-desc {
  margin: 6px 0 0;
  line-height: 1.6;
}

.pager-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.page-select {
  min-width: 240px;
  border: 1px solid #d0d7de;
  background: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  font-weight: 600;
  color: var(--text);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.chart-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.1);
  border: 2px solid var(--border);
}

.chart-card h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--text);
  border-bottom: 2px solid var(--border);
  padding-bottom: 0.5rem;
}

.chart {
  height: 400px;
  width: 100%;
}

.chart-pie {
  height: 450px;
}

.btn {
  border: 1px solid #d0d7de;
  background: #fff;
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.btn:hover {
  background: #f6f8fa;
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 1rem;
  }

  .head-row,
  .pager-row {
    flex-direction: column;
    align-items: stretch;
  }

  .pager-actions {
    width: 100%;
  }

  .pager-actions .btn,
  .page-select {
    width: 100%;
  }

  .charts-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .chart,
  .chart-pie {
    height: 360px;
  }
}
</style>
