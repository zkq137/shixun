<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const activeTab = ref('plan') // 'plan' | 'completed' | 'ability'
const trainingList = ref([])
const abilityTrainings = ref([])
const loading = ref(true)
const error = ref('')

const completedTrainings = computed(() =>
  trainingList.value.filter(t => t.is_completed)
)
const abilitySearch = ref('')
const filteredAbilityTrainings = computed(() => {
  const q = abilitySearch.value.trim().toLowerCase()
  if (!q) return abilityTrainings.value
  return abilityTrainings.value.filter(
    item => item.name.includes(q) || item.employee_id.toLowerCase().includes(q)
  )
})

// 新增培训表单
const showAddForm = ref(false)
const formData = ref({ employee_id: '', name: '', training_plan: '' })
const adding = ref(false)

// AI 聊天
const chatMessages = ref([
  {
    role: 'assistant',
    content: '您好！我是**培训发展助手** ◈，可以帮您：\n\n' +
      '• 根据员工情况制定培训\n' +
      '• 根据您的选择安排培训\n\n' +
      '请问有什么可以帮您的？'
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

async function fetchAbilityTrainings() {
  try {
    const resp = await fetch('/api/training/completed-abilities')
    if (resp.ok) abilityTrainings.value = await resp.json()
  } catch {}
}

onMounted(async () => {
  await Promise.all([fetchTrainingList(), fetchAbilityTrainings()])
})

async function fetchTrainingList() {
  loading.value = true
  error.value = ''
  try {
    const resp = await fetch('/api/training/list')
    if (!resp.ok) throw new Error('请求失败')
    trainingList.value = await resp.json()
  } catch (e) {
    error.value = '加载培训数据失败: ' + e.message
  } finally {
    loading.value = false
  }
}

async function addTraining() {
  if (!formData.value.employee_id || !formData.value.name || !formData.value.training_plan) {
    return
  }
  adding.value = true
  try {
    const resp = await fetch('/api/training/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData.value),
    })
    const data = await resp.json()
    if (data.status === 'ok') {
      formData.value = { employee_id: '', name: '', training_plan: '' }
      showAddForm.value = false
      await fetchTrainingList()
    } else {
      alert('添加失败: ' + (data.error || '未知错误'))
    }
  } catch {
    alert('网络错误')
  } finally {
    adding.value = false
  }
}

async function toggleCompletion(item) {
  try {
    const resp = await fetch('/api/training/update-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        employee_id: item.employee_id,
        training_plan: item.training_plan,
        is_completed: item.is_completed ? 0 : 1,
      }),
    })
    const data = await resp.json()
    if (data.status === 'ok') {
      await Promise.all([fetchTrainingList(), fetchAbilityTrainings()])
    }
  } catch {
    alert('更新失败')
  }
}

async function deleteTraining(item) {
  if (!confirm(`确定删除 ${item.name} 的培训计划「${item.training_plan}」吗？`)) return
  try {
    const resp = await fetch('/api/training/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        employee_id: item.employee_id,
        training_plan: item.training_plan,
      }),
    })
    const data = await resp.json()
    if (data.status === 'ok') {
      await Promise.all([fetchTrainingList(), fetchAbilityTrainings()])
    }
  } catch {
    alert('删除失败')
  }
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || chatLoading.value) return

  chatMessages.value.push({ role: 'user', content: text })
  userInput.value = ''
  chatLoading.value = true

  try {
    const resp = await fetch('/api/ai/training-chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: text,
        conversation_id: conversationId.value,
        inputs: {
          training_data: JSON.stringify(trainingList.value.slice(0, 50)),
        },
      }),
    })
    const data = await resp.json()
    if (data.answer) {
      chatMessages.value.push({ role: 'assistant', content: data.answer })
      conversationId.value = data.conversation_id || ''
    } else if (data.error) {
      chatMessages.value.push({ role: 'assistant', content: '✕ ' + data.error })
    }
    // 智能体可能修改了数据库，同步刷新左侧列表
    await Promise.all([fetchTrainingList(), fetchAbilityTrainings()])
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '✕ 网络错误，请稍后重试' })
  } finally {
    chatLoading.value = false
  }
}
</script>

<template>
  <div class="training-layout">
    <!-- 左侧：培训计划列表 -->
    <div class="training-main">
      <!-- Tab 切换 -->
      <div class="tab-bar">
        <div
          :class="['tab-item', { active: activeTab === 'plan' }]"
          @click="activeTab = 'plan'"
        >
          ☰ 培训计划
        </div>
        <div
          :class="['tab-item', { active: activeTab === 'ability' }]"
          @click="activeTab = 'ability'"
        >
          ☰ 能力培训完成
        </div>
      </div>

      <!-- ====== 培训计划 Tab ====== -->
      <template v-if="activeTab === 'plan'">
        <div class="toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">员工培训计划</span>
            <span class="toolbar-count">共 {{ trainingList.length }} 项</span>
          </div>
          <button class="btn-add" @click="showAddForm = !showAddForm">
            {{ showAddForm ? '收起' : '+ 新增培训' }}
          </button>
        </div>

        <!-- 新增表单 -->
        <div v-if="showAddForm" class="add-form">
          <input v-model="formData.employee_id" placeholder="员工ID" class="form-input" />
          <input v-model="formData.name" placeholder="员工姓名" class="form-input" />
          <input v-model="formData.training_plan" placeholder="培训计划名称" class="form-input" />
          <button class="btn-submit" @click="addTraining" :disabled="adding">
            {{ adding ? '提交中...' : '确认添加' }}
          </button>
        </div>

        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else-if="error" class="error-state">{{ error }}</div>

        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>员工ID</th>
                <th>姓名</th>
                <th>培训计划</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in trainingList" :key="item.employee_id + item.training_plan">
                <td class="cell-id">{{ item.employee_id }}</td>
                <td>{{ item.name }}</td>
                <td>{{ item.training_plan }}</td>
                <td>
                  <span :class="['tag', item.is_completed ? 'tag-s' : 'tag-b']">
                    {{ item.is_completed ? '✓ 已完成' : '◎ 未完成' }}
                  </span>
                </td>
                <td class="cell-date">{{ item.created_at ? item.created_at.slice(0, 10) : '-' }}</td>
                <td class="cell-actions">
                  <button
                    class="btn-action btn-toggle"
                    @click="toggleCompletion(item)"
                    :title="item.is_completed ? '标记为未完成' : '标记为已完成'"
                  >
                    {{ item.is_completed ? '↩ 撤回' : '✓ 完成' }}
                  </button>
                  <button class="btn-action btn-delete" @click="deleteTraining(item)">✕ 删除</button>
                </td>
              </tr>
              <tr v-if="trainingList.length === 0">
                <td colspan="6" class="empty-cell">暂无培训计划数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- ====== 已完成培训 Tab ====== -->
      <template v-if="activeTab === 'completed'">
        <div class="toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">✓ 已完成培训记录</span>
            <span class="toolbar-count">共 {{ completedTrainings.length }} 项</span>
          </div>
        </div>

        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else-if="error" class="error-state">{{ error }}</div>

        <div v-else-if="completedTrainings.length === 0" class="loading-state">
          暂无已完成培训记录
        </div>

        <div v-else class="completed-grid">
          <div
            v-for="item in completedTrainings"
            :key="'done-' + item.employee_id + item.training_plan"
            class="completed-card"
          >
            <div class="card-icon">✓</div>
            <div class="card-body">
              <div class="card-name">{{ item.name }}</div>
              <div class="card-plan">{{ item.training_plan }}</div>
              <div class="card-meta">
                <span class="meta-badge">工号: {{ item.employee_id }}</span>
                <span class="meta-date">{{ item.created_at ? item.created_at.slice(0, 10) : '-' }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- ====== 能力培训完成 Tab ====== -->
      <template v-if="activeTab === 'ability'">
        <div class="toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">☰ 员工已完成培训（能力表）</span>
            <span class="toolbar-count">共 {{ filteredAbilityTrainings.length }} 人</span>
          </div>
          <div class="search-box">
            <input
              v-model="abilitySearch"
              class="search-input"
              placeholder="◎ 搜索姓名或工号..."
            />
          </div>
        </div>

        <div v-if="abilityTrainings.length === 0" class="loading-state">
          暂无数据
        </div>

        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>员工ID</th>
                <th>姓名</th>
                <th>已完成培训</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in filteredAbilityTrainings" :key="'ab' + idx">
                <td class="cell-id">{{ item.employee_id }}</td>
                <td>{{ item.name }}</td>
                <td>
                  <div class="ability-tags">
                    <span v-for="(t, ti) in item.trainings" :key="ti" class="ability-tag">{{ t }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <!-- 右侧：AI 培训助手 -->
    <div class="chat-sidebar">
      <div class="chat-header training-chat-header">
        <span class="chat-avatar">◈</span>
        <div>
          <p class="chat-title">培训发展助手</p>
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
          <div class="msg-bubble thinking">◎ 思考中...</div>
        </div>
      </div>

      <div class="chat-input-wrap">
        <input
          v-model="userInput"
          class="chat-input"
          placeholder="询问培训建议、分析需求..."
          @keyup.enter="sendMessage"
          :disabled="chatLoading"
        />
        <button
          class="chat-send training-send"
          @click="sendMessage"
          :disabled="chatLoading || !userInput.trim()"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Tab 切换 ── */
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

/* ── 能力培训标签 ── */
.ability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.ability-tag {
  display: inline-block;
  padding: 2px 10px;
  background: #f0fdfa;
  color: #0d9488;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

/* ── 已完成培训卡片 ── */
.completed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}

.completed-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  transition: box-shadow 0.2s, transform 0.1s;
}

.completed-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}

.card-icon {
  font-size: 28px;
  flex-shrink: 0;
  margin-top: 2px;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.card-plan {
  font-size: 13px;
  color: #475569;
  margin-bottom: 8px;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.meta-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #f0fdfa;
  color: #0d9488;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.meta-date {
  font-size: 11px;
  color: #94a3b8;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.training-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 120px);
}

.training-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.toolbar-count {
  font-size: 13px;
  color: #94a3b8;
}

.btn-add {
  padding: 8px 18px;
  border: none;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-add:hover {
  opacity: 0.9;
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
  width: 200px;
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

.add-form {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding: 16px;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 12px;
  flex-wrap: wrap;
}

.form-input {
  flex: 1;
  min-width: 140px;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: #14b8a6;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
}

.btn-submit {
  padding: 10px 20px;
  border: none;
  background: #14b8a6;
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-submit:hover {
  opacity: 0.9;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.error-state {
  color: #dc2626;
}

.table-wrap {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
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
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.data-table td {
  padding: 10px 16px;
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

.cell-date {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
  color: #94a3b8;
}

.cell-actions {
  display: flex;
  gap: 6px;
}

.btn-action {
  padding: 4px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.btn-toggle {
  color: #0d9488;
  border-color: #99f6e4;
}

.btn-toggle:hover {
  background: #f0fdfa;
}

.btn-delete {
  color: #dc2626;
  border-color: #fca5a5;
}

.btn-delete:hover {
  background: #fef2f2;
}

.empty-cell {
  text-align: center;
  color: #94a3b8;
  padding: 40px !important;
}

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

.tag-b {
  background: #fef9c3;
  color: #854d0e;
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
  color: #fff;
}

.training-chat-header {
  background: linear-gradient(135deg, #0d9488, #14b8a6);
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
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.chat-msg.assistant .msg-bubble {
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #1e293b;
}

.chat-msg.user .msg-bubble {
  background: #0d9488;
  color: #fff;
}

.msg-bubble.thinking {
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #94a3b8;
  font-style: italic;
}

.chat-input-wrap {
  display: flex;
  padding: 12px;
  border-top: 1px solid #e2e8f0;
  gap: 8px;
  background: #fff;
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
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
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
  color: #fff;
}

.training-send {
  background: #0d9488;
}

.chat-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-send:hover:not(:disabled) {
  opacity: 0.9;
}
</style>
