<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

const potentialList = ref([])
const loading = ref(true)
const error = ref('')

// AI 聊天相关
const chatMessages = ref([
  { role: 'assistant', content: '您好！我是**人才潜力分析助手**，可以回答关于员工潜力数据的问题。\n\n例如：\n- "对某员工进行潜力评估"\n- "S级高潜员工有哪些？"\n- "各等级人数分布如何？"' }
])
const userInput = ref('')
const chatLoading = ref(false)
const conversationId = ref('')

// 渲染 Markdown，过滤 AI 的思考标签
function renderMarkdown(text) {
  if (!text) return ''
  // 过滤 <think>...</think> 思考链标签
  let clean = text.replace(/<think>[\s\S]*?<\/think>/g, '')
  // 过滤纯 think 开头无闭合的情况
  clean = clean.replace(/^<think>.*$/gm, '')
  return marked.parse(clean)
}

onMounted(async () => {
  try {
    const resp = await fetch('/api/potential')
    potentialList.value = await resp.json()
  } catch {
    error.value = '加载潜力数据失败'
  } finally {
    loading.value = false
  }
})

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
          potential_data: JSON.stringify(potentialList.value.slice(0, 20))
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
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '❌ 网络错误，请稍后重试' })
  } finally {
    chatLoading.value = false
  }
}
</script>

<template>
  <div class="potential-layout">
    <!-- 左侧：潜力数据列表 -->
    <div class="potential-main">
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="toolbar-title">员工潜力列表</span>
          <span class="toolbar-count">共 {{ potentialList.length }} 人</span>
        </div>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="error" class="error-state">{{ error }}</div>

      <div v-else class="table-wrap">
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
            <tr v-for="emp in potentialList" :key="emp.employee_id">
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
    </div>

    <!-- 右侧：AI 对话助手 -->
    <div class="chat-sidebar">
      <div class="chat-header">
        <span class="chat-avatar">🤖</span>
        <div>
          <p class="chat-title">人才潜力分析助手</p>
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
          placeholder="输入你的问题..."
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

.cell-score {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-bar {
  position: absolute;
  left: 16px;
  height: 6px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 3px;
  opacity: 0.15;
  max-width: calc(100% - 32px);
}

.score-text {
  position: relative;
  font-weight: 600;
  font-family: 'SF Mono', 'Consolas', monospace;
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

/* Markdown 渲染内容样式 */
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
  padding: 8px 16px;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.chat-send:hover {
  background: #4f46e5;
}

.chat-send:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}
</style>
