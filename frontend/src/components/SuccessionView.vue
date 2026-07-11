<script setup>
defineProps({
  succession: { type: Array, default: () => [] },
  riskClass: { type: Function, default: () => '' },
})
</script>

<template>
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
          <td><span class="badge badge-ready">{{ item.readiness }}</span></td>
          <td><strong>{{ item.matchScore }}</strong></td>
          <td :class="riskClass(item.risk)">{{ item.risk }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
