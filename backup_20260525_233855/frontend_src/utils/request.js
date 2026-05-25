import axios from 'axios'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 15000,
  withCredentials: true
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
    // 项目若使用 Element Plus，请改为 ElMessage.error(msg)
    alert(msg)
    if (error.response?.status === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default service
