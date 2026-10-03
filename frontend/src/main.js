import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'

import App from './App.vue'
import router from './router'
import i18n from './i18n'
import lazyLoad from './directives/lazyLoad'
import { useThemeStore } from './stores/theme'

// 全局样式必须在入口引入：所有页面都依赖这里的 CSS 变量
import './assets/global.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(Toast, { timeout: 3000, position: 'top-right' })
app.use(lazyLoad)

// 主题必须在挂载前应用，避免首屏闪白
useThemeStore().apply()

app.mount('#app')

// PWA：只在生产构建中注册 Service Worker，
// 开发环境注册会缓存模块导致热更新失效。
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* 注册失败不影响主流程 */
    })
  })
}
