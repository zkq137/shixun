<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

// ── 状态 ──
const activeTab = ref('potential')  // 'potential' | 'risk'
const potentialList = ref([])
const positionRisks = ref([])
const employeeRisks = ref([])
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

// AI 聊天
const chatMessages = ref([
  {
    role: 'assistant',
    content: '您好！我是**人才分析与风险研判助手** 🧠，可以帮您：\n\n' +
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

function renderMarkdown(text) {
  if (!text) return ''
  let clean = text.replace(/<think>[\s\S]*?<\/think>/g, '')
  clean = clean.replace(/^<think>.*$/gm, '')
  return marked.parse(clean)
}

onMounted(async () => {
  await Promise.all([fetchPotential(), fetchRisks()])
  loading.value = false
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
      chatMessages.value.push({ role: 'assistant', content: '❌ ' + data.error })
    }
    // 智能体可能修改了数据库，同步刷新左侧列表
    await Promise.all([fetchPotential(), fetchRisks()])
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '❌ 网络错误，请稍后重试' })
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
          🧠 人才潜力评估
        </div>
        <div
          :class="['tab-item', { active: activeTab === 'risk' }]"
          @click="activeTab = 'risk'"
        >
          ⚠️ 岗位风险研判
        </div>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="error" class="error-state">{{ error }}</div>

      <!-- ====== 人才潜力评估 Tab ====== -->
      <template v-if="activeTab === 'potential'">
        <div class="toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">员工潜力列表</span>
            <span class="toolbar-count">共 {{ filteredPotentialList.length }} 人</span>
          </div>
          <div class="search-box">
            <input
              v-model="searchQuery"
              class="search-input"
              placeholder="🔍 搜索工号或姓名..."
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
          <div class="risk-stat-card emp">
            <span class="risk-stat-num">{{ employeeRisks.filter(r => r.attrition_risk === '高风险').length }}</span>
            <span class="risk-stat-label">高流失风险员工</span>
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

        <!-- 员工流失风险 -->
        <div class="toolbar" style="margin-top:16px">
          <div class="toolbar-left">
            <span class="toolbar-title">员工流失风险</span>
            <span class="toolbar-count">共 {{ filteredEmployeeRisks.length }} 人</span>
          </div>
          <div class="search-box">
            <input
              v-model="searchQuery"
              class="search-input"
              placeholder="🔍 搜索工号、姓名或部门..."
            />
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>工号</th>
                <th>姓名</th>
                <th>部门</th>
                <th>当前岗位</th>
                <th>流失风险分</th>
                <th>流失风险</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="emp in filteredEmployeeRisks" :key="emp.employee_id">
                <td class="cell-id">{{ emp.employee_id }}</td>
                <td>{{ emp.name }}</td>
                <td>{{ emp.department || '-' }}</td>
                <td>{{ emp.current_position || '-' }}</td>
                <td>
                  <span :style="{ color: getScoreColor(emp.attrition_risk_score), fontWeight: 600 }">
                    {{ emp.attrition_risk_score ?? '-' }}
                  </span>
                </td>
                <td>
                  <span :class="['risk-badge', getRiskLevelTag(emp.attrition_risk).cls]">
                    {{ getRiskLevelTag(emp.attrition_risk).label }}
                  </span>
                </td>
                <td>{{ emp.potential_score ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <!-- 右侧：AI 对话助手 -->
    <div class="chat-sidebar">
      <div class="chat-header">
        <span class="chat-avatar">🧠</span>
        <div>
          <p class="chat-title">人才分析与风险研判助手</p>
          <p class="chat-subtitle">AI 智能体</p>
        </div>
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
          <div class="msg-bubble thinking">⏳ 思考中...</div>
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
</template>

<style scoped>
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
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-weight: 600;
}

/* ── 风险统计卡片 ── */
.risk-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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
.risk-stat-card.total { border-left: 4px solid #6366f1; }

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
  border-color: #6366f1;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
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
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
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
  width: 360px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
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
  border-left: 3px solid #6366f1;
  margin: 8px 0;
  padding: 6px 12px;
  background: rgba(99, 102, 241, 0.05);
  border-radius: 0 6px 6px 0;
  color: #64748b;
}

.msg-bubble :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 12px;
}

.msg-bubble :deep(th),
.msg-bubble :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  text-align: left;
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
  background: #6366f1;
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
  border-color: #6366f1;
}

.chat-send {
  padding: 8px 18px;
  border: none;
  background: #6366f1;
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
</style>
