<!-- 标签筛选条零件：渲染全部标签，高亮当前选中的标签，点击后把标签抛给页面。 -->
<template>
  <div class="tag-filter" v-if="tags.length > 0">
    <span
      v-for="tag in tags"
      :key="tag"
      :class="['tag-btn', { active: active === tag }]"
      @click="emit('select', tag)"
    >{{ tag }}</span>
  </div>
</template>

<script setup>
defineProps({
  tags: { type: Array, default: () => [] },
  active: { type: String, default: '' },
})

const emit = defineEmits(['select'])
</script>

<style scoped>
.tag-filter { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.tag-btn { background: var(--bg-secondary); border: 1px solid var(--border); padding: 6px 14px; border-radius: 20px; cursor: pointer; font-size: 13px; }
.tag-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
</style>
