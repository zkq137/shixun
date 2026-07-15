<script setup>
import { ref, onMounted, watch } from 'vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

// ── 候选人列表 ──
const candidates = ref([])
const candidatesLoading = ref(false)
const candidatesError = ref('')
const searchPosition = ref('')
const searchCandidate = ref('')
let searchTimer = null

async function fetchCandidates() {
  candidatesLoading.value = true
  candidatesError.value = ''
  try {
    const params = new URLSearchParams()
    if (searchPosition.value.trim()) params.set('position', searchPosition.value.trim())
    if (searchCandidate.value.trim()) params.set('candidate', searchCandidate.value.trim())
    const query = params.toString() ? `?${params.toString()}` : ''
    const resp = await fetch(`/api/succession/candidates${query}`)
    if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
    candidates.value = await resp.json()
  } catch (e) {
    candidatesError.value = `加载数据失败: ${e.message}`
    candidates.value = []
  } finally {
    candidatesLoading.value = false
  }
}

watch([searchPosition, searchCandidate], () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchCandidates, 300)
})

onMounted(fetchCandidates)

// ── 继任梯队工作流 ──
const targetPositionName = ref(localStorage.getItem('succ_position_name') || '')
const targetPositionLevel = ref(localStorage.getItem('succ_position_level') || '')
const targetDepartment = ref(localStorage.getItem('succ_department') || '')
const departmentOptions = ref([])
const levelOptions = ['员工层', '主管层', '经理层', '总监层', '高管层', '决策层']
const workflowLoading = ref(false)
const workflowResult = ref(null)
const workflowError = ref('')

// 持久化表单值
watch(targetPositionName, v => localStorage.setItem('succ_position_name', v))
watch(targetPositionLevel, v => localStorage.setItem('succ_position_level', v))
watch(targetDepartment, v => localStorage.setItem('succ_department', v))

async function fetchDepartmentOptions() {
  try {
    const resp = await fetch('/api/departments')
    if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
    departmentOptions.value = await resp.json()
  } catch {
    // 忽略
  }
}

function renderMarkdown(text) {
  if (!text) return ''
  const clean = String(text).replace(/<think>[\s\S]*?<\/think>/g, '').replace(/^<think>.*$/gm, '')
  return marked.parse(clean)
}

async function runSuccessionWorkflow() {
  if (!targetPositionName.value.trim()) {
    workflowError.value = '请输入目标岗位名称'
    return
  }

  workflowLoading.value = true
  workflowError.value = ''
  workflowResult.value = null

  const targetPosition = [
    targetPositionName.value.trim(),
    targetPositionLevel.value.trim(),
    targetDepartment.value.trim()
  ].filter(Boolean).join(' - ')

  try {
    const resp = await fetch('/api/succession/workflow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_position: targetPosition,
        target_position_name: targetPositionName.value.trim(),
        target_position_level: targetPositionLevel.value.trim(),
        target_department: targetDepartment.value.trim(),
        created_by: 'HR',
      }),
    })

    const data = await resp.json()
    if (!resp.ok) throw new Error(data.error || `请求失败: ${resp.status}`)
    if (data.status === 'failed' || data.error) {
      throw new Error(data.error || '工作流执行失败')
    }
    workflowResult.value = data
  } catch (e) {
    workflowError.value = e.message
  } finally {
    workflowLoading.value = false
  }
}

onMounted(fetchDepartmentOptions)
</script>

<template>
  <!-- ── 继任梯队生成工作流 ── -->
  <section class="panel">
    <div class="section-header">
      <div>
        <h2>继任梯队生成</h2>
        <p class="section-desc">基于 Dify AI 工作流，为目标岗位自动生成继任梯队与晋升建议。</p>
      </div>
      <button class="btn-primary" :disabled="workflowLoading" @click="runSuccessionWorkflow">
        {{ workflowLoading ? '生成中...' : '生成继任梯队' }}
      </button>
    </div>

    <div class="workflow-form">
      <div class="form-grid">
        <div class="form-group">
          <label for="wf-target-position-name">目标岗位名称</label>
          <input id="wf-target-position-name" v-model="targetPositionName" type="text" placeholder="例如：信息技术总监" />
        </div>

        <div class="form-group">
          <label for="wf-target-position-level">岗位层级</label>
          <select id="wf-target-position-level" v-model="targetPositionLevel">
            <option value="" disabled>请选择层级</option>
            <option v-for="level in levelOptions" :key="level" :value="level">{{ level }}</option>
          </select>
        </div>

        <div class="form-group">
          <label for="wf-target-department">岗位部门</label>
          <select id="wf-target-department" v-model="targetDepartment">
            <option value="" disabled>请选择部门</option>
            <option v-for="dept in departmentOptions" :key="dept" :value="dept">{{ dept }}</option>
          </select>
        </div>

      </div>
    </div>

    <div v-if="workflowLoading" class="loading-state">正在调用 Dify 工作流，请稍候...</div>
    <div v-else-if="workflowError" class="error-state">{{ workflowError }}</div>

    <div v-if="workflowResult" class="success-state">继任梯队生成成功</div>
  </section>

  <!-- ── 继任候选人列表 ── -->
  <section class="panel">
    <div class="section-header">
      <div>
        <h2>继任候选人列表</h2>
        <p class="section-desc">查看关键岗位继任梯队与候选人匹配情况。</p>
      </div>
      <div class="search-box">
        <input v-model="searchPosition" type="text" placeholder="按岗位名称筛选..." class="search-input" />
        <input v-model="searchCandidate" type="text" placeholder="按员工姓名筛选..." class="search-input" />
      </div>
    </div>

    <div v-if="candidatesLoading" class="loading-state">加载中...</div>
    <div v-else-if="candidatesError" class="error-state">{{ candidatesError }}</div>
    <div v-else-if="candidates.length === 0" class="loading-state">暂无数据</div>
    <table v-else>
      <thead>
        <tr>
          <th>目标岗位部门</th>
          <th>目标岗位层级</th>
          <th>目标岗位</th>
          <th>候选人</th>
          <th>梯队</th>
          <th>匹配分</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in candidates" :key="`${item.position}-${item.candidate}`">
          <td>{{ item.department }}</td>
          <td>{{ item.positionLevel }}</td>
          <td>{{ item.position }}</td>
          <td>{{ item.candidate }}</td>
          <td><span class="badge badge-ready">{{ item.readiness }}</span></td>
          <td><strong>{{ item.matchScore }}</strong></td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.section-header h2 {
  margin: 0;
}

.section-desc {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 14px;
}

.search-box {
  display: flex;
  gap: 8px;
  min-width: 400px;
}

.search-input {
  flex: 1;
  min-width: 0;
  padding: 10px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #f8fafc;
}

.search-input:focus {
  border-color: #14b8a6;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.15);
  background: #fff;
}

.loading-state {
  padding: 32px;
  text-align: center;
  color: #64748b;
}

.error-state {
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #b91c1c;
  font-size: 14px;
}

.success-state {
  padding: 12px 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  color: #15803d;
  font-size: 14px;
}

/* ── 工作流表单 ── */
.workflow-form {
  margin-bottom: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group-wide {
  grid-column: 1 / -1;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.form-group input,
.form-group textarea,
.form-group select {
  padding: 10px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #f8fafc;
  font-family: inherit;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #14b8a6;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.15);
  background: #fff;
}

.hint-error {
  margin: 4px 0 0;
  font-size: 12px;
  color: #b91c1c;
}

/* ── 结果卡片 ── */
.result-card {
  margin-top: 16px;
  padding: 20px;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 10px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.result-header h3 {
  margin: 0;
  font-size: 16px;
}

.run-id {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.raw-details {
  margin-top: 12px;
  font-size: 13px;
}

.raw-details summary {
  cursor: pointer;
  color: #0d9488;
  font-weight: 500;
}

.raw-details pre {
  margin-top: 8px;
  padding: 12px;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── Markdown ── */
:deep(.markdown-body) {
  line-height: 1.7;
  color: #1e293b;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3),
:deep(.markdown-body h4) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
}

:deep(.markdown-body h1) { font-size: 18px; }
:deep(.markdown-body h2) { font-size: 16px; }
:deep(.markdown-body h3) { font-size: 14px; }
:deep(.markdown-body p) { margin: 6px 0; }
:deep(.markdown-body ul),
:deep(.markdown-body ol) { padding-left: 20px; }
:deep(.markdown-body li) { margin: 4px 0; }
:deep(.markdown-body table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}
:deep(.markdown-body th),
:deep(.markdown-body td) {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  text-align: left;
}
:deep(.markdown-body th) {
  background: #f1f5f9;
  font-weight: 600;
}
:deep(.markdown-body code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
:deep(.markdown-body pre code) {
  background: none;
  padding: 0;
}

/* ── 按钮 ── */
.btn-primary {
  padding: 10px 24px;
  background: #14b8a6;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.btn-primary:hover:not(:disabled) {
  background: #0d9488;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 760px) {
  .search-box {
    min-width: 100%;
    flex-direction: column;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
