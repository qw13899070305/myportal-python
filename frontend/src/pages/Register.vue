<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <span class="auth-logo">◈</span>
        <h1>{{ t('auth.createAccount') }}</h1>
        <p>加入 MyPortal 开始协作</p>
      </div>

      <form @submit.prevent="handleRegister">
        <label class="input-group">
          <span>{{ t('auth.username') }}</span>
          <input
            v-model.trim="username"
            minlength="3"
            maxlength="50"
            autocomplete="username"
            required
            @blur="checkUsername"
          />
        </label>
        <p v-if="usernameHint" class="hint" :class="{ bad: usernameTaken }">{{ usernameHint }}</p>

        <label class="input-group">
          <span>{{ t('auth.email') }}</span>
          <input v-model.trim="email" type="email" autocomplete="email" />
        </label>
        <label class="input-group">
          <span>{{ t('auth.password') }}</span>
          <input v-model="password" type="password" autocomplete="new-password" required />
        </label>
        <label class="input-group">
          <span>{{ t('auth.confirmPassword') }}</span>
          <input v-model="confirmPassword" type="password" autocomplete="new-password" required />
        </label>

        <p class="hint">密码需至少 8 位，且包含大写字母、小写字母、数字和特殊字符。</p>
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
        <p v-if="successMsg" class="success-msg">{{ successMsg }}</p>

        <button type="submit" :disabled="loading">
          <span v-if="!loading">{{ t('common.register') }}</span>
          <span v-else class="spinner"></span>
        </button>
      </form>

      <p class="switch-text">
        {{ t('auth.haveAccount') }}<router-link :to="{ name: 'login' }">{{ t('common.login') }}</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMsg = ref('')
const successMsg = ref('')
const usernameHint = ref('')
const usernameTaken = ref(false)
const loading = ref(false)

async function checkUsername() {
  usernameHint.value = ''
  usernameTaken.value = false
  if (username.value.length < 3) return
  try {
    const data = await request.get('/auth/check-username', {
      params: { username: username.value },
    })
    if (!data.available) {
      usernameTaken.value = true
      usernameHint.value = '该用户名已被占用'
    }
  } catch {
    // 提示失败不影响注册流程
  }
}

async function handleRegister() {
  errorMsg.value = ''
  successMsg.value = ''

  if (password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await auth.register({
      username: username.value,
      password: password.value,
      confirmPassword: confirmPassword.value,
      email: email.value,
    })
    successMsg.value = '注册成功，正在跳转到登录页…'
    setTimeout(() => router.push({ name: 'login' }), 800)
  } catch (error) {
    errorMsg.value = error.message || '注册失败'
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
.hint { font-size: 12px; color: var(--text-tertiary); margin-bottom: 10px; }
.hint.bad { color: var(--danger); }
.error-msg { color: var(--danger); font-size: 14px; margin-bottom: 8px; }
.success-msg { color: var(--success); font-size: 14px; margin-bottom: 8px; }
button { width: 100%; padding: 14px; background: var(--primary); color: white; border-radius: var(--radius-sm); font-size: 16px; font-weight: 600; border: none; cursor: pointer; }
button:hover:not(:disabled) { background: var(--primary-hover); }
button:disabled { opacity: 0.7; cursor: not-allowed; }
.spinner { width: 22px; height: 22px; border: 2px solid transparent; border-top-color: white; border-radius: 50%; animation: spin 0.6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.switch-text { margin-top: 20px; text-align: center; color: var(--text-secondary); }
.switch-text a { color: var(--primary); font-weight: 600; }
</style>
