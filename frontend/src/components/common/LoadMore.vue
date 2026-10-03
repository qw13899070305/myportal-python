<!-- LoadMore：分页尾巴零件，只在还有没加载完的数据时显示「加载更多」按钮。 -->
<template>
  <div v-if="total > loaded" class="pager">
    <button type="button" :disabled="loading" @click="emit('load')">
      {{ loading ? '加载中...' : '加载更多' }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  // 后端返回的总条数
  total: { type: Number, default: 0 },
  // 当前已经加载到本地的条数
  loaded: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['load'])
</script>

<style scoped>
.pager { text-align: center; margin-top: 18px; }
.pager button { padding: 9px 24px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
.pager button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
