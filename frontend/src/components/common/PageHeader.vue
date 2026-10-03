<!-- PageHeader：页面标题零件，左边标题、右边留一个默认插槽放操作按钮。 -->
<template>
  <div class="page-header">
    <h2>{{ title }}</h2>
    <div v-if="$slots.default" class="page-header-actions">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
})
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.page-header-actions { display: flex; gap: 10px; }
</style>
