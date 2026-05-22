<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <span class="auth-logo">◈</span>
        <h1>欢迎回来</h1>
        <p>登录你的 MyPortal 工作空间</p>
      </div>
      <form @submit.prevent="handleLogin" class="auth-form">
        <label>
          <span>用户名</span>
          <input v-model="username" type="text" placeholder="输入用户名" required />
        </label>
        <label>
          <span>密码</span>
          <input v-model="password" type="password" placeholder="输入密码" required />
        </label>
        <button type="submit" :disabled="loading">
          <span v-if="!loading">登 录</span>
          <span v-else class="spinner"></span>
        </button>
      </form>
      <p class="auth-switch">
        没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const username = ref('')
const password = ref('')
const loading = ref(false)
const router = useRouter()
const auth = useAuthStore()

async function handleLogin() {
  loading.value = true
  try {
    const res = await axios.post('/api/v1/auth/login', {
      username: username.value,
      password: password.value
    })
    auth.setAuth(res.data.access_token, res.data.user)
    router.push('/')
  } catch (e) {
    alert('登录失败：' + (e.response?.data?.detail || '网络错误'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 40%, #f5f3ff 100%);
  padding: 24px;
}
.auth-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-xl);
  padding: 48px 40px;
  width: 420px;
  max-width: 100%;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.15);
  border: 1px solid var(--border);
}
.auth-header {
  text-align: center;
  margin-bottom: 32px;
}
.auth-logo {
  font-size: 44px;
  color: var(--primary);
  display: block;
  margin-bottom: 12px;
}
.auth-header h1 {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin-bottom: 6px;
}
.auth-header p {
  color: var(--text-secondary);
  font-size: 15px;
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.auth-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.auth-form label span {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}
.auth-form input {
  padding: 12px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  font-size: 15px;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
}
.auth-form input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
.auth-form button {
  width: 100%;
  padding: 14px;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 16px;
  font-weight: 600;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 8px;
}
.auth-form button:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 10px 20px -10px var(--primary);
}
.auth-form button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.spinner {
  width: 22px; height: 22px;
  border: 2px solid transparent;
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.auth-switch {
  margin-top: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}
.auth-switch a {
  color: var(--primary);
  font-weight: 600;
  text-decoration: none;
}
.auth-switch a:hover {
  text-decoration: underline;
}
</style>
