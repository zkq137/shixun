<script setup>
defineProps({
  overview: { type: Object, default: () => ({}) },
  health: { type: Object, default: null },
  succession: { type: Array, default: () => [] },
  pct: { type: Function, default: (v) => v },
  riskClass: { type: Function, default: () => '' },
})
</script>

<template>
  <section class="kpi-grid">
    <article class="kpi-card">
      <p>👥 员工总数</p>
      <h3>{{ overview.employeeCount }}</h3>
    </article>
    <article class="kpi-card">
      <p>🎯 关键岗位</p>
      <h3>{{ overview.keyPositions }}</h3>
    </article>
    <article class="kpi-card">
      <p>✅ Ready Now</p>
      <h3>{{ overview.readyNowSuccessors }}</h3>
    </article>
    <article class="kpi-card">
      <p>🔴 高风险员工</p>
      <h3>{{ overview.highRiskEmployees }}</h3>
    </article>
  </section>

  <section class="panel">
    <h2>系统状态</h2>
    <div class="status-grid">
      <div><strong>后端服务：</strong>{{ health?.service }}</div>
      <div><strong>健康检查：</strong>{{ health?.status }}</div>
      <div><strong>培养计划完成率：</strong>{{ pct(overview.completionRate) }}</div>
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
          <td :class="riskClass(item.risk)">{{ item.risk }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
