<template>
  <div class="skeleton-loader" aria-hidden="true">
    <div v-for="n in count" :key="n" class="skeleton-item">
      <div class="skeleton-line skeleton-line-short"></div>
      <div class="skeleton-line skeleton-line-long"></div>
      <div class="skeleton-line skeleton-line-medium"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  count: { type: Number, default: 3 },
})
</script>

<style scoped>
.skeleton-loader { padding: 8px 0; }
.skeleton-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 12px;
}
.skeleton-line {
  height: 14px;
  border-radius: 4px;
  margin-bottom: 10px;
  background: linear-gradient(
    90deg,
    var(--bg-tertiary) 25%,
    var(--border) 50%,
    var(--bg-tertiary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton-line:last-child { margin-bottom: 0; }
.skeleton-line-short { width: 30%; }
.skeleton-line-long { width: 90%; }
.skeleton-line-medium { width: 60%; }
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
