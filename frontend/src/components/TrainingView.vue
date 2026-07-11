<script setup>
defineProps({
  training: { type: Array, default: () => [] },
  pct: { type: Function, default: (v) => v },
})
</script>

<template>
  <section class="panel">
    <h2>培养计划执行</h2>
    <ul class="list">
      <li v-for="item in training" :key="item.name">
        <h4>{{ item.name }}</h4>
        <p>👥 对象：{{ item.targetGroup }} · ⏱ 周期：{{ item.duration }}</p>
        <div class="progress-wrap">
          <div class="progress-bar" :style="{ width: pct(item.progress) }"></div>
        </div>
        <small>进度：{{ pct(item.progress) }}</small>
      </li>
    </ul>
  </section>
</template>
