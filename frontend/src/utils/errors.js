/**
 * 错误归一化（独立零件）。
 *
 * 把 axios 抛出的各种错误统一成一个带中文 message 的 ``Error``，
 * 这样页面里只要 ``catch (e) { show(e.message) }`` 就够了。
 */

/** HTTP 状态码 -> 兜底提示。 */
const STATUS_MESSAGES = {
  400: '请求不合法',
  401: '登录状态已失效，请重新登录',
  403: '没有操作权限',
  404: '请求的资源不存在',
  409: '资源冲突，请刷新后重试',
  410: '内容已失效',
  413: '文件过大',
  422: '提交的内容不合法',
  429: '操作过于频繁，请稍后再试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂时不可用',
  504: '网关超时',
}

/** 从 FastAPI 的 422 响应里拼出可读的一段话。 */
function formatValidationDetail(detail) {
  const first = detail[0]
  const location = Array.isArray(first?.loc)
    ? first.loc.filter((part) => part !== 'body').join('.')
    : ''
  const message = first?.msg || '参数不合法'
  return location ? `${location}: ${message}` : message
}

/**
 * 把任意错误转换成可直接展示的 ``Error``。
 *
 * - 网络不可用 / 超时 -> 友好提示
 * - 后端返回的 ``detail`` 字符串 -> 原样使用（后端已经是中文）
 * - ``detail`` 是数组（422）-> 取第一条并带上字段名
 * - 其它 -> 按状态码给兜底文案
 */
export function toFriendlyError(error) {
  const response = error?.response

  if (!response) {
    if (error?.code === 'ECONNABORTED') {
      return new Error('请求超时，请稍后重试')
    }
    if (error?.message === 'Network Error') {
      return new Error('无法连接服务器，请确认后端已启动')
    }
    return new Error(error?.message || '网络异常，请稍后重试')
  }

  const detail = response.data?.detail
  if (typeof detail === 'string' && detail) {
    return new Error(detail)
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return new Error(formatValidationDetail(detail))
  }

  return new Error(
    STATUS_MESSAGES[response.status] || `请求失败（HTTP ${response.status}）`,
  )
}

export default toFriendlyError
