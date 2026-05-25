<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <span class="auth-logo">◈</span>
        <h1>欢迎回来</h1>
        <p>登录你的 MyPortal 工作空间</p>
      </div>
      <form @submit.prevent="handleLogin">
        <label class="input-group"><span>用户名</span><input v-model="username" required /></label>
        <label class="input-group"><span>密码</span><input type="password" v-model="password" required /></label>
        <div v-if="needCaptcha" class="captcha-row">
          <img :src="captchaUrl" @click="refreshCaptcha" title="点击刷新验证码"/>
          <input v-model="captchaCode" placeholder="验证码" required />
        </div>
        <p class="error-msg" v-if="errorMsg">{{ errorMsg }}</p>
        <button type="submit" :disabled="loading">
          <span v-if="!loading">登 录</span>
          <span v-else class="spinner"></span>
        </button>
      </form>
      <p class="switch-text">没有账号？<router-link to="/register">立即注册</router-link></p>
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
const captchaCode = ref('')
const captchaId = ref('')
const needCaptcha = ref(false)
const captchaUrl = ref('')
const errorMsg = ref('')
const loading = ref(false)
const router = useRouter()
const auth = useAuthStore()

async function refreshCaptcha() {
  const res = await axios.get('/api/v1/auth/captcha')
  captchaId.value = res.headers['x-captcha-id']
  const blob = new Blob([res.data], {type: 'image/png'})
  captchaUrl.value = URL.createObjectURL(blob)
}

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    const payload = { username: username.value, password: password.value }
    if (needCaptcha.value) {
      payload.captcha_code = captchaCode.value
      payload.captcha_id = captchaId.value
    }
    const res = await axios.post('/api/v1/auth/login', payload)
    auth.setAuth(res.data.access_token, res.data.user)
    router.push('/')
  } catch (e) {
    const detail = e.response?.data?.detail || '登录失败'
    errorMsg.value = detail
    if (detail.includes('验证码') || detail.includes('需要验证码')) {
      needCaptcha.value = true
      await refreshCaptcha()
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #f0f4ff 0%, #e8ecff 40%, #f5f3ff 100%); padding: 24px; }
.auth-card { background: var(--bg-secondary); border-radius: var(--radius-xl); padding: 48px 40px; width: 420px; max-width: 100%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.15); border: 1px solid var(--border); }
.auth-header { text-align: center; margin-bottom: 32px; }
.auth-logo { font-size: 44px; color: var(--primary); }
h1 { font-size: 28px; font-weight: 700; margin: 12px 0 6px; }
.auth-header p { color: var(--text-secondary); }
.input-group { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.input-group span { font-weight: 600; font-size: 14px; }
input { padding: 12px 16px; border: 1.5px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); color: var(--text); font-size: 15px; }
input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
.captcha-row { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.captcha-row img { height: 40px; cursor: pointer; border: 1px solid var(--border); border-radius: 4px; }
.error-msg { color: var(--danger); font-size: 14px; margin-bottom: 8px; }
button { width: 100%; padding: 14px; background: var(--primary); color: white; border-radius: var(--radius-sm); font-size: 16px; font-weight: 600; border: none; cursor: pointer; }
button:hover:not(:disabled) { background: var(--primary-hover); }
button:disabled { opacity: 0.7; cursor: not-allowed; }
.spinner { width: 22px; height: 22px; border: 2px solid transparent; border-top-color: white; border-radius: 50%; animation: spin 0.6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.switch-text { margin-top: 20px; text-align: center; }
.switch-text a { color: var(--primary); font-weight: 600; }
</style>
