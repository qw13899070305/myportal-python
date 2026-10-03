import { describe, expect, it } from 'vitest'

import { toFriendlyError } from './errors'

/** 造一个形如 axios 错误的对象。 */
function axiosError({ status, data, code, message } = {}) {
  const error = new Error(message || 'boom')
  if (status) error.response = { status, data }
  if (code) error.code = code
  return error
}

describe('toFriendlyError', () => {
  it('网络不可用时给出可操作的提示', () => {
    expect(toFriendlyError(axiosError({ message: 'Network Error' })).message).toBe(
      '无法连接服务器，请确认后端已启动',
    )
    expect(toFriendlyError(new Error('something')).message).toBe('something')
  })

  it('超时单独提示', () => {
    const error = axiosError({ code: 'ECONNABORTED' })
    expect(toFriendlyError(error).message).toBe('请求超时，请稍后重试')
  })

  it('直接使用后端返回的中文 detail', () => {
    const error = axiosError({ status: 400, data: { detail: '用户名已存在' } })
    expect(toFriendlyError(error).message).toBe('用户名已存在')
  })

  it('422 的 detail 数组会被拼成一句话', () => {
    const error = axiosError({
      status: 422,
      data: {
        detail: [
          { loc: ['body', 'password'], msg: '密码必须包含至少一个数字' },
        ],
      },
    })
    expect(toFriendlyError(error).message).toBe(
      'password: 密码必须包含至少一个数字',
    )
  })

  it('没有 detail 时按状态码兜底', () => {
    expect(toFriendlyError(axiosError({ status: 403, data: {} })).message).toBe(
      '没有操作权限',
    )
    expect(toFriendlyError(axiosError({ status: 429, data: {} })).message).toBe(
      '操作过于频繁，请稍后再试',
    )
    expect(toFriendlyError(axiosError({ status: 418, data: {} })).message).toBe(
      '请求失败（HTTP 418）',
    )
  })

  it('永远返回 Error 实例，页面可以直接读 message', () => {
    for (const input of [undefined, null, {}, new Error('x'), axiosError({ status: 500 })]) {
      const result = toFriendlyError(input)
      expect(result).toBeInstanceOf(Error)
      expect(typeof result.message).toBe('string')
      expect(result.message.length).toBeGreaterThan(0)
    }
  })
})
