import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

export const useAppStore = defineStore('app', () => {
  const isDark = ref(localStorage.getItem('theme') === 'dark')

  function toggleDark() {
    isDark.value = !isDark.value
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
    applyTheme()
  }

  function applyTheme() {
    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  // 初始化时应用主题
  applyTheme()

  // 监听变化
  watchEffect(() => {
    applyTheme()
  })

  return { isDark, toggleDark }
})
