<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

// ── 状态 ──
const activeTab = ref('potential')  // 'potential' | 'risk' | 'records'
const potentialList = ref([])
const sidebarWidth = ref(33)  // 默认占 33%
const isResizing = ref(false)

function startResize(e) {
  isResizing.value = true
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  e.preventDefault()
}

function onResize(e) {
  if (!isResizing.value) return
  const container = document.querySelector('.potential-layout')
  if (!container) return
  const rect = container.getBoundingClientRect()
  const newWidth = ((rect.right - e.clientX) / rect.width) * 100
  sidebarWidth.value = Math.max(20, Math.min(60, newWidth))
}

function stopResize() {
  isResizing.value = false
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})
const positionRisks = ref([])
const employeeRisks = ref([])
const assessmentRecords = ref([])
const loading = ref(true)
const error = ref('')

// 搜索
const searchQuery = ref('')

const filteredPotentialList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return potentialList.value
  return potentialList.value.filter(
    emp => emp.employee_id.toLowerCase().includes(q) || emp.name.includes(q)
  )
})

const filteredEmployeeRisks = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return employeeRisks.value
  return employeeRisks.value.filter(
    emp =>
      emp.employee_id.toLowerCase().includes(q) ||
      emp.name.includes(q) ||
      (emp.department && emp.department.includes(q))
  )
})

// 评估记录搜索
const recordsSearch = ref('')
const filteredRecords = computed(() => {
  const q = recordsSearch.value.trim().toLowerCase()
  if (!q) return assessmentRecords.value
  return assessmentRecords.value.filter(
    r => r.employee_id?.toLowerCase().includes(q) || r.name?.includes(q)
  )
})

// ── 保存评估表单弹窗 ──
const showDetailModal = ref(false)
const detailRecord = ref(null)

function viewAssessmentDetail(record) {
  detailRecord.value = record
  showDetailModal.value = true
}

function closeDetailModal() {
  showDetailModal.value = false
  detailRecord.value = null
}

// AI 聊天
const chatMessages = ref([
  {
    role: 'assistant',
    content: '您好！我是**人才分析与风险研判助手** ◈，可以帮您：\n\n' +
      '**人才潜力评估：**\n' +
      '• 对某员工进行潜力评估\n' +
      '**岗位风险研判：**\n' +
      '• 对某岗位进行风险研判\n' +
      '请问您想了解什么？'
  }
])
const userInput = ref('')
const chatLoading = ref(false)
const conversationId = ref('')
const chatBox = ref(null)

function renderMarkdown(text) {
  if (!text) return ''
  let clean = text.replace(/<think>[\s\S]*?<\/think>/g, '')
  clean = clean.replace(/^<think>.*$/gm, '')
  return marked.parse(clean)
}

// ── ECharts ──
const potentialChartRef = ref(null)
const riskPieChartRef = ref(null)

let potentialChart = null
let riskPieChart = null

function initCharts() {
  nextTick(() => {
    if (activeTab.value === 'potential') {
      renderPotentialPie()
    } else {
      renderRiskPie()
    }
  })
}

function getOrCreateChart(ref) {
  if (!ref.value) return null
  // 用 ECharts 自带的 API 检查 DOM 上是否已有实例
  let instance = echarts.getInstanceByDom(ref.value)
  if (!instance) instance = echarts.init(ref.value)
  return instance
}

function renderPotentialPie() {
  potentialChart = getOrCreateChart(potentialChartRef)
  if (!potentialChart) return
  const levels = ['S级（高潜）', 'A级（优秀）', 'B级（合格）', 'C级（待提升）']
  const count = levels.map(l => potentialList.value.filter(e => e.potential_level === l).length)
  potentialChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: [
        { value: count[0] || 1, name: 'S级（高潜）', itemStyle: { color: '#16a34a' } },
        { value: count[1] || 1, name: 'A级（优秀）', itemStyle: { color: '#2563eb' } },
        { value: count[2] || 1, name: 'B级（合格）', itemStyle: { color: '#d97706' } },
        { value: count[3] || 1, name: 'C级（待提升）', itemStyle: { color: '#dc2626' } },
      ]
    }]
  })
}

function renderRiskPie() {
  riskPieChart = getOrCreateChart(riskPieChartRef)
  if (!riskPieChart) return
  const levels = ['高风险', '中风险', '低风险']
  const count = levels.map(l => positionRisks.value.filter(r => r.risk_level === l).length)
  riskPieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}个 ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: [
        { value: count[0] || 1, name: '高风险', itemStyle: { color: '#dc2626' } },
        { value: count[1] || 1, name: '中风险', itemStyle: { color: '#d97706' } },
        { value: count[2] || 1, name: '低风险', itemStyle: { color: '#16a34a' } },
      ]
    }]
  })
}

function resizeCharts() {
  [potentialChart, riskPieChart].forEach(c => c?.resize())
}

watch(activeTab, () => {
  nextTick(() => {
    if (activeTab.value === 'potential') {
      renderPotentialPie()
    } else if (activeTab.value === 'risk') {
      renderRiskPie()
    } else if (activeTab.value === 'records') {
      fetchAssessmentRecords()
    }
  })
})

onMounted(async () => {
  await Promise.all([fetchPotential(), fetchRisks()])
  loading.value = false
  initCharts()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  [potentialChart, riskPieChart].forEach(c => c?.dispose())
  window.removeEventListener('resize', resizeCharts)
})

async function fetchPotential() {
  try {
    const resp = await fetch('/api/potential')
    potentialList.value = await resp.json()
  } catch {
    error.value = '加载潜力数据失败'
  }
}

async function fetchRisks() {
  try {
    const [posResp, empResp] = await Promise.all([
      fetch('/api/position-risks'),
      fetch('/api/employee-risks'),
    ])
    positionRisks.value = await posResp.json()
    employeeRisks.value = await empResp.json()
  } catch {
    // ignore
  }
}

async function fetchAssessmentRecords() {
  try {
    const resp = await fetch('/api/potential-assessments/all')
    assessmentRecords.value = await resp.json()
  } catch {
    // ignore
  }
}

function getLevelTag(level) {
  if (!level) return { cls: 'tag-default', label: '未评级' }
  const map = {
    'S级（高潜）': { cls: 'tag-s', label: 'S级' },
    'A级（优秀）': { cls: 'tag-a', label: 'A级' },
    'B级（合格）': { cls: 'tag-b', label: 'B级' },
    'C级（待提升）': { cls: 'tag-c', label: 'C级' },
  }
  return map[level] || { cls: 'tag-default', label: level }
}

function getRiskLevelTag(level) {
  if (!level) return { cls: 'risk-low', label: '未知' }
  if (level.includes('高')) return { cls: 'risk-high', label: '高风险' }
  if (level.includes('中')) return { cls: 'risk-mid', label: '中风险' }
  return { cls: 'risk-low', label: '低风险' }
}

function getScoreColor(score) {
  if (!score) return '#94a3b8'
  const s = Number(score)
  if (s >= 70) return '#dc2626'
  if (s >= 40) return '#d97706'
  return '#16a34a'
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || chatLoading.value) return

  chatMessages.value.push({ role: 'user', content: text })
  userInput.value = ''
  chatLoading.value = true

  try {
    const resp = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: text,
        conversation_id: conversationId.value,
        inputs: {
          potential_data: JSON.stringify(potentialList.value.slice(0, 20)),
          position_risk_data: JSON.stringify(positionRisks.value.slice(0, 20)),
          employee_risk_data: JSON.stringify(employeeRisks.value.slice(0, 20)),
        }
      })
    })
    const data = await resp.json()
    if (data.answer) {
      chatMessages.value.push({ role: 'assistant', content: data.answer })
      conversationId.value = data.conversation_id || ''
    } else if (data.error) {
      chatMessages.value.push({ role: 'assistant', content: '✕ ' + data.error })
    }
    // 智能体可能修改了数据库，同步刷新左侧列表
    await Promise.all([fetchPotential(), fetchRisks()])
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '✕ 网络错误，请稍后重试' })
  } finally {
    chatLoading.value = false
  }
}
</script>

<template>
  <div class="potential-layout">
    <!-- 左侧：内容区 -->
    <div class="potential-main">
      <!-- 标签切换 -->
      <div class="tab-bar">
        <div
          :class="['tab-item', { active: activeTab === 'potential' }]"
          @click="activeTab = 'potential'"
        >
          ◈ 人才潜力评估
        </div>
        <div
          :class="['tab-item', { active: activeTab === 'risk' }]"
          @click="activeTab = 'risk'"
        >
          ▲ 岗位风险研判
        </div>
        <div
          :class="['tab-item', { active: activeTab === 'records' }]"
          @click="activeTab = 'records'"
        >
          ☰ 评估详情
        </div>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="error" class="error-state">{{ error }}</div>

      <!-- ====== 人才潜力评估 Tab ====== -->
      <template v-if="activeTab === 'potential'">
        <!-- 图表区域 -->
        <div class="charts-row">
          <div class="chart-box">
            <h4 class="chart-title">▣ 潜力等级分布</h4>
            <div ref="potentialChartRef" class="chart-canvas"></div>
          </div>
        </div>
        <div class="toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">员工潜力列表</span>
            <span class="toolbar-count">共 {{ filteredPotentialList.length }} 人</span>
          </div>
          <div class="search-box">
            <input
              v-model="searchQuery"
              class="search-input"
              placeholder="◎ 搜索工号或姓名..."
            />
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>工号</th>
                <th>姓名</th>
                <th>潜力评分</th>
                <th>潜力等级</th>
                <th>人才标签</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="emp in filteredPotentialList" :key="emp.employee_id">
                <td class="cell-id">{{ emp.employee_id }}</td>
                <td>{{ emp.name }}</td>
                <td class="cell-score">
                  <span class="score-bar" :style="{ width: (emp.potential_score || 0) + '%' }"></span>
                  <span class="score-text">{{ emp.potential_score ?? '-' }}</span>
                </td>
                <td>
                  <span :class="['tag', getLevelTag(emp.potential_level).cls]">
                    {{ getLevelTag(emp.potential_level).label }}
                  </span>
                </td>
                <td>{{ emp.talent_tag || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- ====== 岗位风险研判 Tab ====== -->
      <template v-if="activeTab === 'risk'">
        <!-- 图表区域 -->
        <div class="charts-row">
          <div class="chart-box">
            <h4 class="chart-title">● 岗位风险等级分布</h4>
            <div ref="riskPieChartRef" class="chart-canvas"></div>
          </div>
        </div>
        <!-- 岗位风险概览 -->
        <div class="risk-summary">
          <div class="risk-stat-card high">
            <span class="risk-stat-num">{{ positionRisks.filter(r => r.risk_level === '高风险').length }}</span>
            <span class="risk-stat-label">高风险岗位</span>
          </div>
          <div class="risk-stat-card low">
            <span class="risk-stat-num">{{ positionRisks.filter(r => r.risk_level === '低风险').length }}</span>
            <span class="risk-stat-label">低风险岗位</span>
          </div>
          <div class="risk-stat-card total">
            <span class="risk-stat-num">{{ positionRisks.length }}</span>
            <span class="risk-stat-label">评估岗位总数</span>
          </div>
        </div>

        <div class="toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">岗位风险排名</span>
          </div>
        </div>
        <div class="table-wrap risk-table">
          <table class="data-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>岗位名称</th>
                <th>风险评分</th>
                <th>风险等级</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(pos, idx) in positionRisks" :key="pos.position_name">
                <td class="cell-rank">{{ idx + 1 }}</td>
                <td>{{ pos.position_name }}</td>
                <td>
                  <div class="risk-score-bar">
                    <div
                      class="risk-score-fill"
                      :style="{ width: (pos.total_risk_score || 0) + '%', background: getScoreColor(pos.total_risk_score) }"
                    ></div>
                    <span class="risk-score-text">{{ pos.total_risk_score ?? '-' }}</span>
                  </div>
                </td>
                <td>
                  <span :class="['risk-badge', getRiskLevelTag(pos.risk_level).cls]">
                    {{ getRiskLevelTag(pos.risk_level).label }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>


      </template>

      <!-- ====== 评估详情 Tab ====== -->
      <template v-if="activeTab === 'records'">
        <div class="toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">☰ 潜力评估详情</span>
            <span class="toolbar-count">共 {{ filteredRecords.length }} 条</span>
          </div>
          <div class="search-box">
            <input
              v-model="recordsSearch"
              class="search-input"
              placeholder="◎ 搜索工号或姓名..."
            />
          </div>
        </div>
        <div v-if="filteredRecords.length === 0" class="empty-state">暂无评估详情</div>
        <div v-else class="record-cards">
          <div
            v-for="rec in filteredRecords"
            :key="rec.id"
            class="record-card"
            @click="viewAssessmentDetail(rec)"
          >
            <div class="card-id">{{ rec.employee_id }}</div>
            <div class="card-name">{{ rec.name }}</div>
            <div class="card-meta">
              <span v-if="rec.department">{{ rec.department }}</span>
              <span v-if="rec.current_position"> · {{ rec.current_position }}</span>
            </div>
            <div class="card-footer">
              <span class="card-time">{{ rec.created_at ? rec.created_at.slice(0, 10) : '-' }}</span>
              <button class="card-btn" @click.stop="viewAssessmentDetail(rec)">查看详情 →</button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 拖拽手柄 -->
    <div class="resize-handle" @mousedown="startResize"></div>

    <!-- 右侧：AI 对话助手 -->
    <div class="chat-sidebar" :style="{ flex: `0 0 ${sidebarWidth}%` }">
      <div class="chat-header">
        <span class="chat-avatar">◈</span>
        <div>
          <p class="chat-title">人才分析与风险研判助手</p>
          <p class="chat-subtitle">AI 智能体</p>
        </div>
        <button class="chat-clear" @click="chatMessages = chatMessages.slice(0, 1)" title="清除对话">清除</button>
      </div>

      <div class="chat-messages" ref="chatBox">
        <div
          v-for="(msg, i) in chatMessages"
          :key="i"
          :class="['chat-msg', msg.role]"
        >
          <div class="msg-bubble" v-html="renderMarkdown(msg.content)"></div>
        </div>
        <div v-if="chatLoading" class="chat-msg assistant">
          <div class="msg-bubble thinking">◎ 思考中...</div>
        </div>
      </div>

      <div class="chat-input-wrap">
        <input
          v-model="userInput"
          class="chat-input"
          placeholder="询问潜力评估或风险分析..."
          @keyup.enter="sendMessage"
          :disabled="chatLoading"
        />
        <button class="chat-send" @click="sendMessage" :disabled="chatLoading || !userInput.trim()">
          发送
        </button>
      </div>
    </div>
  </div>

  <!-- ── 评估详情弹窗 ── -->
  <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>☰ 评估详情</h3>
        <button class="modal-close" @click="closeDetailModal">✕</button>
      </div>
      <div class="modal-body" v-if="detailRecord">
        <div class="detail-item">
          <span class="detail-label">工号</span>
          <span class="detail-value">{{ detailRecord.employee_id }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">姓名</span>
          <span class="detail-value">{{ detailRecord.name }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">评估时间</span>
          <span class="detail-value">{{ detailRecord.created_at || '-' }}</span>
        </div>
        <div v-if="detailRecord.assessment_detail" class="detail-section">
          <h4>▸ 评估详情</h4>
          <div class="detail-text" v-html="renderMarkdown(detailRecord.assessment_detail)"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── 图表样式 ── */
.charts-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.chart-box {
  flex: 1;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  min-width: 0;
}

.chart-box-third {
  flex: 1;
}

.chart-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.chart-canvas {
  width: 100%;
  height: 200px;
}

.potential-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 120px);
}

.potential-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ── 标签栏 ── */
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 4px;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-item:hover {
  background: #f1f5f9;
}

.tab-item.active {
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  font-weight: 600;
}

/* ── 风险统计卡片 ── */
.risk-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.risk-stat-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.risk-stat-card.high { border-left: 4px solid #dc2626; }
.risk-stat-card.low { border-left: 4px solid #16a34a; }
.risk-stat-card.emp { border-left: 4px solid #d97706; }
.risk-stat-card.total { border-left: 4px solid #14b8a6; }

.risk-stat-num {
  font-size: 28px;
  font-weight: 700;
}

.risk-stat-label {
  font-size: 12px;
  color: #64748b;
}

/* ── 工具栏 ── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.toolbar-count {
  font-size: 13px;
  color: #94a3b8;
}

/* ── 搜索框 ── */
.search-box {
  display: flex;
  align-items: center;
}

.search-input {
  padding: 8px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  width: 220px;
  outline: none;
  transition: all 0.2s;
  background: #f8fafc;
}

.search-input:focus {
  border-color: #14b8a6;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
}

.search-input::placeholder {
  color: #94a3b8;
}

.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #94a3b8;
  font-size: 14px;
}

.table-wrap {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  min-height: 0;
}

.risk-table {
  max-height: 320px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.data-table td {
  padding: 9px 14px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
}

.data-table tbody tr:hover {
  background: #f8fafc;
}

.cell-id {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
  color: #64748b;
}

.cell-rank {
  font-weight: 600;
  color: #94a3b8;
  font-size: 12px;
}

.cell-score {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-bar {
  position: absolute;
  left: 14px;
  height: 6px;
  background: linear-gradient(90deg, #14b8a6, #0d9488);
  border-radius: 3px;
  opacity: 0.15;
  max-width: calc(100% - 28px);
}

.score-text {
  position: relative;
  font-weight: 600;
  font-family: 'SF Mono', 'Consolas', monospace;
}

/* ── 风险进度条 ── */
.risk-score-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.risk-score-fill {
  height: 6px;
  border-radius: 3px;
  opacity: 0.2;
  max-width: 120px;
  min-width: 8px;
}

.risk-score-text {
  font-weight: 600;
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
}

.risk-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.risk-badge.risk-high {
  background: #fee2e2;
  color: #991b1b;
}

.risk-badge.risk-mid {
  background: #fef3c7;
  color: #92400e;
}

.risk-badge.risk-low {
  background: #dcfce7;
  color: #166534;
}

/* ── 标签 ── */
.tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.tag-s {
  background: #dcfce7;
  color: #166534;
}

.tag-a {
  background: #dbeafe;
  color: #1e40af;
}

.tag-b {
  background: #fef9c3;
  color: #854d0e;
}

.tag-c {
  background: #fee2e2;
  color: #991b1b;
}

.tag-default {
  background: #f1f5f9;
  color: #64748b;
}

/* ── AI 聊天侧栏 ── */
.chat-sidebar {
  min-width: 260px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── 拖拽手柄 ── */
.resize-handle {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  flex-shrink: 0;
  transition: background 0.2s;
  border-radius: 3px;
  margin: 0 4px;
}

.resize-handle:hover,
.resize-handle:active {
  background: #14b8a6;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
}

.chat-avatar {
  font-size: 28px;
}

.chat-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.chat-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  opacity: 0.7;
}

.chat-clear {
  margin-left: auto;
  padding: 4px 10px;
  background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.3);
  color: #fff;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.chat-clear:hover {
  background: rgba(255,255,255,0.35);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f8fafc;
}

.chat-msg {
  display: flex;
}

.chat-msg.user {
  justify-content: flex-end;
}

.msg-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}

.msg-bubble :deep(p) {
  margin: 0 0 8px;
}

.msg-bubble :deep(p:last-child) {
  margin-bottom: 0;
}

.msg-bubble :deep(strong) {
  font-weight: 600;
  color: inherit;
}

.msg-bubble :deep(ul),
.msg-bubble :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.msg-bubble :deep(li) {
  margin-bottom: 4px;
}

.msg-bubble :deep(code) {
  background: rgba(99, 102, 241, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
}

.msg-bubble :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.msg-bubble :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: 12px;
}

.msg-bubble :deep(h1),
.msg-bubble :deep(h2),
.msg-bubble :deep(h3),
.msg-bubble :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
}

.msg-bubble :deep(h1) { font-size: 16px; }
.msg-bubble :deep(h2) { font-size: 15px; }
.msg-bubble :deep(h3) { font-size: 14px; }
.msg-bubble :deep(blockquote) {
  border-left: 3px solid #14b8a6;
  margin: 8px 0;
  padding: 6px 12px;
  background: rgba(20, 184, 166, 0.05);
  border-radius: 0 6px 6px 0;
  color: #64748b;
}

.msg-bubble :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 12px;
}

.msg-bubble :deep(th),
.msg-bubble :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 5px 8px;
  text-align: left;
  word-break: break-word;
  white-space: normal;
}

.msg-bubble :deep(th) {
  background: #f1f5f9;
  font-weight: 600;
}

.msg-bubble :deep(hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 12px 0;
}

.chat-msg.assistant .msg-bubble {
  background: #fff;
  color: #334155;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
}

.chat-msg.user .msg-bubble {
  background: #14b8a6;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-bubble.thinking {
  color: #94a3b8;
  animation: pulse-text 1.5s infinite;
}

@keyframes pulse-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.chat-input-wrap {
  display: flex;
  padding: 12px;
  border-top: 1px solid #e2e8f0;
  background: #fff;
  gap: 8px;
}

.chat-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #14b8a6;
}

.chat-send {
  padding: 8px 18px;
  border: none;
  background: #14b8a6;
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  white-space: nowrap;
}

.chat-send:hover {
  opacity: 0.9;
}

.chat-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
  font-size: 14px;
}
.btn-sm {
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-sm:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

/* ── 弹窗 ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  border-radius: 16px;
  width: 640px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}
.modal-close:hover {
  background: #f1f5f9;
  color: #475569;
}

.modal-body {
  padding: 24px;
}

.detail-item {
  margin-bottom: 10px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.detail-label {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.detail-value {
  font-size: 14px;
  color: #1e293b;
  font-weight: 500;
}

.detail-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  margin: 0 0 12px;
}

.detail-text {
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  white-space: pre-wrap;
}

.detail-text :deep(p) {
  margin: 0 0 8px;
}
.detail-text :deep(ul), .detail-text :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}
.detail-text :deep(li) {
  margin-bottom: 2px;
}

.cell-time {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

/* ── 卡片视图 ── */
.record-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  padding-bottom: 20px;
}

.record-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-card:hover {
  border-color: #14b8a6;
  box-shadow: 0 4px 16px rgba(20, 184, 166, 0.1);
  transform: translateY(-2px);
}

.card-id {
  font-size: 13px;
  font-weight: 600;
  color: #14b8a6;
  font-family: 'SF Mono', 'Consolas', monospace;
  margin-bottom: 4px;
}

.card-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.card-meta {
  font-size: 12px;
  color: #94a3b8;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.card-time {
  font-size: 12px;
  color: #94a3b8;
}

.card-btn {
  background: none;
  border: none;
  color: #14b8a6;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.card-btn:hover {
  background: #f0fdfa;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
  font-size: 14px;
}

</style>
