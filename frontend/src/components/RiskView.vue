<script setup>
import { onMounted, ref } from 'vue'
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

const currentStep = ref('overview')
const selectedLevel = ref('全部')

const overviewLoading = ref(true)
const listLoading = ref(false)
const detailLoading = ref(false)
const interventionLoading = ref(false)
const error = ref('')
const interventionError = ref('')
const interventionResult = ref('')
const difyConfigured = ref(false)

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
  focusEmployees: [],
  departmentDistribution: [],
})

const listData = ref({
  total: 0,
  items: [],
})

const detailData = ref(null)

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

function reasonTags(value) {
  if (Array.isArray(value)) return value
  if (!value) return []
  return value
    .split('+')
    .map((item) => item.trim())
    .filter(Boolean)
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

async function loadRiskList(level = selectedLevel.value) {
  listLoading.value = true
  error.value = ''

  try {
    listData.value = await getRiskEmployees(level)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '风险名单加载失败'
  } finally {
    listLoading.value = false
  }
}

async function openList(level = '全部') {
  selectedLevel.value = level
  currentStep.value = 'list'
  await loadRiskList(level)
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
  } catch (err) {
    error.value = err instanceof Error ? err.message : '员工风险详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

function backToOverview() {
  currentStep.value = 'overview'
}

function backToList() {
  currentStep.value = 'list'
}

async function onLevelChange() {
  await loadRiskList(selectedLevel.value)
}

async function generatePlan() {
  if (!detailData.value?.employeeInput || interventionLoading.value) return

  interventionLoading.value = true
  interventionError.value = ''
  interventionResult.value = ''

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
    interventionLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadOverview(), loadDifyStatus()])
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
                  <span v-for="tag in reasonTags(item.reasonTags)" :key="tag" class="reason-tag">
                    {{ tag }}
                  </span>
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
                <h2>部门分布</h2>
                <p class="section-desc">观察风险员工目前主要集中在哪些部门。</p>
              </div>
            </div>

            <div class="department-list">
              <div
                v-for="item in overviewData.departmentDistribution"
                :key="item.department"
                class="department-row"
              >
                <span>{{ item.department }}</span>
                <strong>{{ item.count }} 人</strong>
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
              <p class="section-desc">支持按风险等级筛选，并进入单个员工的风险详情页。</p>
            </div>
            <div class="toolbar">
              <label class="toolbar-label">
                风险等级
                <select v-model="selectedLevel" class="toolbar-select" @change="onLevelChange">
                  <option>全部</option>
                  <option>高风险</option>
                  <option>中风险</option>
                  <option>低风险</option>
                </select>
              </label>
              <button type="button" class="ghost-btn" @click="backToOverview">返回总览</button>
            </div>
          </div>

          <section v-if="listLoading" class="loading-state">风险名单加载中...</section>
          <section v-else-if="error" class="error">{{ error }}</section>
          <template v-else>
            <div class="summary-strip">
              当前共 {{ listData.total }} 人
              <span v-if="selectedLevel !== '全部'"> · 筛选条件：{{ selectedLevel }}</span>
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

            <article class="panel">
              <h2>干预建议与工作流输入</h2>
              <ol class="action-list">
                <li v-for="action in detailData.recommendedActions" :key="action">{{ action }}</li>
              </ol>

              <div class="workflow-box">
                <p class="block-title">Dify 输入预览</p>
                <pre>{{ JSON.stringify(detailData.employeeInput, null, 2) }}</pre>
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

          <section v-if="interventionError" class="panel error">
            {{ interventionError }}
          </section>

          <section v-if="interventionResult" class="panel intervention-panel">
            <div class="section-head">
              <div>
                <h2>AI 干预方案</h2>
                <p class="section-desc">以下内容来自你发布的 Dify 工作流。</p>
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
.link-action {
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
.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.kpi-grid,
.double-grid,
.detail-grid {
  display: grid;
  gap: 16px;
}

.kpi-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.double-grid {
  grid-template-columns: 1.6fr 1fr;
}

.detail-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.kpi-card {
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
.empty-text {
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
.mini-btn {
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

.toolbar {
  align-items: center;
}

.toolbar-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 14px;
}

.toolbar-select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 10px;
  background: #fff;
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
.info-list > div,
.department-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.metric-item,
.info-list > div {
  padding: 10px 0;
  border-bottom: 1px solid #e2e8f0;
}

.compact {
  margin-top: 18px;
}

.tag-block + .tag-block {
  margin-top: 18px;
}

.department-list {
  display: grid;
  gap: 10px;
}

.department-row {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fafc;
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

.workflow-box,
.warning-box,
.intervention-panel {
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

.workflow-box pre {
  margin: 10px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  color: #0f172a;
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

@media (max-width: 1100px) {
  .kpi-grid,
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
  .meta-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
