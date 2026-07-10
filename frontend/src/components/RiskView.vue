<script setup>
defineProps({
  risks: { type: Array, default: () => [] },
  riskClass: { type: Function, default: () => '' },
})
</script>

<template>
  <section class="panel">
    <h2>流失风险预警</h2>
    <ul class="list">
      <li v-for="item in risks" :key="item.employee">
        <div class="risk-header">
          <h4>{{ item.employee }}</h4>
          <span :class="['risk-tag', riskClass(item.riskLevel)]">{{ item.riskLevel }}风险</span>
        </div>
        <p>🏢 {{ item.department }}</p>
        <p>📋 原因：{{ item.reason }}</p>
        <p>💡 建议：{{ item.action }}</p>
      </li>
    </ul>
  </section>
</template>
