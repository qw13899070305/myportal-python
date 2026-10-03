/**
 * 登录态管理。
 *
 * 注意：这里**不导入 router**，导航交给调用方或 request 拦截器处理，
 * 避免 router <-> store <-> request 之间形成循环依赖。
 *
 * 对外的 API 同时保留新旧两套写法：
 * - ``accessToken`` / ``token``（getter）
 * - ``isAdmin``（方法，页面上用 ``auth.isAdmin()``）
 * - ``setAuth(...)``（旧代码使用）
 */
import { defineStore } from 'pinia'

import request, {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  getCsrfToken,
} from '@/utils/request'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY) || null,
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY) || null,
    //: 是否已经尝试过恢复会话（路由守卫依赖它避免重复请求）
    ready: false,
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.user),
    //: 旧代码里写的是 auth.token
    token: (state) => state.accessToken,
    roles: (state) => state.user?.roles || [],
  },

  actions: {
    /** 是否具备管理权限（页面上以 auth.isAdmin() 调用）。 */
    isAdmin() {
      return this.roles.some((role) => role === 'admin' || role === 'super_admin')
    },

    setTokens(accessToken, refreshToken) {
      this.accessToken = accessToken || null
      this.refreshToken = refreshToken || null
      if (accessToken) {
        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
      } else {
        localStorage.removeItem(ACCESS_TOKEN_KEY)
      }
      if (refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
      } else {
        localStorage.removeItem(REFRESH_TOKEN_KEY)
      }
    },

    /** 旧代码使用的方法：一次性写入令牌与用户。 */
    setAuth(accessToken, refreshToken, user = null) {
      this.setTokens(accessToken, refreshToken)
      if (user) {
        this.user = user
        this.ready = true
      }
    },

    /** 清空本地登录态（不调用后端）。 */
    clear() {
      this.user = null
      this.setTokens(null, null)
    },

    /** 登录：后端同时支持 JSON 与表单，这里用 JSON 并在拦截器里自动带 CSRF。 */
    async login(username, password) {
      await getCsrfToken()
      const data = await request.post('/auth/login', { username, password })
      this.setTokens(data.access_token, data.refresh_token)
      await this.fetchUser()
      this.ready = true
    },

    /** 用 refresh token 换取新的令牌对。 */
    async refresh() {
      if (!this.refreshToken) {
        throw new Error('缺少刷新令牌')
      }
      const data = await request.post('/auth/refresh', {
        refresh_token: this.refreshToken,
      })
      this.setTokens(data.access_token, data.refresh_token)
      return true
    },

    async fetchUser() {
      this.user = await request.get('/auth/me')
      return this.user
    },

    /** 应用启动时尝试用本地令牌恢复会话，返回是否已登录。 */
    async restore() {
      if (this.ready) {
        return this.isAuthenticated
      }
      if (!this.accessToken) {
        this.ready = true
        return false
      }
      try {
        await this.fetchUser()
        return true
      } catch {
        this.clear()
        return false
      } finally {
        this.ready = true
      }
    },

    /** 退出登录：通知后端把令牌加入黑名单，然后清理本地状态。 */
    async logout() {
      if (this.accessToken) {
        try {
          await request.post('/auth/logout')
        } catch {
          // 后端不可用时也要保证本地能退出
        }
      }
      this.clear()
    },

    /** 注册新账号（不自动登录）。 */
    async register({ username, password, confirmPassword, email }) {
      await getCsrfToken()
      return request.post('/auth/register', {
        username,
        password,
        confirm_password: confirmPassword,
        email: email || null,
      })
    },

    async changePassword(oldPassword, newPassword) {
      return request.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
    },

    async uploadAvatar(file) {
      const form = new FormData()
      form.append('file', file)
      return request.post('/auth/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
  },
})
