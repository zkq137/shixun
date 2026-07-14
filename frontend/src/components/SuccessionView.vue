<script setup>
import { ref, onMounted, watch } from 'vue'

const targetPosition = ref('')
const promotionRule = ref('')
const managerComment = ref('')
const createdBy = ref('HR')
const workflowLoading = ref(false)
const workflowResult = ref(null)
const workflowError = ref('')
const positionOptions = ref([])
const positionError = ref('')

async function fetchPositionOptions() {
  positionError.value = ''
  try {
    const resp = await fetch('/api/succession/positions')
    if (!resp.ok) throw new Error(`请求失败: ${resp.status}`)
    positionOptions.value = await resp.json()
  } catch (e) {
    positionError.value = `岗位列表加载失败: ${e.message}`
    positionOptions.value = []
  }
}

async function submitWorkflow() {
  if (!targetPosition.value.trim()) {
    workflowError.value = '请填写目标晋升岗位'
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
        target_position: targetPosition.value.trim(),
        promotion_rule: promotionRule.value.trim(),
        manager_comment: managerComment.value.trim(),
        created_by: createdBy.value.trim() || 'HR',
      }),
    })
    const data = await resp.json()
    if (!resp.ok) {
      workflowError.value = data.error || '晋升决策生成失败'
    } else {
      workflowResult.value = data
    }
  } catch (e) {
    workflowError.value = `网络错误: ${e.message}`
  } finally {
    workflowLoading.value = false
  }
}

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
  searchTimer = setTimeout(() => {
    fetchCandidates()
  }, 300)
})

onMounted(() => {
  fetchCandidates()
  fetchPositionOptions()
})
</script>

<template>
  <section class="panel">
    <h2>晋升决策辅助 Agent</h2>
    <p class="section-desc">选择目标晋升岗位，补充 HR 规则和经理评价，由本地 Dify 工作流生成可解释的晋升建议。</p>

    <div class="workflow-form">
      <div class="form-grid">
        <div class="form-group form-group-wide">
          <label for="target-position">目标晋升岗位</label>
          <input
            id="target-position"
            v-model="targetPosition"
            list="position-options"
            type="text"
            placeholder="例如：信息技术总监"
          />
          <datalist id="position-options">
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
            placeholder="例如：绩效低于4暂缓，必须完成核心培训"
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

      <div class="workflow-actions">
        <button class="btn-primary" :disabled="workflowLoading" @click="submitWorkflow">
          <span v-if="workflowLoading">生成中...</span>
          <span v-else>生成晋升建议</span>
        </button>
      </div>
    </div>

    <div v-if="workflowError" class="workflow-error">{{ workflowError }}</div>

    <div v-if="workflowResult" class="workflow-result">
      <div class="result-header">
        <h3>晋升建议</h3>
        <span v-if="workflowResult.workflow_run_id" class="run-id">{{ workflowResult.workflow_run_id }}</span>
      </div>
      <div class="result-content">
        <pre>{{ workflowResult.promotion_report || '工作流未返回 promotion_report，请展开原始结果查看。' }}</pre>
      </div>

      <details v-if="workflowResult.position_profile_raw" class="raw-details">
        <summary>查看岗位画像原始结果</summary>
        <pre>{{ workflowResult.position_profile_raw }}</pre>
      </details>

      <details v-if="workflowResult.candidate_pool_raw" class="raw-details">
        <summary>查看候选人池原始结果</summary>
        <pre>{{ workflowResult.candidate_pool_raw }}</pre>
      </details>

      <details class="raw-details">
        <summary>查看完整工作流响应</summary>
        <pre>{{ JSON.stringify(workflowResult.raw || workflowResult, null, 2) }}</pre>
      </details>
    </div>
  </section>

  <section class="panel">
    <div class="section-header">
      <h2>继任候选人列表</h2>
      <div class="search-box">
        <input
          v-model="searchPosition"
          type="text"
          placeholder="按岗位名称筛选..."
          class="search-input"
        />
        <input
          v-model="searchCandidate"
          type="text"
          placeholder="按员工姓名筛选..."
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
  border-radius: 8px;
  padding: 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.form-group {
  min-width: 0;
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
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
  box-sizing: border-box;
}

.form-group textarea {
  resize: vertical;
  line-height: 1.6;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: #14b8a6;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.15);
}

.hint-error {
  margin: 6px 0 0;
  color: #b91c1c;
  font-size: 12px;
}

.workflow-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
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
  border-radius: 8px;
  padding: 16px 20px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.workflow-result h3 {
  margin: 0;
  font-size: 15px;
  color: #166534;
}

.run-id {
  color: #64748b;
  font-size: 12px;
}

.result-content pre,
.raw-details pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #14532d;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 420px;
  overflow-y: auto;
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
  margin-top: 10px;
  color: #334155;
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

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-group-wide {
    grid-column: span 1;
  }

  .search-box {
    min-width: 100%;
    flex-direction: column;
  }

  .workflow-actions {
    justify-content: stretch;
  }

  .btn-primary {
    width: 100%;
  }
}
</style>
