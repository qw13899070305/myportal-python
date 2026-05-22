import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

export const useAppStore = defineStore('app', () => {
  const isDark = ref(localStorage.getItem('theme') === 'dark')
  function toggleDark() {
    isDark.value = !isDark.value
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  }
  watchEffect(() => { document.documentElement.classList.toggle('dark', isDark.value) })
  return { isDark, toggleDark }
})
