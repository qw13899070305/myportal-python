import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  function setAuth(t, u) {
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('user', JSON.stringify(u))
  }
  function logout() {
    token.value = ''
    user.value = null
    localStorage.clear()
  }
  function isAdmin() {
    return user.value?.roles?.includes('admin') || user.value?.roles?.includes('super_admin')
  }
  return { token, user, setAuth, logout, isAdmin }
})
