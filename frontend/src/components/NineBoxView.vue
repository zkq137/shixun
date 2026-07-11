<script setup>
defineProps({
  nineBox: { type: Array, default: () => [] },
})
</script>

<template>
  <section class="panel">
    <h2>人才九宫格分布</h2>
    <div class="nine-box-grid">
      <div
        v-for="item in nineBox"
        :key="item.cell"
        :class="['nine-box-item', `level-${item.level}`]"
      >
        <h4>{{ item.cell }}</h4>
        <p class="nine-count">{{ item.count }} 人</p>
        <span class="nine-level">Level {{ item.level }}</span>
      </div>
    </div>
  </section>
</template>
