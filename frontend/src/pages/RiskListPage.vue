<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getRiskAlerts } from '../api'

const loading = ref(true)
const errorMsg = ref('')
const risks = ref([])
const selectedLevel = ref('全部')

const filteredRisks = computed(() => {
  if (selectedLevel.value === '全部') {
    return risks.value
  }

  return risks.value.filter((item) => item.riskLevel === selectedLevel.value)
})

async function loadData() {
  loading.value = true
  errorMsg.value = ''

  try {
    risks.value = await getRiskAlerts()
  } catch (error) {
    errorMsg.value = String(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <main class="page">
    <header class="page-header">
      <div>
        <p class="eyebrow">人才流失风险预警</p>
        <h1>风险名单</h1>
      </div>
      <div class="actions">
        <RouterLink class="ghost-btn" :to="{ name: 'risk-overview' }">返回总览</RouterLink>
      </div>
    </header>

    <section class="toolbar panel">
      <label>
        风险等级
        <select v-model="selectedLevel">
          <option>全部</option>
          <option>高</option>
          <option>中</option>
        </select>
      </label>
      <span class="count">当前 {{ filteredRisks.length }} 人</span>
    </section>

    <section v-if="loading" class="panel">数据加载中...</section>
    <section v-else-if="errorMsg" class="panel error">加载失败：{{ errorMsg }}</section>

    <section v-else class="panel">
      <table>
        <thead>
          <tr>
            <th>员工</th>
            <th>部门</th>
            <th>风险等级</th>
            <th>风险原因</th>
            <th>建议动作</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredRisks" :key="item.employee">
            <td>{{ item.employee }}</td>
            <td>{{ item.department }}</td>
            <td>{{ item.riskLevel }}风险</td>
            <td>{{ item.reason }}</td>
            <td>{{ item.action }}</td>
            <td>
              <RouterLink
                class="detail-link"
                :to="{ name: 'risk-detail', params: { employee: item.employee } }"
              >
                查看员工详情
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header,
.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.eyebrow {
  margin: 0;
  color: #0f766e;
  font-weight: 600;
}

h1 {
  margin: 8px 0 0;
}

.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 16px;
}

.ghost-btn,
.detail-link {
  text-decoration: none;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  color: #0f172a;
  padding: 10px 14px;
  border-radius: 10px;
}

.detail-link {
  display: inline-block;
  padding: 8px 12px;
  border-radius: 10px;
  background: #0f766e;
  color: #fff;
}

label {
  display: flex;
  align-items: center;
  gap: 8px;
}

select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 10px;
}

.count {
  color: #475569;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 12px 10px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
}

.error {
  color: #b91c1c;
}

@media (max-width: 900px) {
  .page-header,
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  table {
    display: block;
    overflow-x: auto;
  }
}
</style>
