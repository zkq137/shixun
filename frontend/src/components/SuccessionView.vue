<script setup>
import { ref, onMounted, watch } from 'vue'

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
</script>

<template>
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

@media (max-width: 760px) {
  .search-box {
    min-width: 100%;
    flex-direction: column;
  }
}
</style>
