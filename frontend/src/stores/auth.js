import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAuthenticated: false
  }),
  getters: {
    isAdmin: (state) => state.user?.roles?.includes('admin') || state.user?.roles?.includes('super_admin')
  },
  actions: {
    async login(username, password) {
      await request.post('/auth/login', { username, password })
      await this.fetchUser()
    try { const csrfRes = await request.get("/auth/csrf-token"); localStorage.setItem("csrf_token", csrfRes.csrf_token); } catch(e) {}
    },
    async fetchUser() {
      try {
        const res = await request.get('/auth/me')
        this.user = res.data || res
        this.isAuthenticated = true
      } catch {
        this.logout()
        throw new Error("会话已过期")
      }
    },
    logout() {
      this.user = null
      this.isAuthenticated = false
      window.location.href = '/login'
    }
  }
})
