<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { marked } from 'marked'
import {
  generateRiskIntervention,
  getDifyStatus,
  getRiskEmployeeDetail,
  getRiskEmployees,
  getRiskOverview,
} from '../api'

marked.setOptions({
  breaks: true,
  gfm: true,
})

const STORAGE_KEYS = {
  detail: 'risk-module-detail',
  step: 'risk-module-step',
}

const currentStep = ref('overview')
const selectedLevel = ref('全部')
const keywordDraft = ref('')
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const overviewLoading = ref(true)
const listLoading = ref(false)
const detailLoading = ref(false)
const interventionLoading = ref(false)
const error = ref('')
const interventionError = ref('')
const interventionResult = ref('')
const difyConfigured = ref(false)
const loadingStage = ref('')
const loadingSeconds = ref(0)

let loadingTimer = null
let secondsTimer = null

const overviewData = ref({
  summary: {
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    departments: 0,
    highPriority: 0,
    lastUpdated: '',
  },
  riskDistribution: [],
  priorityDistribution: [],
  focusEmployees: [],
  departmentDistribution: [],
  reasonDistribution: [],
})

const listData = ref({
  total: 0,
  page: 1,
  pageSize: 10,
  totalPages: 1,
  keyword: '',
  items: [],
})

const detailData = ref(null)

function saveCurrentStep(step) {
  window.sessionStorage.setItem(STORAGE_KEYS.step, step)
}

function saveDetailData(detail) {
  if (!detail) return
  window.sessionStorage.setItem(STORAGE_KEYS.detail, JSON.stringify(detail))
}

function restoreDetailData() {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEYS.detail)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function openStoredDetail() {
  if (!detailData.value) return
  currentStep.value = 'detail'
  saveCurrentStep('detail')
}

const donutStyle = computed(() => buildDonutStyle(overviewData.value.riskDistribution))
const priorityDonutStyle = computed(() => buildDonutStyle(overviewData.value.priorityDistribution))

const pageNumbers = computed(() => {
  const totalPages = listData.value.totalPages || 1
  const current = listData.value.page || 1
  const start = Math.max(1, current - 2)
  const end = Math.min(totalPages, start + 4)
  const pages = []
  for (let page = start; page <= end; page += 1) {
    pages.push(page)
  }
  return pages
})

const listSummaryText = computed(() => {
  if (!listData.value.total) return '当前没有符合条件的员工'
  const start = (listData.value.page - 1) * listData.value.pageSize + 1
  const end = Math.min(start + listData.value.items.length - 1, listData.value.total)
  return `当前显示 ${start}-${end} / ${listData.value.total}`
})

function renderMarkdown(text) {
  if (!text) return ''
  const clean = text.replace(/<think>[\s\S]*?<\/think>/g, '')
  return marked.parse(clean)
}

function riskClass(level) {
  if (!level) return 'risk-low'
  if (level.includes('高')) return 'risk-high'
  if (level.includes('中')) return 'risk-mid'
  return 'risk-low'
}

function priorityLabel(level) {
  return level === 'high' ? '高优先级' : '常规跟进'
}

function buildDonutStyle(items) {
  const total = items.reduce((sum, item) => sum + (item.value || 0), 0)
  if (!total) {
    return {
      background: 'conic-gradient(#e2e8f0 0deg 360deg)',
    }
  }

  let start = 0
  const segments = items.map((item) => {
    const angle = ((item.value || 0) / total) * 360
    const end = start + angle
    const segment = `${item.color} ${start}deg ${end}deg`
    start = end
    return segment
  })

  return {
    background: `conic-gradient(${segments.join(', ')})`,
  }
}

function resetListState() {
  keywordDraft.value = ''
  keyword.value = ''
  currentPage.value = 1
  pageSize.value = 10
}

async function loadDifyStatus() {
  try {
    const result = await getDifyStatus()
    difyConfigured.value = !!result.configured
  } catch {
    difyConfigured.value = false
  }
}

async function loadOverview() {
  overviewLoading.value = true
  error.value = ''

  try {
    overviewData.value = await getRiskOverview()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '风险总览加载失败'
  } finally {
    overviewLoading.value = false
  }
}

async function loadRiskList() {
  listLoading.value = true
  error.value = ''

  try {
    listData.value = await getRiskEmployees({
      level: selectedLevel.value,
      keyword: keyword.value,
      page: currentPage.value,
      pageSize: pageSize.value,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '风险名单加载失败'
  } finally {
    listLoading.value = false
  }
}

async function openList(level = '全部') {
  selectedLevel.value = level
  resetListState()
  currentStep.value = 'list'
  saveCurrentStep('list')
  await loadRiskList()
}

async function openDetail(item) {
  if (!item?.employeeId) return

  currentStep.value = 'detail'
  detailLoading.value = true
  detailData.value = null
  interventionResult.value = ''
  interventionError.value = ''
  error.value = ''

  try {
    detailData.value = await getRiskEmployeeDetail(item.employeeId)
    saveDetailData(detailData.value)
    saveCurrentStep('detail')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '员工风险详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

function backToOverview() {
  currentStep.value = 'overview'
  saveCurrentStep('overview')
}

function backToList() {
  currentStep.value = 'list'
  saveCurrentStep('list')
}

async function onLevelChange() {
  currentPage.value = 1
  await loadRiskList()
}

async function applyKeywordSearch() {
  keyword.value = keywordDraft.value.trim()
  currentPage.value = 1
  await loadRiskList()
}

async function resetFilters() {
  selectedLevel.value = '全部'
  resetListState()
  await loadRiskList()
}

async function changePage(page) {
  if (page < 1 || page > listData.value.totalPages || page === currentPage.value) return
  currentPage.value = page
  await loadRiskList()
}

async function onPageSizeChange() {
  currentPage.value = 1
  await loadRiskList()
}

function startLoadingFeedback() {
  stopLoadingFeedback()
  loadingStage.value = '正在整理员工画像并检查输入字段...'
  loadingSeconds.value = 0

  secondsTimer = window.setInterval(() => {
    loadingSeconds.value += 1
  }, 1000)

  loadingTimer = window.setInterval(() => {
    const seconds = loadingSeconds.value
    if (seconds >= 8) {
      loadingStage.value = '结果内容较长，模型仍在生成，请再稍候...'
    } else if (seconds >= 4) {
      loadingStage.value = '正在调用大模型生成干预方案...'
    } else if (seconds >= 2) {
      loadingStage.value = '正在分析风险因素并组织建议结构...'
    }
  }, 500)
}

function stopLoadingFeedback() {
  if (loadingTimer) {
    window.clearInterval(loadingTimer)
    loadingTimer = null
  }
  if (secondsTimer) {
    window.clearInterval(secondsTimer)
    secondsTimer = null
  }
}

async function generatePlan() {
  if (!detailData.value?.employeeInput || interventionLoading.value) return

  interventionLoading.value = true
  interventionError.value = ''
  interventionResult.value = ''
  startLoadingFeedback()

  try {
    const result = await generateRiskIntervention({
      employeeInput: detailData.value.employeeInput,
      analysisMode: 'single',
      highRiskThreshold: 70,
      mediumRiskThreshold: 40,
      user: 'risk-module',
    })
    interventionResult.value = result.answer || ''
  } catch (err) {
    interventionError.value = err instanceof Error ? err.message : '干预方案生成失败'
  } finally {
    stopLoadingFeedback()
    interventionLoading.value = false
  }
}

onMounted(async () => {
  detailData.value = restoreDetailData()
  const savedStep = window.sessionStorage.getItem(STORAGE_KEYS.step)
  if (savedStep === 'detail' && detailData.value) {
    currentStep.value = 'detail'
  }
  await Promise.all([loadOverview(), loadDifyStatus()])
})

onBeforeUnmount(() => {
  stopLoadingFeedback()
})
</script>

<template>
  <div class="risk-module">
    <div class="risk-subnav panel">
      <button
        type="button"
        class="subnav-btn"
        :class="{ active: currentStep === 'overview' }"
        @click="backToOverview"
      >
        风险总览
      </button>
      <button
        type="button"
        class="subnav-btn"
        :class="{ active: currentStep === 'list' }"
        @click="openList()"
      >
        风险名单
      </button>
      <button
        type="button"
        class="subnav-btn"
        :class="{ active: currentStep === 'detail' }"
        :disabled="!detailData"
        @click="openStoredDetail"
      >
        员工详情
      </button>
    </div>

    <section v-if="overviewLoading && currentStep === 'overview'" class="panel loading-state">
      风险总览加载中...
    </section>
    <section v-else-if="error && currentStep !== 'detail'" class="panel error">
      {{ error }}
    </section>

    <template v-else>
      <template v-if="currentStep === 'overview'">
        <section class="kpi-grid">
          <article class="kpi-card accent-high">
            <p>高风险员工</p>
            <h3>{{ overviewData.summary.high }}</h3>
            <button type="button" class="link-action" @click="openList('高风险')">查看名单</button>
          </article>
          <article class="kpi-card accent-mid">
            <p>中风险员工</p>
            <h3>{{ overviewData.summary.medium }}</h3>
            <button type="button" class="link-action" @click="openList('中风险')">查看名单</button>
          </article>
          <article class="kpi-card">
            <p>预警总人数</p>
            <h3>{{ overviewData.summary.total }}</h3>
            <button type="button" class="link-action" @click="openList()">查看全部</button>
          </article>
          <article class="kpi-card">
            <p>高优先级干预</p>
            <h3>{{ overviewData.summary.highPriority }}</h3>
            <span class="card-note">优先处理高风险或高价值中风险员工</span>
          </article>
        </section>

        <section class="chart-grid">
          <article class="panel chart-card">
            <div class="section-head">
              <div>
                <h2>风险等级分布</h2>
                <p class="section-desc">更直观看当前高、中、低风险结构。</p>
              </div>
            </div>
            <div class="donut-layout">
              <div class="donut-ring" :style="donutStyle">
                <div class="donut-inner">
                  <strong>{{ overviewData.summary.total }}</strong>
                  <span>总人数</span>
                </div>
              </div>
              <div class="legend-list">
                <div v-for="item in overviewData.riskDistribution" :key="item.label" class="legend-item">
                  <span class="legend-dot" :style="{ background: item.color }"></span>
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
            </div>
          </article>

          <article class="panel chart-card">
            <div class="section-head">
              <div>
                <h2>部门风险分布</h2>
                <p class="section-desc">帮助你快速看到风险更集中的部门。</p>
              </div>
            </div>
            <div class="bar-list">
              <div
                v-for="item in overviewData.departmentDistribution"
                :key="item.department"
                class="bar-item"
              >
                <div class="bar-head">
                  <span>{{ item.department }}</span>
                  <strong>{{ item.count }} 人</strong>
                </div>
                <div class="bar-track">
                  <div
                    class="bar-fill teal"
                    :style="{ width: `${Math.max((item.count / Math.max(overviewData.summary.total, 1)) * 100, 8)}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </article>

          <article class="panel chart-card">
            <div class="section-head">
              <div>
                <h2>高优先级占比</h2>
                <p class="section-desc">展示真正需要优先处理的对象比例。</p>
              </div>
            </div>
            <div class="donut-layout compact-donut">
              <div class="donut-ring small" :style="priorityDonutStyle">
                <div class="donut-inner">
                  <strong>{{ overviewData.summary.highPriority }}</strong>
                  <span>高优先级</span>
                </div>
              </div>
              <div class="legend-list">
                <div v-for="item in overviewData.priorityDistribution" :key="item.label" class="legend-item">
                  <span class="legend-dot" :style="{ background: item.color }"></span>
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section class="double-grid">
          <article class="panel">
            <div class="section-head">
              <div>
                <h2>重点预警员工</h2>
                <p class="section-desc">优先展示当前最值得人工关注的员工。</p>
              </div>
              <button type="button" class="primary-btn" @click="openList()">进入风险名单</button>
            </div>

            <div class="focus-grid">
              <article
                v-for="item in overviewData.focusEmployees"
                :key="item.employeeId"
                class="focus-card"
              >
                <div class="focus-top">
                  <div>
                    <h3>{{ item.employee }}</h3>
                    <p>{{ item.department }} / {{ item.positionName }}</p>
                  </div>
                  <span :class="['risk-badge', riskClass(item.riskLevel)]">{{ item.riskLevel }}</span>
                </div>

                <div class="tag-row">
                  <span v-for="tag in item.reasonTags" :key="tag" class="reason-tag">{{ tag }}</span>
                </div>

                <div class="meta-row">
                  <span>风险分 {{ item.riskScore }}</span>
                  <span>{{ priorityLabel(item.priorityLevel) }}</span>
                </div>

                <p class="focus-action">{{ item.action }}</p>

                <button type="button" class="ghost-btn" @click="openDetail(item)">查看员工详情</button>
              </article>
            </div>
          </article>

          <article class="panel">
            <div class="section-head">
              <div>
                <h2>风险原因 TOP</h2>
                <p class="section-desc">帮助你快速判断当前风险的主要来源。</p>
              </div>
            </div>

            <div class="bar-list">
              <div
                v-for="item in overviewData.reasonDistribution"
                :key="item.label"
                class="bar-item"
              >
                <div class="bar-head">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.count }}</strong>
                </div>
                <div class="bar-track">
                  <div
                    class="bar-fill orange"
                    :style="{ width: `${Math.max((item.count / Math.max(overviewData.summary.total, 1)) * 100, 8)}%` }"
                  ></div>
                </div>
              </div>
            </div>

            <div class="summary-note">
              涉及部门数：{{ overviewData.summary.departments }} 个
              <span v-if="overviewData.summary.lastUpdated">
                · 更新日期：{{ overviewData.summary.lastUpdated }}
              </span>
            </div>
          </article>
        </section>
      </template>

      <template v-else-if="currentStep === 'list'">
        <section class="panel">
          <div class="section-head list-head">
            <div>
              <h2>风险名单</h2>
              <p class="section-desc">支持搜索、风险等级筛选和分页浏览。</p>
            </div>
            <button type="button" class="ghost-btn" @click="backToOverview">返回总览</button>
          </div>

          <div class="toolbar rich-toolbar">
            <label class="toolbar-label grow">
              关键词搜索
              <input
                v-model="keywordDraft"
                class="toolbar-input"
                type="text"
                placeholder="输入姓名、工号、部门或岗位"
                @keyup.enter="applyKeywordSearch"
              />
            </label>

            <label class="toolbar-label">
              风险等级
              <select v-model="selectedLevel" class="toolbar-select" @change="onLevelChange">
                <option>全部</option>
                <option>高风险</option>
                <option>中风险</option>
                <option>低风险</option>
              </select>
            </label>

            <label class="toolbar-label">
              每页条数
              <select v-model="pageSize" class="toolbar-select" @change="onPageSizeChange">
                <option :value="5">5</option>
                <option :value="10">10</option>
                <option :value="15">15</option>
              </select>
            </label>

            <button type="button" class="primary-btn" @click="applyKeywordSearch">搜索</button>
            <button type="button" class="ghost-btn" @click="resetFilters">重置</button>
          </div>

          <section v-if="listLoading" class="loading-state">风险名单加载中...</section>
          <section v-else-if="error" class="error">{{ error }}</section>
          <template v-else>
            <div class="summary-strip">
              {{ listSummaryText }}
              <span v-if="keyword"> · 当前关键词：{{ keyword }}</span>
              <span v-if="selectedLevel !== '全部'"> · 当前等级：{{ selectedLevel }}</span>
            </div>

            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>员工</th>
                    <th>部门 / 岗位</th>
                    <th>风险等级</th>
                    <th>风险分</th>
                    <th>优先级</th>
                    <th>主要原因</th>
                    <th>建议动作</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in listData.items" :key="item.employeeId">
                    <td>{{ item.employee }}</td>
                    <td>{{ item.department }} / {{ item.positionName }}</td>
                    <td>
                      <span :class="['risk-badge', riskClass(item.riskLevel)]">{{ item.riskLevel }}</span>
                    </td>
                    <td>{{ item.riskScore }}</td>
                    <td>{{ priorityLabel(item.priorityLevel) }}</td>
                    <td>{{ item.reason }}</td>
                    <td>{{ item.action }}</td>
                    <td>
                      <button type="button" class="mini-btn" @click="openDetail(item)">查看详情</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="pagination">
              <button type="button" class="ghost-btn" :disabled="listData.page <= 1" @click="changePage(listData.page - 1)">
                上一页
              </button>
              <button
                v-for="page in pageNumbers"
                :key="page"
                type="button"
                class="page-btn"
                :class="{ active: page === listData.page }"
                @click="changePage(page)"
              >
                {{ page }}
              </button>
              <button
                type="button"
                class="ghost-btn"
                :disabled="listData.page >= listData.totalPages"
                @click="changePage(listData.page + 1)"
              >
                下一页
              </button>
            </div>
          </template>
        </section>
      </template>

      <template v-else-if="currentStep === 'detail'">
        <section v-if="detailLoading" class="panel loading-state">员工风险详情加载中...</section>
        <section v-else-if="error" class="panel error">{{ error }}</section>
        <template v-else-if="detailData">
          <section class="panel detail-hero">
            <div>
              <p class="detail-label">员工风险详情</p>
              <h2>{{ detailData.employee }}</h2>
              <p class="detail-sub">
                {{ detailData.department }} / {{ detailData.positionName }} / {{ detailData.jobLevel || '未标注职级层级' }}
              </p>
            </div>
            <div class="hero-right">
              <span :class="['risk-badge', 'large', riskClass(detailData.riskLevel)]">
                {{ detailData.riskLevel }}
              </span>
              <span class="priority-badge">{{ priorityLabel(detailData.priorityLevel) }}</span>
            </div>
          </section>

          <section class="detail-grid">
            <article class="panel">
              <h2>风险分析</h2>
              <div class="tag-row">
                <span v-for="tag in detailData.reasonTags" :key="tag" class="reason-tag">{{ tag }}</span>
              </div>
              <p class="detail-text">{{ detailData.summary }}</p>
              <div class="metric-list">
                <div class="metric-item">
                  <span>风险分</span>
                  <strong>{{ detailData.riskScore }}</strong>
                </div>
                <div class="metric-item">
                  <span>绩效评分</span>
                  <strong>{{ detailData.assessment.performanceScore }}</strong>
                </div>
                <div class="metric-item">
                  <span>潜力评分</span>
                  <strong>{{ detailData.assessment.potentialScore }}</strong>
                </div>
              </div>
            </article>

            <article class="panel">
              <h2>员工画像</h2>
              <div class="info-list">
                <div><span>工号</span><strong>{{ detailData.employeeId }}</strong></div>
                <div><span>职级</span><strong>{{ detailData.rankName || '--' }}</strong></div>
                <div><span>司龄</span><strong>{{ detailData.profile.tenureYears }} 年</strong></div>
                <div><span>办公方式</span><strong>{{ detailData.profile.workMode || '--' }}</strong></div>
                <div><span>人才标签</span><strong>{{ detailData.profile.talentTag || '--' }}</strong></div>
                <div><span>薪酬系数</span><strong>{{ detailData.profile.compensationFactor }}</strong></div>
              </div>
            </article>

            <article class="panel">
              <h2>发展与梯队信息</h2>
              <div class="tag-block">
                <p class="block-title">已完成培训</p>
                <div class="tag-row">
                  <span
                    v-for="tag in detailData.development.trainingCompleted"
                    :key="tag"
                    class="reason-tag"
                  >
                    {{ tag }}
                  </span>
                  <span v-if="detailData.development.trainingCompleted.length === 0" class="empty-text">
                    暂无记录
                  </span>
                </div>
              </div>

              <div class="tag-block">
                <p class="block-title">待补培训</p>
                <div class="tag-row">
                  <span
                    v-for="tag in detailData.development.missingTraining"
                    :key="tag"
                    class="reason-tag missing-tag"
                  >
                    {{ tag }}
                  </span>
                  <span v-if="detailData.development.missingTraining.length === 0" class="empty-text">
                    当前无明显培训缺口
                  </span>
                </div>
              </div>

              <div class="info-list compact">
                <div><span>关键岗位</span><strong>{{ detailData.positionRisk.isKeyPosition ? '是' : '否' }}</strong></div>
                <div><span>岗位风险</span><strong>{{ detailData.positionRisk.positionRiskLevel }}</strong></div>
                <div><span>继任候选</span><strong>{{ detailData.succession.isCandidate ? '是' : '否' }}</strong></div>
                <div><span>继任层级</span><strong>{{ detailData.succession.successionLevel }}</strong></div>
              </div>
            </article>

            <article class="panel suggestion-panel">
              <div class="section-head compact-head">
                <div>
                  <h2>建议措施</h2>
                  <p class="section-desc">先看系统建议，再按需生成更完整的 AI 干预方案。</p>
                </div>
              </div>

              <ol class="action-list polished-list">
                <li v-for="action in detailData.recommendedActions" :key="action">
                  <span class="action-index"></span>
                  <span>{{ action }}</span>
                </li>
              </ol>

              <div class="ai-capability-box">
                <div class="ai-capability-head">
                  <div>
                    <p class="capability-eyebrow">AI 深度分析</p>
                    <h3>可进一步生成个性化干预方案</h3>
                  </div>
                  <div class="capability-glow"></div>
                </div>

                <p class="capability-copy">
                  点击下方按钮后，系统会结合该员工的风险等级、岗位背景和发展信息，补充更细的沟通策略与跟进建议。
                </p>

                <div class="capability-tags">
                  <span class="capability-tag">沟通话术建议</span>
                  <span class="capability-tag">跟进周期建议</span>
                  <span class="capability-tag">责任人建议</span>
                  <span class="capability-tag">保留动作补充</span>
                </div>
              </div>
            </article>
          </section>

          <section class="panel detail-actions">
            <button type="button" class="ghost-btn" @click="backToList">返回风险名单</button>
            <button
              type="button"
              class="primary-btn"
              :disabled="interventionLoading || !difyConfigured"
              @click="generatePlan"
            >
              {{ interventionLoading ? '正在生成...' : '生成干预方案' }}
            </button>
          </section>

          <section v-if="!difyConfigured" class="panel warning-box">
            尚未配置 Dify API Key。请先在本地完成配置，再点击“生成干预方案”。
          </section>

          <section v-if="interventionLoading" class="panel progress-panel">
            <div class="progress-top">
              <strong>AI 正在生成干预方案</strong>
              <span>{{ loadingSeconds }}s</span>
            </div>
            <p class="progress-text">{{ loadingStage }}</p>
            <div class="progress-bar">
              <div class="progress-bar-fill"></div>
            </div>
            <div class="skeleton-group">
              <div class="skeleton-line long"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line short"></div>
            </div>
          </section>

          <section v-if="interventionError" class="panel error">
            {{ interventionError }}
          </section>

          <section v-if="interventionResult" class="panel intervention-panel">
            <div class="section-head">
              <div>
                <h2>AI 干预方案</h2>
                <p class="section-desc">以下内容来自 AI，仅供参考。</p>
              </div>
            </div>
            <div class="ai-result" v-html="renderMarkdown(interventionResult)"></div>
          </section>
        </template>
      </template>
    </template>
  </div>
</template>

<style scoped>
.risk-module {
  display: grid;
  gap: 20px;
}

.risk-subnav {
  display: flex;
  gap: 10px;
  padding: 12px;
  margin-bottom: 0;
}

.subnav-btn,
.primary-btn,
.ghost-btn,
.mini-btn,
.link-action,
.page-btn {
  border: 0;
  cursor: pointer;
  transition: all 0.2s;
  font: inherit;
}

.subnav-btn {
  padding: 10px 14px;
  border-radius: 10px;
  background: #f1f5f9;
  color: #475569;
}

.subnav-btn.active {
  background: #0f766e;
  color: #fff;
}

.subnav-btn:disabled,
.primary-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.kpi-grid,
.double-grid,
.detail-grid,
.chart-grid {
  display: grid;
  gap: 16px;
}

.kpi-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.chart-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.double-grid {
  grid-template-columns: 1.6fr 1fr;
}

.detail-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.kpi-card,
.chart-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  background: #fff;
}

.kpi-card h3 {
  margin: 10px 0 0;
  font-size: 30px;
}

.accent-high {
  border-color: #fecaca;
  background: linear-gradient(180deg, #fff 0%, #fef2f2 100%);
}

.accent-mid {
  border-color: #fed7aa;
  background: linear-gradient(180deg, #fff 0%, #fff7ed 100%);
}

.link-action {
  margin-top: 12px;
  padding: 0;
  background: transparent;
  color: #0f766e;
  font-size: 13px;
  font-weight: 600;
}

.card-note,
.section-desc,
.detail-sub,
.summary-note,
.empty-text,
.progress-text {
  color: #64748b;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-head h2,
.detail-hero h2 {
  margin: 0 0 6px;
}

.donut-layout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.donut-ring {
  width: 168px;
  height: 168px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.donut-ring.small {
  width: 140px;
  height: 140px;
}

.donut-inner {
  width: 102px;
  height: 102px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #0f172a;
  box-shadow: inset 0 0 0 1px #e2e8f0;
}

.donut-inner strong {
  font-size: 24px;
}

.donut-inner span {
  font-size: 12px;
  color: #64748b;
}

.legend-list,
.bar-list {
  display: grid;
  gap: 12px;
  width: 100%;
}

.legend-item,
.bar-head,
.progress-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 8px;
}

.bar-track,
.progress-bar {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.bar-fill,
.progress-bar-fill {
  height: 100%;
  border-radius: inherit;
}

.bar-fill.teal {
  background: linear-gradient(90deg, #0f766e, #14b8a6);
}

.bar-fill.orange {
  background: linear-gradient(90deg, #f97316, #fb923c);
}

.progress-bar-fill {
  width: 45%;
  background: linear-gradient(90deg, #0f766e, #2dd4bf);
  animation: progress-slide 1.6s ease-in-out infinite;
}

@keyframes progress-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(220%);
  }
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.focus-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 18px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.focus-top,
.detail-hero,
.detail-actions,
.toolbar,
.meta-row,
.hero-right {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.focus-top,
.detail-hero,
.detail-actions,
.toolbar {
  align-items: flex-start;
}

.focus-top h3,
.focus-top p,
.focus-action,
.detail-label,
.detail-text,
.block-title {
  margin: 0;
}

.focus-action,
.detail-text {
  color: #334155;
  line-height: 1.7;
}

.focus-action {
  margin-top: 12px;
  min-height: 54px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.reason-tag {
  padding: 5px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #334155;
  font-size: 12px;
  font-weight: 500;
}

.missing-tag {
  background: #fff7ed;
  color: #c2410c;
}

.risk-badge,
.priority-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.risk-badge {
  padding: 5px 10px;
}

.risk-badge.large {
  padding: 8px 14px;
  font-size: 14px;
}

.priority-badge {
  padding: 8px 12px;
  background: #ecfeff;
  color: #155e75;
}

.risk-high {
  color: #b91c1c;
  background: #fee2e2;
}

.risk-mid {
  color: #c2410c;
  background: #ffedd5;
}

.risk-low {
  color: #166534;
  background: #dcfce7;
}

.primary-btn,
.ghost-btn,
.mini-btn,
.page-btn {
  border-radius: 10px;
  padding: 10px 14px;
}

.primary-btn {
  background: #0f766e;
  color: #fff;
}

.ghost-btn {
  background: #fff;
  color: #0f172a;
  border: 1px solid #cbd5e1;
}

.mini-btn {
  background: #e0f2fe;
  color: #075985;
  padding: 8px 12px;
}

.page-btn {
  background: #f8fafc;
  color: #334155;
  border: 1px solid #e2e8f0;
  min-width: 40px;
}

.page-btn.active {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}

.toolbar {
  align-items: center;
}

.rich-toolbar {
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.toolbar-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 14px;
}

.toolbar-label.grow {
  flex: 1;
  min-width: 240px;
}

.toolbar-select,
.toolbar-input {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
}

.toolbar-input {
  width: 100%;
}

.summary-strip {
  margin-bottom: 14px;
  color: #475569;
  font-size: 14px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 14px 12px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  vertical-align: top;
}

th {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  background: #f8fafc;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 18px;
  flex-wrap: wrap;
}

.detail-label {
  color: #0f766e;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}

.metric-list,
.info-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.metric-list {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-item,
.info-list > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #e2e8f0;
}

.compact {
  margin-top: 18px;
}

.tag-block + .tag-block {
  margin-top: 18px;
}

.meta-row {
  margin-top: 12px;
  color: #64748b;
  font-size: 13px;
}

.action-list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  line-height: 1.8;
}

.ai-capability-box,
.warning-box,
.intervention-panel,
.progress-panel {
  margin-top: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  background: #f8fafc;
}

.warning-box {
  color: #92400e;
  background: #fffbeb;
  border-color: #fde68a;
}

.suggestion-panel {
  position: relative;
  overflow: hidden;
}

.suggestion-panel::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 4px;
  background: linear-gradient(90deg, #0f766e, #14b8a6, #67e8f9);
  opacity: 0.9;
}

.compact-head {
  margin-bottom: 12px;
}

.polished-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.polished-list li {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 12px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.action-index {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  box-shadow: 0 8px 18px rgba(20, 184, 166, 0.25);
  position: relative;
  margin-top: 2px;
}

.action-index::after {
  content: '';
  position: absolute;
  inset: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
}

.ai-capability-box {
  position: relative;
  background:
    radial-gradient(circle at top right, rgba(45, 212, 191, 0.18), transparent 32%),
    linear-gradient(180deg, #f8fffe 0%, #f8fafc 100%);
}

.ai-capability-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.capability-eyebrow {
  margin: 0 0 8px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.ai-capability-head h3 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}

.capability-copy {
  margin: 12px 0 0;
  color: #475569;
  line-height: 1.7;
}

.capability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.capability-tag {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(20, 184, 166, 0.18);
  color: #155e75;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 8px 20px rgba(148, 163, 184, 0.12);
}

.capability-glow {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0) 40%),
    linear-gradient(135deg, #0f766e, #2dd4bf);
  box-shadow: 0 16px 32px rgba(20, 184, 166, 0.22);
  flex-shrink: 0;
}

.skeleton-group {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.skeleton-line {
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(90deg, #e2e8f0 25%, #f8fafc 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.skeleton-line.long {
  width: 100%;
}

.skeleton-line.short {
  width: 60%;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.ai-result {
  color: #334155;
  line-height: 1.8;
}

.ai-result :deep(p) {
  margin: 0 0 10px;
}

.ai-result :deep(p:last-child) {
  margin-bottom: 0;
}

.ai-result :deep(h1),
.ai-result :deep(h2),
.ai-result :deep(h3) {
  margin: 16px 0 8px;
}

.ai-result :deep(ul),
.ai-result :deep(ol) {
  margin: 8px 0 10px;
  padding-left: 20px;
}

.ai-result :deep(li) {
  margin-bottom: 6px;
}

.ai-result :deep(code) {
  background: rgba(15, 118, 110, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

.loading-state,
.error {
  padding: 24px;
}

.error {
  color: #b91c1c;
}

@media (max-width: 1200px) {
  .kpi-grid,
  .chart-grid,
  .detail-grid,
  .double-grid,
  .focus-grid,
  .metric-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .risk-subnav,
  .section-head,
  .focus-top,
  .detail-hero,
  .detail-actions,
  .toolbar,
  .hero-right,
  .meta-row,
  .donut-layout {
    flex-direction: column;
    align-items: flex-start;
  }

  .donut-ring,
  .donut-ring.small {
    width: 132px;
    height: 132px;
  }
}
</style>
