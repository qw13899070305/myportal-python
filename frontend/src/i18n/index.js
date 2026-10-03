import { createI18n } from 'vue-i18n'

import enUS from './locales/en-US.json'
import zhCN from './locales/zh-CN.json'

const STORAGE_KEY = 'locale'
const SUPPORTED = ['zh-CN', 'en-US']

export const LOCALES = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'en-US', label: 'English' },
]

function initialLocale() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (SUPPORTED.includes(saved)) {
    return saved
  }
  return navigator.language?.toLowerCase().startsWith('en') ? 'en-US' : 'zh-CN'
}

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale(),
  fallbackLocale: 'en-US',
  messages: { 'zh-CN': zhCN, 'en-US': enUS },
})

/** 切换语言并持久化。 */
export function setLocale(locale) {
  const next = SUPPORTED.includes(locale) ? locale : 'zh-CN'
  i18n.global.locale.value = next
  localStorage.setItem(STORAGE_KEY, next)
  document.documentElement.lang = next
  return next
}

document.documentElement.lang = i18n.global.locale.value

export default i18n
