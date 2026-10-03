<template>
  <button
    class="theme-toggle"
    type="button"
    :title="theme.isDark ? '切换到亮色模式' : '切换到暗色模式'"
    aria-label="切换主题"
    @click="theme.toggle()"
  >
    <span v-if="theme.isDark">☀️</span>
    <span v-else>🌙</span>
  </button>
</template>

<script setup>
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()
</script>

<style scoped>
.theme-toggle {
  background: transparent;
  border: none;
  font-size: 18px;
  line-height: 1;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.theme-toggle:hover {
  background: var(--bg-tertiary);
}
</style>
