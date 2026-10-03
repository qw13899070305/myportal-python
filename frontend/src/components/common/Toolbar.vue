<!-- Toolbar：工具栏零件，只提供一行弹性布局和搜索框/按钮的统一外观，内容全部由默认插槽决定。 -->
<template>
  <div class="toolbar" :class="{ wrap }" :style="{ '--toolbar-input-width': inputWidth }">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  // 内容多时是否换行（文件管理、审计日志原本就允许换行）
  wrap: { type: Boolean, default: false },
  // 搜索框宽度：各页面原本宽度不同，用这个 prop 保持一致
  inputWidth: { type: String, default: '220px' },
})
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 16px; }
.toolbar.wrap { flex-wrap: wrap; }
.toolbar :deep(input) { padding: 9px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-secondary); color: var(--text); width: var(--toolbar-input-width); }
.toolbar :deep(button) { padding: 9px 18px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
.toolbar :deep(button.danger) { color: var(--danger); }
.toolbar :deep(button:disabled) { opacity: 0.5; cursor: not-allowed; }
</style>
