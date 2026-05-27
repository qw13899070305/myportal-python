import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import { useThemeStore } from '@/stores/theme'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(Toast)

// 初始化主题
const themeStore = useThemeStore()
themeStore.apply()

app.mount('#app')