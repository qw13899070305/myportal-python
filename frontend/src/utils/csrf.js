/**
 * CSRF 令牌（独立零件）。
 *
 * 后端采用「双提交 Cookie」：``GET /auth/csrf-token`` 同时返回令牌
 * 并写入签名 Cookie，前端把令牌放进 ``X-CSRF-Token`` 请求头即可。
 *
 * 只有**未携带 Bearer 令牌的写操作**需要它（登录 / 注册 / 申请），
 * 已登录的请求因为带 Authorization 头，天然不受 CSRF 影响。
 */
import axios from 'axios'

//: 需要携带 CSRF 令牌的接口前缀
export const CSRF_PROTECTED_PATHS = [
  '/auth/login',
  '/auth/register',
  '/users/apply',
]

const CSRF_TOKEN_PATH = '/api/v1/auth/csrf-token'
const MUTATING_METHODS = ['post', 'put', 'patch', 'delete']

let cachedToken = null

/** 该请求是否需要 CSRF 令牌。 */
export function needsCsrf(url = '', method = 'get') {
  if (!MUTATING_METHODS.includes(String(method).toLowerCase())) {
    return false
  }
  return CSRF_PROTECTED_PATHS.some((path) => String(url).startsWith(path))
}

/**
 * 获取（并缓存）CSRF 令牌。
 *
 * 用裸 axios 而不是业务实例，避免拦截器递归；
 * ``withCredentials`` 保证签名 Cookie 能带上。
 */
export async function getCsrfToken(force = false) {
  if (!cachedToken || force) {
    const response = await axios.get(CSRF_TOKEN_PATH, { withCredentials: true })
    cachedToken = response.data?.csrf_token || null
  }
  return cachedToken
}

/** 清空缓存（令牌失效时调用，下次会重新拉取）。 */
export function resetCsrfToken() {
  cachedToken = null
}

export default { getCsrfToken, needsCsrf, resetCsrfToken }
