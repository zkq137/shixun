<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const targetPosition = ref('')
const promotionRule = ref('')
const managerComment = ref('')
const createdBy = ref('HR')
const positionOptions = ref([])
const positionError = ref('')
const workflowResult = ref(null)
const workflowError = ref('')
const chatLoading = ref(false)
const userInput = ref('')
const chatBox = ref(null)
const conversationId = ref(localStorage.getItem('promotion_agent_conversation_id') || '')
const chatMessages = ref([
  {
    role: 'assistant',
    content: '您好！我是**晋升决策辅助 Agent**，可以根据目标岗位、HR 规则和经理评价生成晋升建议，也支持继续追问候选人比较、风险点和决策理由。',
  },
])

function renderMarkdown(text) {
  if (!text) return ''
  const clean = String(text).replace(/<think>[\s\S]*?<\/think>/g, '').replace(/^<think>.*$/gm, '')
  return marked.parse(clean)
}

async function scrollToBottom() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

async function fetchPositionOptions() {
  positionError.value = ''
  try {
    const resp = await fetch('/api/promotion-agent/positions')
    if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
    positionOptions.value = await resp.json()
  } catch (e) {
    positionError.value = `岗位列表加载失败: ${e.message}`
  }
}

function getRecentContext() {
  return chatMessages.value
    .slice(-8)
    .map((msg) => `${msg.role === 'user' ? '??' : '??'}: ${String(msg.content || '').replace(/\s+/g, ' ').trim()}`)
    .join('\n')
}

function parseSseBlock(block) {
  let event = 'message'
  let data = ''
  block.split(/\r?\n/).forEach((line) => {
    if (line.startsWith('event:')) event = line.slice(6).trim() || event
    if (line.startsWith('data:')) data += line.slice(5).trim()
  })
  if (!data) return null
  try {
    return { event, payload: JSON.parse(data) }
  } catch {
    return { event, payload: data }
  }
}

function setConversationId(value) {
  if (!value) return
  conversationId.value = value
  localStorage.setItem('promotion_agent_conversation_id', value)
}

async function sendPromotionMessage(text) {
  const query = text.trim()
  if (!query || chatLoading.value) return
  if (!targetPosition.value.trim()) {
    workflowError.value = '请先选择或填写目标晋升岗位'
    return
  }

  workflowError.value = ''
  workflowResult.value = null
  chatMessages.value.push({ role: 'user', content: query })
  const assistantIndex = chatMessages.value.length
  chatMessages.value.push({ role: 'assistant', content: '正在启动晋升决策工作流...' })
  chatLoading.value = true
  await scrollToBottom()

  try {
    const resp = await fetch('/api/promotion-agent/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        conversation_id: conversationId.value,
        conversation_context: getRecentContext(),
        target_position: targetPosition.value.trim(),
        promotion_rule: promotionRule.value.trim(),
        manager_comment: managerComment.value.trim(),
        created_by: createdBy.value.trim() || 'HR',
      }),
    })

    if (!resp.ok || !resp.body) {
      let message = `请求失败: ${resp.status}`
      try {
        const data = await resp.json()
        message = data.error || message
      } catch {}
      throw new Error(message)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let liveText = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split(/\n\n/)
      buffer = blocks.pop() || ''

      for (const block of blocks) {
        const parsed = parseSseBlock(block)
        if (!parsed) continue
        const { event, payload } = parsed

        if (event === 'error') {
          throw new Error(payload?.error || '晋升决策工作流执行失败')
        }
        if (event === 'session') {
          setConversationId(payload?.conversation_id)
          continue
        }
        if (event === 'progress') {
          chatMessages.value[assistantIndex].content = payload?.message || '正在分析...'
          await scrollToBottom()
          continue
        }
        if (event === 'token') {
          liveText += payload?.text || ''
          chatMessages.value[assistantIndex].content = liveText || '正在生成...'
          await scrollToBottom()
          continue
        }
        if (event === 'done') {
          workflowResult.value = payload
          if (payload?.status === 'failed' || payload?.error) {
            const errorText = payload?.error || 'Dify workflow failed without an error message.'
            workflowError.value = errorText
            chatMessages.value[assistantIndex].content = `???${errorText}`
          } else {
            const report = payload?.promotion_report || liveText || '??????????????'
            chatMessages.value[assistantIndex].content = report
          }
          await scrollToBottom()
        }
      }
    }
  } catch (e) {
    workflowError.value = e.message
    chatMessages.value[assistantIndex].content = `???${e.message}`
  } finally {
    chatLoading.value = false
    userInput.value = ''
    await scrollToBottom()
  }
}

function generateReport() {
  sendPromotionMessage('请基于当前表单生成晋升决策建议')
}

function sendMessage() {
  sendPromotionMessage(userInput.value)
}

onMounted(fetchPositionOptions)
</script>

<template>
  <div class="agent-layout">
    <section class="panel agent-main">
      <div class="section-header">
        <div>
          <h2>晋升决策辅助 Agent</h2>
          <p class="section-desc">独立接入你的本地 Dify 晋升工作流，不占用队友继任计划模块。</p>
        </div>
        <button class="btn-primary" :disabled="chatLoading" @click="generateReport">
          {{ chatLoading ? '生成中...' : '生成晋升建议' }}
        </button>
      </div>

      <div class="workflow-form">
        <div class="form-grid">
          <div class="form-group form-group-wide">
            <label for="target-position">目标晋升岗位</label>
            <input id="target-position" v-model="targetPosition" list="promotion-position-options" type="text" placeholder="例如：信息技术总监" />
            <datalist id="promotion-position-options">
              <option v-for="name in positionOptions" :key="name" :value="name" />
            </datalist>
            <p v-if="positionError" class="hint-error">{{ positionError }}</p>
          </div>

          <div class="form-group">
            <label for="created-by">发起人</label>
            <input id="created-by" v-model="createdBy" type="text" placeholder="HR" />
          </div>

          <div class="form-group form-group-wide">
            <label for="promotion-rule">HR 晋升规则</label>
            <textarea id="promotion-rule" v-model="promotionRule" rows="4" placeholder="例如：绩效低于4暂缓，必须完成核心培训" />
          </div>

          <div class="form-group form-group-wide">
            <label for="manager-comment">部门经理评价</label>
            <textarea id="manager-comment" v-model="managerComment" rows="4" placeholder="例如：优先考虑技术管理经验和跨部门协作能力" />
          </div>
        </div>
      </div>

      <div v-if="workflowError" class="error-state">{{ workflowError }}</div>

      <div v-if="workflowResult" class="result-card">
        <div class="result-header">
          <h3>最近一次晋升建议</h3>
          <span v-if="workflowResult.workflow_run_id" class="run-id">{{ workflowResult.workflow_run_id }}</span>
        </div>
        <div class="markdown-body" v-html="renderMarkdown(workflowResult.promotion_report || '工作流未返回 promotion_report。')"></div>
        <details v-if="workflowResult.position_profile_raw" class="raw-details">
          <summary>岗位画像原始结果</summary>
          <pre>{{ workflowResult.position_profile_raw }}</pre>
        </details>
        <details v-if="workflowResult.candidate_pool_raw" class="raw-details">
          <summary>候选人池原始结果</summary>
          <pre>{{ workflowResult.candidate_pool_raw }}</pre>
        </details>
      </div>
    </section>

    <aside class="chat-sidebar">
      <div class="chat-header promotion-chat-header">
        <span class="chat-avatar">?</span>
        <div>
          <p class="chat-title">晋升决策辅助</p>
          <p class="chat-subtitle">AI 智能体</p>
        </div>
      </div>

      <div class="chat-messages" ref="chatBox">
        <div v-for="(msg, i) in chatMessages" :key="i" :class="['chat-msg', msg.role]">
          <div class="msg-bubble" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>

      <div class="chat-input-wrap">
        <input v-model="userInput" class="chat-input" placeholder="继续追问候选人、规则或决策理由..." @keyup.enter="sendMessage" :disabled="chatLoading" />
        <button class="chat-send promotion-send" @click="sendMessage" :disabled="chatLoading || !userInput.trim()">??</button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.agent-layout {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.agent-main {
  flex: 1;
  min-width: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.section-header h2 {
  margin: 0;
}

.section-desc {
  color: #64748b;
  font-size: 14px;
  margin: 6px 0 0;
}

.workflow-form,
.result-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.form-group-wide {
  grid-column: span 2;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  outline: none;
}

.form-group textarea {
  resize: vertical;
  line-height: 1.6;
}

.form-group input:focus,
.form-group textarea:focus,
.chat-input:focus {
  border-color: #0d9488;
}

.btn-primary {
  padding: 10px 18px;
  background: #0d9488;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.btn-primary:disabled,
.chat-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hint-error,
.error-state {
  color: #b91c1c;
  font-size: 13px;
}

.error-state {
  margin-top: 12px;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
}

.result-card {
  margin-top: 16px;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}

.result-header h3 {
  margin: 0;
  color: #166534;
  font-size: 15px;
}

.run-id {
  color: #64748b;
  font-size: 12px;
}

.markdown-body {
  color: #14532d;
  font-size: 14px;
  line-height: 1.75;
}

.raw-details {
  margin-top: 12px;
  border-top: 1px solid #bbf7d0;
  padding-top: 10px;
}

.raw-details summary {
  cursor: pointer;
  color: #166534;
  font-size: 13px;
  font-weight: 600;
}

.raw-details pre {
  white-space: pre-wrap;
  word-break: break-word;
  color: #334155;
  font-size: 13px;
}

.chat-sidebar {
  width: 360px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 620px;
  max-height: calc(100vh - 120px);
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  color: #fff;
}

.promotion-chat-header {
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
  opacity: 0.8;
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
  max-width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}

.chat-msg.assistant .msg-bubble {
  background: #fff;
  color: #334155;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
}

.chat-msg.user .msg-bubble {
  background: #0d9488;
  color: #fff;
  border-bottom-right-radius: 4px;
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
  min-width: 0;
  padding: 10px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.chat-send {
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: #fff;
  background: #0d9488;
}

@media (max-width: 1100px) {
  .agent-layout {
    flex-direction: column;
  }

  .chat-sidebar {
    width: 100%;
    max-height: none;
  }
}

@media (max-width: 760px) {
  .section-header,
  .form-grid {
    display: block;
  }

  .form-group {
    margin-bottom: 14px;
  }

  .btn-primary {
    width: 100%;
    margin-top: 12px;
  }
}
</style>
