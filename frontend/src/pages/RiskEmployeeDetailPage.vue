<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getRiskAlerts } from '../api'

const props = defineProps({
  employee: {
    type: String,
    required: true
  }
})

const loading = ref(true)
const errorMsg = ref('')
const riskItem = ref(null)

const detailTags = computed(() => {
  if (!riskItem.value) {
    return []
  }

  return riskItem.value.reason
    .split('+')
    .map((item) => item.trim())
    .filter(Boolean)
})

async function loadData() {
  loading.value = true
  errorMsg.value = ''

  try {
    const risks = await getRiskAlerts()
    riskItem.value = risks.find((item) => item.employee === props.employee) || null

    if (!riskItem.value) {
      errorMsg.value = '未找到该员工的风险记录'
    }
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
        <h1>员工风险详情</h1>
      </div>
      <div class="actions">
        <RouterLink class="ghost-btn" :to="{ name: 'risk-list' }">返回风险名单</RouterLink>
        <RouterLink class="ghost-btn" :to="{ name: 'risk-overview' }">返回总览</RouterLink>
      </div>
    </header>

    <section v-if="loading" class="panel">数据加载中...</section>
    <section v-else-if="errorMsg" class="panel error">{{ errorMsg }}</section>

    <template v-else-if="riskItem">
      <section class="hero-card">
        <div>
          <p class="muted">员工姓名</p>
          <h2>{{ riskItem.employee }}</h2>
          <p class="muted">{{ riskItem.department }}</p>
        </div>
        <span :class="['badge', riskItem.riskLevel === '高' ? 'danger' : 'warning']">
          {{ riskItem.riskLevel }}风险
        </span>
      </section>

      <section class="detail-grid">
        <article class="panel">
          <h3>风险原因</h3>
          <div class="tags">
            <span v-for="tag in detailTags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <p class="detail-text">{{ riskItem.reason }}</p>
        </article>

        <article class="panel">
          <h3>干预建议</h3>
          <p class="detail-text">{{ riskItem.action }}</p>
          <button class="solid-btn" type="button">生成干预方案</button>
        </article>
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
.actions,
.hero-card {
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

.hero-card,
.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 18px;
  margin-bottom: 16px;
}

.muted {
  margin: 0;
  color: #64748b;
}

h2 {
  margin: 8px 0;
}

.badge {
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 13px;
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

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #334155;
  font-size: 12px;
}

.detail-text {
  color: #334155;
  line-height: 1.7;
}

.ghost-btn,
.solid-btn {
  text-decoration: none;
  padding: 10px 14px;
  border-radius: 10px;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  color: #0f172a;
}

.solid-btn {
  border: 0;
  background: #0f766e;
  color: #fff;
  cursor: pointer;
}

.error {
  color: #b91c1c;
}

@media (max-width: 900px) {
  .page-header,
  .actions,
  .hero-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
