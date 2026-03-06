<template>
  <div class="dashboard-page">
    <header class="head">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1 style="margin-bottom: 0.5rem;">数据大屏分析系统</h1>
          <p class="muted" style="margin-top: 0;">实时监控你的教学/学习进度状态</p>
        </div>
        <button class="btn" @click="goHome">返回主页</button>
      </div>
    </header>

    <div v-if="loading" class="center-msg">正在加载分析数据...</div>
    <div v-else-if="error" class="center-msg" style="color:var(--danger)">{{ error }}</div>
    
    <div v-else class="charts-grid">
      <!-- 左右分栏结构 -->
      <div class="chart-card">
        <h3>{{ isStudent ? '学习进度对比' : '课程选修人数分布' }}</h3>
        <v-chart class="chart" :option="barChartOption" autoresize />
      </div>

      <div class="chart-card">
        <h3>{{ isStudent ? '各课程阅读量分布' : '课程综合评分对比' }}</h3>
        <v-chart class="chart" :option="pieChartOption" autoresize />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'

// 引入 ECharts 核心和所需组件
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

const loading = ref(true)
const error = ref('')
const data = ref({})

const isStudent = computed(() => data.value?.role === 'student')
const isTeacher = computed(() => data.value?.role === 'teacher')

const router = useRouter()

// [功能说明]: 退出数据大屏返回主菜单
function goHome() {
  router.push('/')
}

onMounted(async () => {
  try {
    // [后端映射]: GET /api/users/analytics -> 按角色拉取统计大盘数据
    const res = await http.get('/users/analytics')
    data.value = res.data.data
  } catch (e) {
    error.value = e.response?.data?.message || '无法获取分析数据'
  } finally {
    loading.value = false
  }
})

// 图表 1 配置 (柱状图)
const barChartOption = computed(() => {
  if (isStudent.value) {
    return {
      tooltip: { formatter: '{b}: {c}% 进度' },
      xAxis: { type: 'category', data: data.value.courseNames || [], axisLabel: { interval: 0, rotate: 30 } },
      yAxis: { type: 'value', max: 100 },
      series: [
        {
          data: data.value.progressRates || [],
          type: 'bar',
          itemStyle: { color: '#0ea5e9' },
          barWidth: '40%'
        }
      ]
    }
  } else {
    return {
      tooltip: { formatter: '{b}: {c} 人' },
      xAxis: { type: 'category', data: data.value.courseNames || [], axisLabel: { interval: 0, rotate: 30 } },
      yAxis: { type: 'value' },
      series: [
        {
          data: data.value.enrollCounts || [],
          type: 'bar',
          itemStyle: { color: '#10b981' },
          barWidth: '40%'
        }
      ]
    }
  }
})

// 图表 2 配置 (饼图对于学生 / 这里我们用柱状图或者饼图结合)
const pieChartOption = computed(() => {
  if (isStudent.value) {
    const pieData = (data.value.courseNames || []).map((name, idx) => ({
      name,
      value: data.value.completedCounts[idx] || 0
    }))
    return {
      tooltip: { trigger: 'item', formatter: '{a} <br/>{b} : {c} ({d}%)' },
      legend: { bottom: '0%' },
      series: [
        {
          name: '阅读量(课件数)',
          type: 'pie',
          radius: '50%',
          data: pieData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    }
  } else {
    // 老师的平均评分饼图或者柱状
    const pieData = (data.value.courseNames || []).map((name, idx) => ({
      name,
      value: data.value.reviewAverages[idx] || 0
    }))
    return {
      tooltip: { trigger: 'item', formatter: '{b} : {c}分' },
      legend: { bottom: '0%' },
      series: [
        {
          name: '平均得分',
          type: 'pie',
          radius: ['40%', '70%'],
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          data: pieData
        }
      ]
    }
  }
})

</script>

<style scoped>
.dashboard-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.center-msg {
  text-align: center;
  padding: 4rem;
  color: var(--muted);
  font-size: 1.25rem;
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
  box-shadow: 4px 4px 0px rgba(0, 0, 0, 0.1);
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
</style>