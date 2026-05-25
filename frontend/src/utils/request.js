import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 15000
})

service.interceptors.request.use(config => {
  const auth = useAuthStore()
  if (auth.token) config.headers.Authorization = `Bearer ${auth.token}`
  return config
})

service.interceptors.response.use(
  res => res.data,
  error => {
    let msg = '请求失败'
    if (error.response?.data?.detail) {
      msg = error.response.data.detail
    } else if (error.code === 'ECONNABORTED') {
      msg = '请求超时，请重试'
    } else if (!error.response) {
      msg = '网络连接失败，请检查网络'
    }
    ElMessage.error(msg)
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default service
