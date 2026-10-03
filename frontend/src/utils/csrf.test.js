import { describe, expect, it } from 'vitest'

import { CSRF_PROTECTED_PATHS, needsCsrf } from './csrf'

describe('needsCsrf', () => {
  it('未登录的写操作需要 CSRF 令牌', () => {
    expect(needsCsrf('/auth/login', 'post')).toBe(true)
    expect(needsCsrf('/auth/register', 'POST')).toBe(true)
    expect(needsCsrf('/users/apply', 'post')).toBe(true)
  })

  it('读请求不需要', () => {
    for (const method of ['get', 'head', 'options']) {
      expect(needsCsrf('/auth/login', method)).toBe(false)
    }
  })

  it('已登录的业务接口不需要（它们带 Bearer 令牌）', () => {
    expect(needsCsrf('/articles/', 'post')).toBe(false)
    expect(needsCsrf('/files/upload', 'post')).toBe(false)
    expect(needsCsrf('/auth/logout', 'post')).toBe(false)
  })

  it('参数缺省时不抛异常', () => {
    expect(needsCsrf()).toBe(false)
    expect(needsCsrf(null, null)).toBe(false)
  })

  it('受保护路径清单是可读的常量', () => {
    expect(Array.isArray(CSRF_PROTECTED_PATHS)).toBe(true)
    expect(CSRF_PROTECTED_PATHS).toContain('/auth/login')
  })
})
