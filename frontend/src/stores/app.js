/**
 * 应用级状态。
 *
 * 主题相关的能力全部委托给 ``stores/theme.js``（唯一数据源），
 * 这样 MainLayout 用 appStore、ThemeToggle 用 themeStore 也不会冲突。
 */
import { computed } from 'vue'
import { defineStore } from 'pinia'

import { useThemeStore } from '@/stores/theme'

export const useAppStore = defineStore('app', () => {
  const themeStore = useThemeStore()

  const isDark = computed(() => themeStore.isDark)

  function toggleDark() {
    themeStore.toggle()
  }

  function applyTheme() {
    themeStore.apply()
  }

  return { isDark, toggleDark, applyTheme, themeStore }
})
