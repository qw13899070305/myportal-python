/**
 * 统一的 HTTP 客户端。
 *
 * 只负责「axios 实例 + 两个拦截器」，具体能力都拆到了独立零件里：
 *
 * - :mod:`@/utils/csrf`   —— CSRF 令牌获取与判定
 * - :mod:`@/utils/errors` —— 错误归一化成中文提示
 *
 * 行为：
 * - 自动附带 ``Authorization`` 头
 * - 未登录的写操作（登录/注册/申请）自动附带 CSRF 令牌
 * - 401 时用 refresh token 自动续期一次，失败则清理登录态并跳登录页
 */
import axios from 'axios'

import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { getCsrfToken, needsCsrf, resetCsrfToken } from '@/utils/csrf'
import { toFriendlyError } from '@/utils/errors'

export { getCsrfToken, resetCsrfToken, toFriendlyError }

export const ACCESS_TOKEN_KEY = 'access_token'
export const REFRESH_TOKEN_KEY = 'refresh_token'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  // CSRF 采用双提交 Cookie，必须允许携带 Cookie。
  // 同源请求本来就会带上，显式声明是为了让跨域部署也能工作
  // （后端已开启 allow_credentials=True）。
  withCredentials: true,
})

// ---------------- 401 续期 ----------------

let refreshPromise = null

/** 同一时刻只允许有一个续期请求，避免并发 401 打出多个 refresh。 */
function refreshSession(auth) {
  if (!refreshPromise) {
    refreshPromise = auth.refresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function redirectToLogin() {
  const current = router.currentRoute.value
  if (current.name !== 'login') {
    router.push({ name: 'login', query: { redirect: current.fullPath } })
  }
}

// ---------------- 拦截器 ----------------

request.interceptors.request.use(async (config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }

  if (needsCsrf(config.url, config.method)) {
    try {
      const token = await getCsrfToken()
      if (token) {
        config.headers['X-CSRF-Token'] = token
      }
    } catch {
      // 取不到令牌就让后端返回 403，由响应拦截器统一提示
    }
  }

  return config
})

request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const { response, config } = error
    const auth = useAuthStore()
    const url = String(config?.url || '')
    const isAuthEndpoint = url.startsWith('/auth/')

    // CSRF 令牌过期：换一个新的再试一次
    if (
      response?.status === 403 &&
      needsCsrf(url, config?.method) &&
      !config?._csrfRetried
    ) {
      config._csrfRetried = true
      try {
        await getCsrfToken(true)
        return request(config)
      } catch {
        resetCsrfToken()
        /* 落到下面统一报错 */
      }
    }

    // 访问令牌过期：用 refresh token 续期并重放一次原请求
    if (
      response?.status === 401 &&
      !isAuthEndpoint &&
      !config?._retried &&
      auth.refreshToken
    ) {
      config._retried = true
      try {
        await refreshSession(auth)
        return request(config)
      } catch {
        auth.clear()
        redirectToLogin()
      }
    } else if (response?.status === 401 && !isAuthEndpoint) {
      auth.clear()
      redirectToLogin()
    }

    return Promise.reject(toFriendlyError(error))
  },
)

export default request
