import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.accessToken) {
    config.headers.Authorization = `Bearer ${authStore.accessToken}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request