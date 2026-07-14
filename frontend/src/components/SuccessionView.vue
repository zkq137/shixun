<script setup>
import { ref, onMounted, watch } from 'vue'

// ── 工作流部分 ──
const department = ref('')
const level = ref('')
const positionName = ref('')
const workflowLoading = ref(false)
const workflowResult = ref(null)
const workflowError = ref('')
const departments = ref([])

async function fetchDepartments() {
  try {
    const resp = await fetch('/api/succession/departments')
    if (resp.ok) departments.value = await resp.json()
  } catch {}
}

async function submitWorkflow() {
  if (!department.value || !level.value || !positionName.value) {
    workflowError.value = '请填写完整的岗位信息'
    return
  }
  workflowLoading.value = true
  workflowError.value = ''
  workflowResult.value = null
  try {
    const resp = await fetch('/api/succession/workflow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        department: department.value,
        level: level.value,
        position: positionName.value,
      }),
    })
    const data = await resp.json()
    if (!resp.ok) {
      workflowError.value = data.error || '请求失败'
    } else {
      workflowResult.value = data
    }
  } catch (e) {
    workflowError.value = `网络错误: ${e.message}`
  } finally {
    workflowLoading.value = false
  }
}

// ── 数据库表格部分 ──
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
    if (!resp.ok) {
      throw new Error(`请求失败: ${resp.status}`)
    }
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
  searchTimer = setTimeout(() => {
    fetchCandidates()
  }, 300)
})

onMounted(() => {
  fetchCandidates()
  fetchDepartments()
})
</script>

<template>
  <!-- 第一部分：工作流接入 -->
  <section class="panel">
    <h2>🤖 继任梯队智能生成</h2>
    <p class="section-desc">输入岗位信息，调用 AI 工作流自动生成继任梯队</p>
    <div class="workflow-form">
      <div class="form-row">
        <div class="form-group">
          <label for="dept">岗位部门</label>
          <select id="dept" v-model="department">
            <option value="" disabled>请选择部门</option>
            <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>
        <div class="form-group">
          <label for="lvl">岗位层级</label>
          <select id="lvl" v-model="level">
            <option value="" disabled>请选择层级</option>
            <option value="员工层">员工层</option>
            <option value="主管层">主管层</option>
            <option value="经理层">经理层</option>
            <option value="总监层">总监层</option>
            <option value="高管层">高管层</option>
            <option value="决策层">决策层</option>
          </select>
        </div>
        <div class="form-group">
          <label for="pos">岗位名称</label>
          <input id="pos" v-model="positionName" type="text" placeholder="例如：高级算法工程师" />
        </div>
        <div class="form-group form-action">
          <label>&nbsp;</label>
          <button class="btn-primary" :disabled="workflowLoading" @click="submitWorkflow">
            <span v-if="workflowLoading">⏳ 生成中...</span>
            <span v-else>生成继任梯队</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 工作流结果 -->
    <div v-if="workflowError" class="workflow-error">{{ workflowError }}</div>
    <div v-if="workflowResult" class="workflow-result">
      <h3>📋 工作流返回结果</h3>
      <div class="result-content">
        <pre>{{ JSON.stringify(workflowResult, null, 2) }}</pre>
      </div>
    </div>
  </section>

  <!-- 第二部分：数据库表格 -->
  <section class="panel">
    <div class="section-header">
      <h2>📋 继任列表</h2>
      <div class="search-box">
        <input
          v-model="searchPosition"
          type="text"
          placeholder="🔍 按岗位名称筛选..."
          class="search-input"
        />
        <input
          v-model="searchCandidate"
          type="text"
          placeholder="🔍 按员工姓名筛选..."
          class="search-input"
        />
      </div>
    </div>

    <div v-if="candidatesLoading" class="loading-state">加载中...</div>
    <div v-else-if="candidatesError" class="workflow-error">{{ candidatesError }}</div>
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
.section-desc {
  color: #64748b;
  font-size: 14px;
  margin: -8px 0 16px;
}

.workflow-form {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
}

.form-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-group {
  flex: 1;
  min-width: 160px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
}

.form-group input:focus,
.form-group select:focus {
  border-color: #14b8a6;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.15);
}

.form-action {
  flex: 0 0 auto;
  min-width: auto;
}

.btn-primary {
  padding: 10px 24px;
  background: linear-gradient(135deg, #14b8a6, #0d9488);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  white-space: nowrap;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.workflow-error {
  margin-top: 12px;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #b91c1c;
  font-size: 14px;
}

.workflow-result {
  margin-top: 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 16px 20px;
}

.workflow-result h3 {
  margin: 0 0 10px;
  font-size: 15px;
  color: #166534;
}

.result-content pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #166534;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.section-header h2 {
  margin: 0;
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
</style>
