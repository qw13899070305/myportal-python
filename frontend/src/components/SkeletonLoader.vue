<template>
  <div class="skeleton-loader">
    <div v-for="n in count" :key="n" class="skeleton-item">
      <div class="skeleton-line skeleton-line-short"></div>
      <div class="skeleton-line skeleton-line-long"></div>
      <div class="skeleton-line skeleton-line-medium"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({ count: { type: Number, default: 3 } })
</script>

<style scoped>
.skeleton-loader { padding: 16px; }
.skeleton-item { margin-bottom: 24px; }
.skeleton-line { height: 14px; background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px; margin-bottom: 8px; }
.skeleton-line-short { width: 30%; }
.skeleton-line-long { width: 90%; }
.skeleton-line-medium { width: 60%; }
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
</style>
