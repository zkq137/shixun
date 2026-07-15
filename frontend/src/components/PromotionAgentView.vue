<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const defaultGreeting = '您好，我是晋升决策辅助 Agent。您可以先生成一版晋升建议，再在右侧继续追问并随时修改左侧正文。'
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
const elapsedTimer = ref(null)
const editableReport = ref('')
const chatMessages = ref([{ role: 'assistant', content: defaultGreeting, thinking: '' }])

const hasDebugOutput = computed(() => {
  const result = workflowResult.value || {}
  return Boolean(result.position_profile_raw || result.candidate_pool_raw || result.raw)
})

function createAssistantMessage(content) {
  return {
    role: 'assistant',
    content,
    thinking: '',
    status: 'running',
    startedAt: Date.now(),
    finishedAt: null,
    elapsedMs: 0,
    currentStep: '',
    steps: [],
    tools: {
      database: null,
      reviseReport: null,
      askUser: null,
    },
    updatedReport: false,
  }
}

function formatElapsed(ms) {
  const totalSeconds = Math.max(0, Math.floor((ms || 0) / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return minutes ? `${minutes}m ${seconds}s` : `${seconds}s`
}

function stopElapsedTimer() {
  if (elapsedTimer.value) {
    clearInterval(elapsedTimer.value)
    elapsedTimer.value = null
  }
}

function startElapsedTimer(messageIndex) {
  stopElapsedTimer()
  elapsedTimer.value = setInterval(() => {
    const message = chatMessages.value[messageIndex]
    if (message?.status === 'running') {
      chatMessages.value[messageIndex] = {
        ...message,
        elapsedMs: Date.now() - message.startedAt,
      }
    }
  }, 1000)
}

function updateAssistantStep(message, stepTitle, status = 'running') {
  const title = cleanProgressMessage(stepTitle)
  if (!message || !title) return
  const previous = message.steps[message.steps.length - 1]
  if (previous && previous.status === 'running' && previous.title !== title) {
    previous.status = 'done'
  }
  const existing = message.steps.find((item) => item.title === title)
  if (existing) {
    existing.status = status
  } else {
    message.steps.push({ title, status })
  }
  message.currentStep = status === 'running' ? title : ''
  if (title.includes('数据库') || title.includes('岗位要求') || title.includes('候选人池')) {
    message.tools.database = true
  }
}

function finishAssistantRun(message, payload, mode) {
  if (!message) return
  message.status = payload?.error ? 'failed' : 'done'
  message.finishedAt = Date.now()
  message.elapsedMs = payload?.elapsed_ms || (message.finishedAt - message.startedAt)
  message.currentStep = ''
  message.steps = message.steps.map((step) => ({
    ...step,
    status: step.status === 'running' ? 'done' : step.status,
  }))
  const updatedReport = Boolean(payload?.updated_report)
  const toolUsage = payload?.tool_usage || {}
  message.updatedReport = updatedReport
  message.tools.reviseReport = typeof toolUsage.revise_report === 'boolean' ? toolUsage.revise_report : updatedReport
  message.tools.askUser = typeof toolUsage.ask_user === 'boolean' ? toolUsage.ask_user : false
  const hasDatabaseOutput = Boolean(payload?.position_profile_raw || payload?.candidate_pool_raw)
  if (typeof toolUsage.database === 'boolean') {
    message.tools.database = toolUsage.database
  } else if (hasDatabaseOutput) {
    message.tools.database = true
  }
  if (message.tools.database === null) message.tools.database = false
  if (mode === 'generate') message.tools.database = hasDatabaseOutput || true
  stopElapsedTimer()
}

function failAssistantRun(message) {
  if (!message) return
  message.status = 'failed'
  message.finishedAt = Date.now()
  message.elapsedMs = message.finishedAt - message.startedAt
  message.currentStep = ''
  message.steps = message.steps.map((step) => ({
    ...step,
    status: step.status === 'running' ? 'error' : step.status,
  }))
  stopElapsedTimer()
}

function toolLabel(value) {
  if (value === true) return '已使用'
  if (value === false) return '未使用'
  return '未判断'
}


function stripPrivateThought(text) {
  return String(text || '')
    .replace(/<think>[\s\S]*?<\/think>/g, '')
    .replace(/^<think>.*$/gm, '')
}

function fenceDecisionJsonBlocks(text) {
  return String(text || '').replace(
    /(##\s*5[.、]\s*决策记录草案[\s\S]*?)(\n\s*\{[\s\S]*?\n\s*\})(?=\n\s*(?:##\s*\d|$))/g,
    (_, heading, block) => heading + '\n\n```json' + block + '\n```',
  )
}

function normalizeMarkdown(text) {
  return fenceDecisionJsonBlocks(stripPrivateThought(text))
    .replace(/\r\n/g, '\n')
    .replace(/\n{4,}/g, '\n\n\n')
}

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(normalizeMarkdown(text))
}

function compactText(text, limit = 360) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim()
  return clean.length > limit ? `${clean.slice(0, limit)}...` : clean
}

function getRecentContext() {
  const draft = editableReport.value ? `当前晋升建议正文：${compactText(editableReport.value, 700)}` : ''
  const dialog = chatMessages.value
    .slice(-6)
    .map((msg) => `${msg.role === 'user' ? '用户' : '助手'}: ${compactText(msg.content)}`)
    .join('\n')
  return [draft, dialog].filter(Boolean).join('\n')
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

function parseSseBlock(block) {
  let event = 'message'
  const dataLines = []
  block.split(/\r?\n/).forEach((line) => {
    if (line.startsWith('event:')) event = line.slice(6).trim() || event
    if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
  })
  const data = dataLines.join('\n')
  if (!data) return null
  try {
    return { event, payload: JSON.parse(data) }
  } catch {
    return { event, payload: data }
  }
}

function splitChatPackage(text) {
  const raw = stripPrivateThought(text).trim()
  if (!raw) return { thinking: '', reply: '', report: '' }
  const thinkingMatch = raw.match(/THINKING_SUMMARY:\s*([\s\S]*?)(?:\nCHAT_REPLY:|\nUPDATED_REPORT:|$)/)
  const replyMatch = raw.match(/CHAT_REPLY:\s*([\s\S]*?)(?:\nUPDATED_REPORT:|$)/)
  const reportMatch = raw.match(/UPDATED_REPORT:\s*([\s\S]*)$/)
  const fallback = raw
    .replace(/THINKING_SUMMARY:\s*[\s\S]*?(?:\nCHAT_REPLY:|$)/, '')
    .replace(/UPDATED_REPORT:\s*[\s\S]*$/, '')
    .trim()
  return {
    thinking: thinkingMatch ? thinkingMatch[1].trim() : '',
    reply: replyMatch ? replyMatch[1].trim() : fallback,
    report: reportMatch ? reportMatch[1].trim() : '',
  }
}

function getLiveChatDisplay(rawText) {
  const parsed = splitChatPackage(rawText)
  return {
    thinking: parsed.thinking,
    content: parsed.reply || '正在组织回复...',
  }
}

function setConversationId(value) {
  if (!value) return
  conversationId.value = value
  localStorage.setItem('promotion_agent_conversation_id', value)
}

function cleanProgressMessage(message) {
  return String(message || '')
    .replace(/\s*已处理\s*$/g, '')
    .replace(/\s*已完成\s*$/g, '')
    .trim()
}

async function handleStreamEvent(event, payload, assistantIndex, liveTextRef, mode) {
  if (event === 'error') {
    throw new Error(payload?.error || '晋升决策工作流执行失败')
  }
  if (event === 'session') {
    setConversationId(payload?.conversation_id)
    return
  }
  if (event === 'progress' || event === 'status') {
    const message = payload?.message || payload?.status || '正在分析...'
    updateAssistantStep(chatMessages.value[assistantIndex], message, 'running')
    await scrollToBottom()
    return
  }
  if (event === 'token' || event === 'delta') {
    const delta = payload?.text || payload?.delta || ''
    if (!delta) return
    liveTextRef.value += delta
    if (mode === 'generate') {
      editableReport.value = liveTextRef.value
      chatMessages.value[assistantIndex].content = '正在生成晋升建议，正文已同步到左侧。'
    } else {
      const liveDisplay = getLiveChatDisplay(liveTextRef.value)
      chatMessages.value[assistantIndex].thinking = liveDisplay.thinking
      chatMessages.value[assistantIndex].content = liveDisplay.content
    }
    await scrollToBottom()
    return
  }
  if (event === 'done') {
    if (payload?.status === 'failed' || payload?.error) {
      const errorText = payload?.error || 'Dify workflow failed without an error message.'
      workflowError.value = errorText
      workflowResult.value = null
      chatMessages.value[assistantIndex].content = `生成失败：${errorText}`
      failAssistantRun(chatMessages.value[assistantIndex])
    } else {
      workflowError.value = ''
      workflowResult.value = payload
      if (mode === 'generate') {
        editableReport.value = payload?.promotion_report || payload?.updated_report || liveTextRef.value || ''
        chatMessages.value[assistantIndex].content = editableReport.value
          ? '生成完成，晋升建议已同步到左侧正文区。'
          : '工作流已完成，但没有返回可用的晋升建议。'
      } else {
        const parsed = splitChatPackage(payload?.chat_reply || payload?.promotion_report || liveTextRef.value || '')
        const reply = payload?.chat_reply && String(payload.chat_reply).includes('CHAT_REPLY:')
          ? parsed.reply
          : (payload?.chat_reply || parsed.reply || '本轮追问完成。')
        const updatedReport = payload?.updated_report || parsed.report || ''
        if (updatedReport) editableReport.value = updatedReport
        chatMessages.value[assistantIndex].thinking = payload?.thinking_summary || parsed.thinking || ''
        chatMessages.value[assistantIndex].content = reply
      }
      finishAssistantRun(chatMessages.value[assistantIndex], payload, mode)
    }
    await scrollToBottom()
  }
}

async function sendPromotionMessage(text, mode = 'chat') {
  const query = String(text || '').trim()
  if (!query || chatLoading.value) return
  if (!targetPosition.value.trim()) {
    workflowError.value = '请先选择或填写目标晋升岗位'
    return
  }

  workflowError.value = ''

  chatMessages.value.push({ role: 'user', content: mode === 'generate' ? '请生成当前晋升建议正文' : query })
  const assistantIndex = chatMessages.value.length
  const assistantMessage = createAssistantMessage(mode === 'generate' ? '已收到，正在生成晋升建议正文。' : '已收到，正在处理追问。')
  chatMessages.value.push(assistantMessage)
  startElapsedTimer(assistantIndex)
  chatLoading.value = true
  await scrollToBottom()

  try {
    const resp = await fetch(mode === 'chat' ? '/api/promotion-agent/chat/stream' : '/api/promotion-agent/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        query,
        followup_question: mode === 'chat' ? query : '',
        current_report: editableReport.value,
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
    const liveTextRef = { value: '' }
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split(/\n\n/)
      buffer = blocks.pop() || ''

      for (const block of blocks) {
        const parsed = parseSseBlock(block)
        if (parsed) await handleStreamEvent(parsed.event, parsed.payload, assistantIndex, liveTextRef, mode)
      }
    }

    const last = parseSseBlock(buffer)
    if (last) await handleStreamEvent(last.event, last.payload, assistantIndex, liveTextRef, mode)
  } catch (e) {
    workflowError.value = e.message
    chatMessages.value[assistantIndex].content = `生成失败：${e.message}`
    failAssistantRun(chatMessages.value[assistantIndex])
  } finally {
    chatLoading.value = false
    userInput.value = ''
    await scrollToBottom()
  }
}

function generateReport() {
  sendPromotionMessage('请基于当前表单生成晋升决策建议', 'generate')
}

function sendMessage() {
  sendPromotionMessage(userInput.value)
}

onMounted(fetchPositionOptions)
onUnmounted(stopElapsedTimer)
</script>

<template>
  <div class="promotion-agent-page">
    <section class="agent-main">
      <div class="page-actions">
        <button class="btn-primary" :disabled="chatLoading" @click="generateReport">
          {{ chatLoading ? '生成中...' : '生成晋升建议' }}
        </button>
      </div>

      <div class="workflow-form">
        <div class="form-grid">
          <div class="form-group form-group-wide">
            <label for="target-position">目标晋升岗位</label>
            <input
              id="target-position"
              v-model="targetPosition"
              list="promotion-position-options"
              type="text"
              placeholder="例如：信息技术总监"
            />
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
            <textarea
              id="promotion-rule"
              v-model="promotionRule"
              rows="4"
              placeholder="例如：绩效低于 4 暂缓，必须完成核心培训"
            />
          </div>

          <div class="form-group form-group-wide">
            <label for="manager-comment">部门经理评价</label>
            <textarea
              id="manager-comment"
              v-model="managerComment"
              rows="4"
              placeholder="例如：优先考虑技术管理经验和跨部门协作能力"
            />
          </div>
        </div>
      </div>

      <div class="result-card">
        <div class="result-header">
          <h3>晋升建议</h3>
          <span v-if="workflowResult?.workflow_run_id" class="run-id">{{ workflowResult.workflow_run_id }}</span>
        </div>

        <textarea
          v-model="editableReport"
          class="report-editor"
          wrap="soft"
          placeholder="这里会显示晋升建议正文，你可以直接修改为最终版本。"
        ></textarea>

        <div class="report-preview-wrap">
          <div class="preview-label">预览</div>
          <div class="report-preview markdown-body" v-html="renderMarkdown(editableReport)"></div>
        </div>

        <details v-if="hasDebugOutput" class="debug-details">
          <summary>调试信息</summary>
          <p class="debug-desc">这里是原始查询结果，仅用于排查和审计，不作为最终交付内容。</p>
          <div v-if="workflowResult?.position_profile_raw" class="raw-block">
            <h4>岗位画像查询原文</h4>
            <pre>{{ workflowResult.position_profile_raw }}</pre>
          </div>
          <div v-if="workflowResult?.candidate_pool_raw" class="raw-block">
            <h4>候选人池查询原文</h4>
            <pre>{{ workflowResult.candidate_pool_raw }}</pre>
          </div>
          <div v-if="workflowResult?.raw" class="raw-block">
            <h4>Dify 原始响应</h4>
            <pre>{{ JSON.stringify(workflowResult.raw, null, 2) }}</pre>
          </div>
        </details>
      </div>

      <div v-if="workflowError" class="error-state">{{ workflowError }}</div>
    </section>

    <aside class="chat-sidebar">
      <div class="chat-header promotion-chat-header">
        <span class="chat-avatar">HR</span>
        <div>
          <p class="chat-title">晋升决策辅助</p>
          <p class="chat-subtitle">多轮对话</p>
        </div>
      </div>

      <div class="chat-messages" ref="chatBox">
        <div v-for="(msg, i) in chatMessages" :key="i" :class="['chat-msg', msg.role]">
          <div class="msg-bubble">
            <div v-if="msg.role === 'assistant' && msg.status" class="run-meta">
              <span :class="['run-dot', msg.status]"></span>
              <span>{{ msg.status === 'running' ? '正在运行' : msg.status === 'failed' ? '执行失败' : '已完成' }}</span>
              <span>{{ formatElapsed(msg.elapsedMs) }}</span>
            </div>
            <div v-if="msg.currentStep" class="current-step">当前步骤：{{ msg.currentStep }}</div>
            <details v-if="msg.role === 'assistant' && (msg.steps?.length || msg.thinking || msg.status === 'done')" class="run-details">
              <summary>执行详情</summary>
              <div v-if="msg.steps?.length" class="step-list">
                <div v-for="step in msg.steps" :key="step.title" :class="['step-item', step.status]">
                  <span class="step-icon">{{ step.status === 'error' ? '!' : step.status === 'running' ? '…' : '✓' }}</span>
                  <span>{{ step.title }}</span>
                </div>
              </div>
              <div v-if="msg.tools" class="tool-list">
                <div>DATABASE：{{ toolLabel(msg.tools.database) }}</div>
                <div>REVISE_REPORT：{{ toolLabel(msg.tools.reviseReport) }}</div>
                <div>左侧正文：{{ msg.updatedReport ? '已更新' : '未更新' }}</div>
              </div>
              <details v-if="msg.thinking" class="thinking-details">
                <summary>思考摘要</summary>
                <div v-html="renderMarkdown(msg.thinking)"></div>
              </details>
            </details>
            <div v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
      </div>

      <div class="chat-input-wrap">
        <input
          v-model="userInput"
          class="chat-input"
          placeholder="继续追问候选人、规则或决策理由..."
          :disabled="chatLoading"
          @keyup.enter="sendMessage"
        />
        <button class="chat-send promotion-send" :disabled="chatLoading || !userInput.trim()" @click="sendMessage">
          发送
        </button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.promotion-agent-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(320px, 28vw, 420px);
  gap: 18px;
  align-items: stretch;
  width: 100%;
  min-height: calc(100vh - 120px);
}

.agent-main {
  min-width: 0;
  display: grid;
  gap: 16px;
  align-content: start;
  overflow-y: auto;
  padding-right: 2px;
}

.page-actions {
  display: flex;
  justify-content: flex-end;
}

.workflow-form,
.result-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px;
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
.form-group textarea,
.report-editor {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  color: #1e293b;
  background: #fff;
  outline: none;
}

.form-group textarea {
  resize: vertical;
  line-height: 1.6;
}

.report-editor {
  min-height: 260px;
  resize: vertical;
  line-height: 1.7;
  font-family: inherit;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.form-group input:focus,
.form-group textarea:focus,
.report-editor:focus,
.chat-input:focus {
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
}

.btn-primary,
.chat-send,
.ghost-btn {
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary,
.chat-send {
  color: #fff;
  background: #0d9488;
}

.btn-primary {
  padding: 10px 18px;
}

.ghost-btn {
  padding: 8px 12px;
  background: #eef2f7;
  color: #334155;
}

.btn-primary:hover,
.chat-send:hover {
  background: #0f766e;
}

.ghost-btn:hover {
  background: #e2e8f0;
}

.btn-primary:disabled,
.chat-send:disabled,
.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hint-error,
.error-state {
  color: #b91c1c;
  font-size: 13px;
}

.error-state {
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.result-header h3 {
  margin: 0;
  color: #1e293b;
  font-size: 15px;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.run-id {
  color: #64748b;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.report-preview-wrap {
  margin-top: 14px;
}

.preview-label {
  margin-bottom: 8px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.report-preview {
  max-height: 36vh;
  overflow: auto;
  padding: 14px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  min-width: 0;
}

.markdown-body {
  color: #14532d;
  font-size: 14px;
  line-height: 1.75;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.markdown-body :deep(table),
.msg-bubble :deep(table) {
  display: block;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}

.markdown-body :deep(th),
.markdown-body :deep(td),
.msg-bubble :deep(th),
.msg-bubble :deep(td) {
  border: 1px solid #cbd5e1;
  padding: 6px 8px;
  white-space: normal;
  overflow-wrap: anywhere;
  font-size: 13px;
}

.markdown-body :deep(p),
.markdown-body :deep(ul),
.markdown-body :deep(ol),
.msg-bubble :deep(p),
.msg-bubble :deep(ul),
.msg-bubble :deep(ol) {
  margin: 0 0 10px;
}

.markdown-body :deep(code),
.msg-bubble :deep(code) {
  white-space: pre-wrap;
  word-break: break-word;
}

.markdown-body :deep(pre),
.msg-bubble :deep(pre) {
  max-width: 100%;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.debug-details {
  margin-top: 14px;
  border-top: 1px solid #bbf7d0;
  padding-top: 12px;
}

.debug-details summary {
  cursor: pointer;
  color: #166534;
  font-size: 13px;
  font-weight: 600;
}

.debug-desc {
  margin: 10px 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.raw-block {
  margin-top: 10px;
}

.raw-block h4 {
  margin: 0 0 6px;
  color: #334155;
  font-size: 13px;
}

.raw-block pre {
  max-height: 260px;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-sidebar {
  width: 100%;
  min-width: 0;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: calc(100vh - 160px);
  height: calc(100vh - 160px);
  max-height: none;
  position: sticky;
  top: 0;
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 13px;
  font-weight: 700;
}

.chat-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.chat-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  opacity: 0.82;
}

.chat-messages {
  flex: 1;
  min-height: 0;
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
  min-width: 0;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
  overflow-wrap: anywhere;
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

.thinking-details {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f1f5f9;
  color: #475569;
  font-size: 13px;
}

.thinking-details summary {
  cursor: pointer;
  color: #0f766e;
  font-weight: 700;
}

.thinking-details :deep(p) {
  margin: 8px 0 0;
}

.run-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.run-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #94a3b8;
}

.run-dot.running {
  background: #0d9488;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

.run-dot.done {
  background: #16a34a;
}

.run-dot.failed {
  background: #dc2626;
}

.current-step {
  margin-bottom: 8px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 600;
}

.run-details {
  margin: 8px 0 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
  color: #475569;
  font-size: 13px;
}

.run-details summary {
  cursor: pointer;
  color: #334155;
  font-weight: 700;
}

.step-list,
.tool-list {
  display: grid;
  gap: 5px;
  margin-top: 8px;
}

.step-item {
  display: flex;
  gap: 7px;
  align-items: center;
}

.step-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  line-height: 1;
}

.step-item.running .step-icon {
  background: #ccfbf1;
  color: #0f766e;
}

.step-item.error .step-icon {
  background: #fee2e2;
  color: #b91c1c;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.45; }
  50% { opacity: 1; }
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
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.chat-send {
  flex: 0 0 auto;
  padding: 10px 16px;
  color: #fff;
  background: #0d9488;
  border: none;
  border-radius: 8px;
}

.chat-send:hover {
  background: #0f766e;
}

@media (max-width: 1180px) {
  .promotion-agent-page {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .chat-sidebar {
    position: static;
    height: auto;
    min-height: 520px;
  }
}

@media (max-width: 760px) {
  .page-actions {
    justify-content: stretch;
  }

  .btn-primary {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-group-wide {
    grid-column: auto;
  }

  .workflow-form,
  .result-card {
    padding: 14px;
  }
}
</style>


