/**
 * 主题（亮色 / 暗色）——**唯一的数据源**。
 *
 * ``global.css`` 通过 ``:root`` 与 ``.dark`` 两套 CSS 变量切换配色，
 * 所以这里只负责给 ``<html>`` 增删 ``dark`` 类（同时写 ``data-theme``
 * 便于以后扩展多主题）。
 *
 * ``stores/app.js`` 会委托到这里，两个 store 不会互相打架。
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'theme'

function readInitialTheme() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'dark' || saved === 'light') {
    return saved
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref(readInitialTheme())
  const isDark = computed(() => theme.value === 'dark')

  /** 把当前主题写到 <html> 上。 */
  function apply() {
    document.documentElement.classList.toggle('dark', isDark.value)
    document.documentElement.dataset.theme = theme.value
  }

  function setTheme(next) {
    theme.value = next === 'dark' ? 'dark' : 'light'
    localStorage.setItem(STORAGE_KEY, theme.value)
    apply()
  }

  function toggle() {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  apply()

  return {
    theme,
    isDark,
    //: 兼容旧代码里的 theme.dark 写法
    dark: isDark,
    apply,
    setTheme,
    toggle,
  }
})
