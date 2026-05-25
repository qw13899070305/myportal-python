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
    alert(msg)
    if (error.response?.status === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default service

// 获取 CSRF Token 并附加到请求头
export async function getCsrfToken() {
  const res = await axios.get('/auth/csrf-token')
  return res.data.csrf_token
}

// 获取 CSRF Token 并附加到请求头
export async function getCsrfToken() {
  const res = await axios.get('/auth/csrf-token')
  return res.data.csrf_token
}
