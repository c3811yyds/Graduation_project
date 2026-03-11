<template>
  <div class="dashboard-page">
    <header class="head">
      <div class="head-row">
        <div>
          <h1 class="page-title">数据总览</h1>
          <p class="muted page-subtitle">{{ subtitleText }}</p>
        </div>
        <button class="btn" @click="goHome">返回首页</button>
      </div>
    </header>

    <div v-if="loading" class="center-msg">正在加载数据总览...</div>
    <div v-else-if="error" class="center-msg error-text">{{ error }}</div>

    <template v-else>
      <section v-if="advice" class="advice-panel">
        <div class="advice-header">
          <div>
            <p class="advice-kicker">智能学习建议</p>
            <p class="advice-kicker">{{ advicePanelTitle }}</p>
            <h2 class="advice-title">{{ advice.headline }}</h2>
            <p class="muted advice-summary">{{ advice.summary }}</p>
          </div>
        </div>

        <div class="advice-stats">
          <article v-for="item in adviceStats" :key="item.label" class="advice-stat">
            <span class="advice-stat-label">{{ item.label }}</span>
            <strong class="advice-stat-value">{{ item.value }}</strong>
          </article>
        </div>

        <div class="advice-body">
          <article v-if="advice.focus" class="advice-focus-card">
            <span class="advice-focus-badge">当前优先事项</span>
            <h3>{{ advice.focus.title }}</h3>
            <p>{{ advice.focus.description }}</p>
            <button
              v-if="advice.focus.action_path"
              class="btn btn-primary"
              @click="openAdviceAction(advice.focus.action_path)"
            >
              {{ advice.focus.action_label || "立即处理" }}
            </button>
          </article>

          <div v-if="adviceRecommendations.length" class="advice-list">
            <article
              v-for="item in adviceRecommendations"
              :key="`${item.title}-${item.action_path}`"
              class="advice-item"
            >
              <div>
                <h3>{{ item.title }}</h3>
                <p>{{ item.description }}</p>
              </div>
              <button
                v-if="item.action_path"
                class="btn"
                @click="openAdviceAction(item.action_path)"
              >
                {{ item.action_label || "查看" }}
              </button>
            </article>
          </div>
        </div>
      </section>

      <section v-if="showCourseControls" class="course-pager panel-lite">
        <div class="pager-row">
          <div class="pager-info">
            <strong>{{ isCustomCompareMode ? "自定义对比课程" : "当前课程组" }}</strong>
            <p class="muted pager-desc" v-if="isCustomCompareMode">
              当前按课程 ID 自定义对比：{{ visibleCourseIdsText }}
            </p>
            <p class="muted pager-desc" v-else>
              当前第 {{ coursePage }} / {{ totalCoursePages }} 组
              (课程 ID {{ visibleCourseStartId }} - {{ visibleCourseEndId }})
            </p>
            <p class="muted pager-desc">当前课程：{{ visibleCourseNamesText }}</p>
          </div>

          <div class="pager-actions">
            <label class="control-group">
              <span>每组显示</span>
              <select v-model.number="coursePageSize" class="page-select page-size-select">
                <option v-for="size in coursePageSizeOptions" :key="size" :value="size">
                  {{ size }} 门
                </option>
              </select>
            </label>

            <label class="control-group course-id-group">
              <span>对比课程 ID</span>
              <input
                v-model="customCourseIdsInput"
                class="course-id-input"
                type="text"
                placeholder="例如 3,8,11"
                @keydown.enter.prevent="applyCustomCompare"
              />
            </label>

            <button class="btn btn-primary" @click="applyCustomCompare">应用对比</button>
            <button class="btn" :disabled="!isCustomCompareMode" @click="clearCustomCompare">恢复分页</button>
            <button
              v-if="!isCustomCompareMode"
              class="btn"
              :disabled="coursePage <= 1"
              @click="prevCoursePage"
            >
              上一组
            </button>
            <button
              v-if="!isCustomCompareMode"
              class="btn"
              :disabled="coursePage >= totalCoursePages"
              @click="nextCoursePage"
            >
              下一组
            </button>
            <select
              v-if="!isCustomCompareMode"
              v-model.number="coursePage"
              class="page-select"
            >
              <option v-for="item in coursePageOptions" :key="item.page" :value="item.page">
                {{ item.label }}
              </option>
            </select>
          </div>
        </div>
        <p v-if="customCompareHint" class="muted pager-desc">{{ customCompareHint }}</p>
      </section>

      <div class="charts-grid">
        <div class="chart-card">
          <h3>{{ isStudent ? "各课程学习进度" : "课程选修人数分布" }}</h3>
          <v-chart class="chart" :option="barChartOption" autoresize />
        </div>

        <div class="chart-card">
          <h3>{{ isStudent ? "各课程已学数量分布" : "课程综合评分对比" }}</h3>
          <v-chart class="chart chart-pie" :option="pieChartOption" autoresize />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import http from "../api/http";

import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

const DEFAULT_COURSE_PAGE_SIZE = 8;
const MAX_CUSTOM_COMPARE_COUNT = 8;

const loading = ref(true);
const error = ref("");
const data = ref({});
const advice = ref(null);
const coursePage = ref(1);
const coursePageSize = ref(DEFAULT_COURSE_PAGE_SIZE);
const customCourseIdsInput = ref("");
const customCourseIds = ref([]);
const customCompareHint = ref("");

const router = useRouter();

const coursePageSizeOptions = [4, 6, 8, 10, 12];

const isStudent = computed(() => data.value?.role === "student");
const isAdmin = computed(() => data.value?.role === "admin");
const isCustomCompareMode = computed(() => customCourseIds.value.length > 0);
const showCourseControls = computed(() => allCourseNames.value.length > 1);

const subtitleText = computed(() => {
  if (isAdmin.value) return "全课程选修评分信息";
  if (isStudent.value) return "查看各课程学习进度与已学课件分布";
  return "查看已发布课程的选修人数与综合评分";
});

const allCourseNames = computed(() => data.value?.courseNames || []);
const allCourseIds = computed(() => data.value?.courseIds || []);
const allEnrollCounts = computed(() => data.value?.enrollCounts || []);
const allReviewAverages = computed(() => data.value?.reviewAverages || []);
const allProgressRates = computed(() => data.value?.progressRates || []);
const allCompletedCounts = computed(() => data.value?.completedCounts || []);
const adviceStats = computed(() => advice.value?.stats || []);
const adviceRecommendations = computed(() => advice.value?.recommendations || []);
const advicePanelTitle = computed(() => {
  const role = advice.value?.role;
  if (role === "teacher") return "智能教学建议";
  if (role === "admin") return "智能运营建议";
  return "智能学习建议";
});

const courseRecords = computed(() =>
  allCourseNames.value.map((name, index) => ({
    id: allCourseIds.value[index],
    label: allCourseIds.value[index] ? `${name} (${allCourseIds.value[index]})` : name,
    name,
    enrollCount: allEnrollCounts.value[index] || 0,
    reviewAverage: allReviewAverages.value[index] || 0,
    progressRate: allProgressRates.value[index] || 0,
    completedCount: allCompletedCounts.value[index] || 0,
  })),
);

const totalCoursePages = computed(() => {
  return Math.max(1, Math.ceil(allCourseNames.value.length / coursePageSize.value));
});

const courseSliceStart = computed(() => {
  return (coursePage.value - 1) * coursePageSize.value;
});

const courseSliceEnd = computed(() => {
  return courseSliceStart.value + coursePageSize.value;
});

const visibleRecords = computed(() => {
  if (isCustomCompareMode.value) {
    return customCourseIds.value
      .map((id) => courseRecords.value.find((record) => Number(record.id) === id))
      .filter(Boolean);
  }

  return courseRecords.value.slice(courseSliceStart.value, courseSliceEnd.value);
});

const visibleCourseLabels = computed(() => visibleRecords.value.map((record) => record.label));
const visibleCourseIds = computed(() => visibleRecords.value.map((record) => record.id));
const visibleEnrollCounts = computed(() => visibleRecords.value.map((record) => record.enrollCount));
const visibleReviewAverages = computed(() => visibleRecords.value.map((record) => record.reviewAverage));
const visibleProgressRates = computed(() => visibleRecords.value.map((record) => record.progressRate));
const visibleCompletedCounts = computed(() => visibleRecords.value.map((record) => record.completedCount));

const visibleCourseStartId = computed(() => {
  if (!visibleCourseIds.value.length) return "-";
  return visibleCourseIds.value[0];
});

const visibleCourseEndId = computed(() => {
  if (!visibleCourseIds.value.length) return "-";
  return visibleCourseIds.value[visibleCourseIds.value.length - 1];
});

const visibleCourseNamesText = computed(() => {
  if (!visibleCourseLabels.value.length) return "暂无课程";
  return visibleCourseLabels.value.join("、");
});

const visibleCourseIdsText = computed(() => {
  if (!visibleCourseIds.value.length) return "未匹配到课程";
  return visibleCourseIds.value.join(", ");
});

const coursePageOptions = computed(() => {
  const result = [];
  for (let page = 1; page <= totalCoursePages.value; page += 1) {
    const start = (page - 1) * coursePageSize.value;
    const end = start + coursePageSize.value;
    const ids = allCourseIds.value.slice(start, end);
    const startId = ids[0] ?? "-";
    const endId = ids[ids.length - 1] ?? "-";
    result.push({
      page,
      label: `第 ${page} 组 (课程 ID ${startId} - ${endId})`,
    });
  }
  return result;
});

watch(coursePageSize, () => {
  coursePage.value = 1;
});

// 返回首页。
function goHome() {
  router.push("/");
}

function openAdviceAction(path) {
  if (!path) return;
  router.push(path);
}

// 切到上一组课程。
function prevCoursePage() {
  if (coursePage.value > 1) coursePage.value -= 1;
}

// 切到下一组课程。
function nextCoursePage() {
  if (coursePage.value < totalCoursePages.value) coursePage.value += 1;
}

// 应用课程 ID 自定义对比，只保留当前存在的课程。
function applyCustomCompare() {
  const ids = Array.from(
    new Set(
      customCourseIdsInput.value
        .split(/[，,\s]+/)
        .map((item) => Number(item.trim()))
        .filter((item) => Number.isInteger(item) && item > 0),
    ),
  );

  if (!ids.length) {
    customCourseIds.value = [];
    customCompareHint.value = "";
    return;
  }

  const existingIdSet = new Set(allCourseIds.value.map((id) => Number(id)));
  const validIds = ids.filter((id) => existingIdSet.has(id));
  const invalidIds = ids.filter((id) => !existingIdSet.has(id));
  const limitedValidIds = validIds.slice(0, MAX_CUSTOM_COMPARE_COUNT);

  customCourseIds.value = limitedValidIds;
  coursePage.value = 1;

  if (!limitedValidIds.length) {
    customCompareHint.value = "未匹配到可对比的课程 ID，请检查输入。";
    return;
  }

  const hints = [];
  if (validIds.length > MAX_CUSTOM_COMPARE_COUNT) {
    hints.push(`最多只保留前 ${MAX_CUSTOM_COMPARE_COUNT} 门课程进行对比`);
  }
  if (invalidIds.length) {
    hints.push(`已忽略不存在的课程 ID：${invalidIds.join(", ")}`);
  }
  customCompareHint.value = hints.join("；");
}

// 清空自定义对比，恢复分页模式。
function clearCustomCompare() {
  customCourseIdsInput.value = "";
  customCourseIds.value = [];
  customCompareHint.value = "";
  coursePage.value = 1;
}

// 页面进入后按角色加载学生/教师/管理员对应的数据总览。
onMounted(async () => {
  try {
    const meRes = await http.get("/users/me");
    const role = meRes.data?.data?.role;
    const endpoint = role === "admin" ? "/admin/analytics" : "/users/analytics";
    const [analyticsRes, adviceRes] = await Promise.all([
      http.get(endpoint),
      http.get("/users/learning-advice").catch(() => null),
    ]);
    data.value = analyticsRes.data.data || {};
    advice.value = adviceRes?.data?.data || null;
    coursePage.value = 1;
  } catch (e) {
    error.value = e?.response?.data?.message || "加载数据总览失败";
  } finally {
    loading.value = false;
  }
});

// 学生端看课程学习进度，教师/管理员看课程选修人数。
const barChartOption = computed(() => {
  if (isStudent.value) {
    return {
      tooltip: { formatter: "{b}: {c}%" },
      grid: { left: 40, right: 20, top: 20, bottom: 70, containLabel: true },
      xAxis: {
        type: "category",
        data: visibleCourseLabels.value,
        axisLabel: {
          interval: 0,
          rotate: 28,
        },
      },
      yAxis: { type: "value", max: 100 },
      series: [
        {
          data: visibleProgressRates.value,
          type: "bar",
          itemStyle: { color: "#0ea5e9" },
          barWidth: "40%",
        },
      ],
    };
  }

  return {
    tooltip: { formatter: "{b}: {c} 人" },
    grid: { left: 40, right: 20, top: 20, bottom: 78, containLabel: true },
    xAxis: {
      type: "category",
      data: visibleCourseLabels.value,
      axisLabel: {
        interval: 0,
        rotate: 28,
      },
    },
    yAxis: { type: "value" },
    series: [
      {
        data: visibleEnrollCounts.value,
        type: "bar",
        itemStyle: { color: "#10b981" },
        barWidth: "40%",
      },
    ],
  };
});

// 学生端第二张图展示各课程已学课件数量分布；教师/管理员展示课程评分。
const pieChartOption = computed(() => {
  if (isStudent.value) {
    const pieData = visibleCourseLabels.value.map((name, index) => ({
      name,
      value: visibleCompletedCounts.value[index] || 0,
    }));

    return {
      tooltip: { trigger: "item", formatter: "{b}: 已学 {c} 个课件，占已学总量 {d}%" },
      legend: {
        bottom: 0,
        left: "center",
        itemGap: 12,
        textStyle: {
          width: 130,
          overflow: "truncate",
        },
      },
      series: [
        {
          name: "已学课件数",
          type: "pie",
          radius: "44%",
          center: ["50%", "36%"],
          data: pieData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: "rgba(0, 0, 0, 0.5)",
            },
          },
        },
      ],
    };
  }

  const pieData = visibleCourseLabels.value.map((name, index) => ({
    name,
    value: visibleReviewAverages.value[index] || 0,
  }));

  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} 分" },
    legend: {
      bottom: 0,
      left: "center",
      itemGap: 12,
      formatter(name) {
        const matched = pieData.find((item) => item.name === name);
        if (!matched) return name;
        return `${name} ${matched.value}分`;
      },
      textStyle: {
        width: 180,
        overflow: "break",
        lineHeight: 16,
      },
    },
    series: [
      {
        name: "课程评分",
        type: "pie",
        radius: ["26%", "48%"],
        center: ["50%", "33%"],
        itemStyle: {
          borderRadius: 10,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter(params) {
            return `${params.name}\n${params.value}分`;
          },
          fontWeight: 700,
          lineHeight: 18,
        },
        labelLine: {
          show: true,
          length: 12,
          length2: 10,
        },
        data: pieData,
      },
    ],
  };
});
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
  flex-direction: column;
  align-items: stretch;
  gap: 16px;
}

.pager-info {
  width: 100%;
  min-width: 0;
}

.pager-desc {
  margin: 6px 0 0;
  line-height: 1.6;
  word-break: break-word;
}

.pager-actions {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  width: 100%;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}

.course-id-group {
  min-width: 220px;
}

.page-select,
.course-id-input {
  min-width: 180px;
  border: 1px solid #d0d7de;
  background: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  font-weight: 600;
  color: var(--text);
  font-family: inherit;
}

.page-size-select {
  min-width: 110px;
}

.advice-panel {
  background: linear-gradient(145deg, #fffdf3 0%, #ffffff 58%, #f4fbff 100%);
  border: 2px solid var(--border);
  border-radius: 16px;
  box-shadow: 6px 6px 0 rgba(0, 0, 0, 0.08);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.advice-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.advice-kicker {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #0f766e;
  text-transform: uppercase;
}

.advice-header .advice-kicker:first-of-type {
  display: none;
}

.advice-title {
  margin: 0;
  font-size: 1.6rem;
  color: var(--text);
}

.advice-summary {
  margin: 0.6rem 0 0;
  max-width: 860px;
}

.advice-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.9rem;
  margin-bottom: 1.2rem;
}

.advice-stat {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 14px;
  padding: 0.95rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.advice-stat-label {
  font-size: 0.9rem;
  color: #52606d;
}

.advice-stat-value {
  font-size: 1.25rem;
  color: var(--text);
}

.advice-body {
  display: grid;
  grid-template-columns: minmax(260px, 360px) minmax(0, 1fr);
  gap: 1rem;
}

.advice-focus-card,
.advice-item {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 16px;
  padding: 1rem 1.1rem;
}

.advice-focus-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.28rem 0.72rem;
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
  font-size: 0.82rem;
  font-weight: 700;
}

.advice-focus-card h3,
.advice-item h3 {
  margin: 0.8rem 0 0.5rem;
  color: var(--text);
}

.advice-focus-card p,
.advice-item p {
  margin: 0 0 1rem;
  color: #52606d;
  line-height: 1.65;
}

.advice-list {
  display: grid;
  gap: 0.85rem;
}

.advice-item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
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
  height: 480px;
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

.btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.btn-primary:hover {
  background: #1d4ed8;
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
  .page-select,
  .course-id-input {
    width: 100%;
  }

  .course-id-group {
    min-width: 100%;
  }

  .advice-body {
    grid-template-columns: 1fr;
  }

  .advice-item {
    flex-direction: column;
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
