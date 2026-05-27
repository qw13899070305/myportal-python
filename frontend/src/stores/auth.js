import { defineStore } from 'pinia'
import request from '@/utils/request'
import router from '@/router'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: localStorage.getItem('access_token') || null,
    refreshToken: localStorage.getItem('refresh_token') || null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken && !!state.user,
  },
  actions: {
    async login(username, password) {
      const res = await request.post('/auth/login', { username, password })
      this.accessToken = res.access_token
      this.refreshToken = res.refresh_token
      localStorage.setItem('access_token', res.access_token)
      localStorage.setItem('refresh_token', res.refresh_token)
      await this.fetchUser()
    },
    async fetchUser() {
      try {
        const data = await request.get('/auth/me')
        this.user = data
      } catch {
        this.logout()
        throw new Error('会话过期')
      }
    },
    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      router.push('/login')
    },
  },
})