<script setup>
import { onMounted, ref } from 'vue'
import { getDashboardData } from './api'

const loading = ref(true)
const errorMsg = ref('')
const health = ref(null)
const overview = ref({})
const nineBox = ref([])
const succession = ref([])
const risks = ref([])
const training = ref([])

function pct(value) {
  if (typeof value !== 'number') {
    return '--'
  }
  return `${Math.round(value * 100)}%`
}

async function loadData() {
  loading.value = true
  errorMsg.value = ''

  try {
    const data = await getDashboardData()
    health.value = data.health
    overview.value = data.overview
    nineBox.value = data.nineBox
    succession.value = data.succession
    risks.value = data.risks
    training.value = data.training
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
    <header class="hero">
      <div>
        <p class="tag">HR 智能人才梯队建设平台</p>
        <h1>组织人才盘点与继任决策驾驶舱</h1>
        <p class="sub">聚焦关键岗位继任、流失预警与培养计划，支持 HR 快速制定人才策略。</p>
      </div>
      <button class="refresh" type="button" @click="loadData">刷新数据</button>
    </header>

    <section v-if="loading" class="panel">数据加载中...</section>
    <section v-else-if="errorMsg" class="panel error">加载失败：{{ errorMsg }}</section>

    <template v-else>
      <section class="kpi-grid">
        <article class="kpi-card">
          <p>员工总数</p>
          <h3>{{ overview.employeeCount }}</h3>
        </article>
        <article class="kpi-card">
          <p>关键岗位</p>
          <h3>{{ overview.keyPositions }}</h3>
        </article>
        <article class="kpi-card">
          <p>Ready Now 继任人数</p>
          <h3>{{ overview.readyNowSuccessors }}</h3>
        </article>
        <article class="kpi-card">
          <p>高风险员工</p>
          <h3>{{ overview.highRiskEmployees }}</h3>
        </article>
      </section>

      <section class="panel two-col">
        <div>
          <h2>人才九宫格分布</h2>
          <div class="nine-box-grid">
            <div
              v-for="item in nineBox"
              :key="item.cell"
              :class="['nine-box-item', `level-${item.level}`]"
            >
              <h4>{{ item.cell }}</h4>
              <p>{{ item.count }} 人</p>
            </div>
          </div>
        </div>
        <div>
          <h2>系统状态</h2>
          <p><strong>后端服务：</strong>{{ health?.service }}</p>
          <p><strong>健康检查：</strong>{{ health?.status }}</p>
          <p><strong>数据更新时间：</strong>{{ overview.lastUpdated }}</p>
          <p><strong>培养计划完成率：</strong>{{ pct(overview.completionRate) }}</p>
        </div>
      </section>

      <section class="panel">
        <h2>关键岗位继任候选人</h2>
        <table>
          <thead>
            <tr>
              <th>目标岗位</th>
              <th>候选人</th>
              <th>准备度</th>
              <th>匹配分</th>
              <th>风险</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in succession" :key="`${item.position}-${item.candidate}`">
              <td>{{ item.position }}</td>
              <td>{{ item.candidate }}</td>
              <td>{{ item.readiness }}</td>
              <td>{{ item.matchScore }}</td>
              <td>{{ item.risk }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="panel two-col">
        <div>
          <h2>流失风险预警</h2>
          <ul class="list">
            <li v-for="item in risks" :key="item.employee">
              <h4>{{ item.employee }} · {{ item.department }} · {{ item.riskLevel }}风险</h4>
              <p>原因：{{ item.reason }}</p>
              <p>建议：{{ item.action }}</p>
            </li>
          </ul>
        </div>
        <div>
          <h2>培养计划执行</h2>
          <ul class="list">
            <li v-for="item in training" :key="item.name">
              <h4>{{ item.name }}</h4>
              <p>对象：{{ item.targetGroup }} · 周期：{{ item.duration }}</p>
              <div class="progress-wrap">
                <div class="progress-bar" :style="{ width: pct(item.progress) }"></div>
              </div>
              <small>进度：{{ pct(item.progress) }}</small>
            </li>
          </ul>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
:global(body) {
  margin: 0;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: radial-gradient(circle at 20% 10%, #fef3c7 0, #fff 40%),
    radial-gradient(circle at 80% 20%, #dbeafe 0, #fff 45%);
  color: #0f172a;
}

.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #ecfeff;
  color: #155e75;
  font-size: 12px;
}

h1 {
  margin: 10px 0 8px;
  font-size: 32px;
}

.sub {
  margin: 0;
  color: #334155;
}

.refresh {
  border: 0;
  background: #0f766e;
  color: #fff;
  border-radius: 10px;
  padding: 10px 16px;
  cursor: pointer;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.kpi-card,
.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px;
}

.kpi-card p {
  margin: 0;
  color: #64748b;
}

.kpi-card h3 {
  margin: 10px 0 0;
  font-size: 30px;
}

.two-col {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 14px;
  margin-top: 12px;
}

.nine-box-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.nine-box-item {
  border-radius: 10px;
  padding: 10px;
  border: 1px solid #e2e8f0;
}

.level-A {
  background: #dcfce7;
}

.level-B {
  background: #fef9c3;
}

.level-C {
  background: #fee2e2;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #e2e8f0;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.list li {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 8px;
  background: #fff;
}

.list h4 {
  margin: 0 0 6px;
}

.list p {
  margin: 2px 0;
  color: #334155;
}

.progress-wrap {
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #16a34a;
}

.error {
  border-color: #fca5a5;
  color: #b91c1c;
}

@media (max-width: 900px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .two-col {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 24px;
  }
}
</style>
