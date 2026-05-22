<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <span class="auth-logo">◈</span>
        <h1>创建账号</h1>
        <p>加入 MyPortal 开始协作</p>
      </div>
      <form @submit.prevent="handleRegister">
        <label class="input-group"><span>用户名</span><input v-model="username" required /></label>
        <label class="input-group"><span>密码</span><input type="password" v-model="password" required /></label>
        <label class="input-group"><span>确认密码</span><input type="password" v-model="password2" required /></label>
        <p class="error-msg" v-if="errorMsg">{{ errorMsg }}</p>
        <button type="submit" :disabled="loading">
          <span v-if="!loading">注 册</span>
          <span v-else class="spinner"></span>
        </button>
      </form>
      <p class="switch-text">已有账号？<router-link to="/login">去登录</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const username = ref('')
const password = ref('')
const password2 = ref('')
const errorMsg = ref('')
const loading = ref(false)
const router = useRouter()

async function handleRegister() {
  errorMsg.value = ''
  if (password.value !== password2.value) {
    errorMsg.value = '两次密码不一致'
    return
  }
  loading.value = true
  try {
    await axios.post('/api/v1/users/apply', {
      username: username.value,
      password: password.value,
      requested_role: 'reader'
    })
    alert('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '注册失败'
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
.error-msg { color: var(--danger); font-size: 14px; margin-bottom: 8px; }
button { width: 100%; padding: 14px; background: var(--primary); color: white; border-radius: var(--radius-sm); font-size: 16px; font-weight: 600; border: none; cursor: pointer; }
button:hover:not(:disabled) { background: var(--primary-hover); }
button:disabled { opacity: 0.7; cursor: not-allowed; }
.spinner { width: 22px; height: 22px; border: 2px solid transparent; border-top-color: white; border-radius: 50%; animation: spin 0.6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.switch-text { margin-top: 20px; text-align: center; }
.switch-text a { color: var(--primary); font-weight: 600; }
</style>
