<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getRiskAlerts } from '../api'

const loading = ref(true)
const errorMsg = ref('')
const risks = ref([])

const riskStats = computed(() => {
  const highCount = risks.value.filter((item) => item.riskLevel === '高').length
  const mediumCount = risks.value.filter((item) => item.riskLevel === '中').length
  const departments = new Set(risks.value.map((item) => item.department)).size

  return {
    total: risks.value.length,
    highCount,
    mediumCount,
    departments
  }
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
        <h1>风险总览</h1>
        <p class="desc">先看整体风险分布，再进入风险名单和员工详情。</p>
      </div>
      <div class="actions">
        <RouterLink class="ghost-btn" :to="{ name: 'dashboard' }">返回首页</RouterLink>
        <RouterLink class="solid-btn" :to="{ name: 'risk-list' }">进入风险名单</RouterLink>
      </div>
    </header>

    <section v-if="loading" class="panel">数据加载中...</section>
    <section v-else-if="errorMsg" class="panel error">加载失败：{{ errorMsg }}</section>

    <template v-else>
      <section class="stats-grid">
        <article class="stat-card danger">
          <p>高风险人数</p>
          <h3>{{ riskStats.highCount }}</h3>
        </article>
        <article class="stat-card warning">
          <p>中风险人数</p>
          <h3>{{ riskStats.mediumCount }}</h3>
        </article>
        <article class="stat-card">
          <p>风险员工总数</p>
          <h3>{{ riskStats.total }}</h3>
        </article>
        <article class="stat-card">
          <p>涉及部门数</p>
          <h3>{{ riskStats.departments }}</h3>
        </article>
      </section>

      <section class="panel">
        <div class="section-header">
          <h2>重点预警员工</h2>
          <RouterLink class="text-link" :to="{ name: 'risk-list' }">查看全部名单</RouterLink>
        </div>
        <div class="risk-cards">
          <article v-for="item in risks" :key="item.employee" class="risk-card">
            <div class="risk-top">
              <div>
                <h3>{{ item.employee }}</h3>
                <p>{{ item.department }}</p>
              </div>
              <span :class="['badge', item.riskLevel === '高' ? 'danger' : 'warning']">
                {{ item.riskLevel }}风险
              </span>
            </div>
            <p><strong>原因：</strong>{{ item.reason }}</p>
            <p><strong>建议：</strong>{{ item.action }}</p>
            <RouterLink
              class="detail-link"
              :to="{ name: 'risk-detail', params: { employee: item.employee } }"
            >
              查看员工详情
            </RouterLink>
          </article>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header,
.section-header,
.risk-top,
.actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.page-header,
.panel {
  margin-bottom: 16px;
}

.eyebrow {
  margin: 0;
  color: #0f766e;
  font-weight: 600;
}

h1 {
  margin: 8px 0;
}

.desc {
  margin: 0;
  color: #475569;
}

.ghost-btn,
.solid-btn,
.detail-link,
.text-link {
  text-decoration: none;
}

.ghost-btn,
.solid-btn {
  padding: 10px 14px;
  border-radius: 10px;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  color: #0f172a;
}

.solid-btn,
.detail-link {
  background: #0f766e;
  color: #fff;
}

.stats-grid,
.risk-cards {
  display: grid;
  gap: 12px;
}

.stats-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 16px;
}

.stat-card,
.panel,
.risk-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px;
}

.stat-card p,
.risk-card p {
  margin: 0;
  color: #475569;
}

.stat-card h3 {
  margin: 10px 0 0;
  font-size: 28px;
}

.stat-card.danger {
  background: #fef2f2;
}

.stat-card.warning {
  background: #fff7ed;
}

.risk-cards {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.risk-card h3 {
  margin: 0 0 4px;
}

.badge {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.badge.danger {
  background: #fee2e2;
  color: #b91c1c;
}

.badge.warning {
  background: #ffedd5;
  color: #c2410c;
}

.detail-link {
  display: inline-block;
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 10px;
}

.text-link {
  color: #0f766e;
}

.error {
  color: #b91c1c;
}

@media (max-width: 900px) {
  .stats-grid,
  .risk-cards {
    grid-template-columns: 1fr;
  }

  .page-header,
  .section-header,
  .risk-top,
  .actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
