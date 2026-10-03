<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <span class="auth-logo">◈</span>
        <h1>{{ t('auth.welcomeBack') }}</h1>
        <p>登录你的 MyPortal 工作空间</p>
      </div>

      <form @submit.prevent="handleLogin">
        <label class="input-group">
          <span>{{ t('auth.username') }}</span>
          <input v-model.trim="username" autocomplete="username" required />
        </label>

        <label class="input-group">
          <span>{{ t('auth.password') }}</span>
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>

        <!-- 登录连续失败后后端会要求验证码 -->
        <div v-if="needCaptcha" class="captcha-row">
          <img :src="captchaUrl" alt="验证码" title="点击刷新" @click="refreshCaptcha" />
          <input v-model.trim="captchaCode" placeholder="验证码" maxlength="8" />
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button type="submit" :disabled="loading">
          <span v-if="!loading">{{ t('common.login') }}</span>
          <span v-else class="spinner"></span>
        </button>
      </form>

      <p class="switch-text">
        {{ t('auth.noAccount') }}<router-link :to="{ name: 'register' }">{{ t('common.register') }}</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const captchaCode = ref('')
const captchaId = ref('')
const captchaUrl = ref('')
const needCaptcha = ref(false)
const errorMsg = ref('')
const loading = ref(false)

async function refreshCaptcha() {
  // 验证码接口返回 PNG，id 在 X-Captcha-Id 响应头里
  const response = await fetch('/api/v1/auth/captcha', { credentials: 'same-origin' })
  const blob = await response.blob()
  captchaId.value = response.headers.get('X-Captcha-Id') || ''
  if (captchaUrl.value) {
    URL.revokeObjectURL(captchaUrl.value)
  }
  captchaUrl.value = URL.createObjectURL(blob)
  captchaCode.value = ''
}

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.push(redirect || { name: 'dashboard' })
  } catch (error) {
    errorMsg.value = error.message || t('auth.loginFailed')
    // 后端要求验证码时自动加载一张
    if (errorMsg.value.includes('验证码')) {
      needCaptcha.value = true
      await refreshCaptcha()
    }
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (captchaUrl.value) {
    URL.revokeObjectURL(captchaUrl.value)
  }
})
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
.captcha-row img { height: 48px; cursor: pointer; border: 1px solid var(--border); border-radius: 6px; background: #fff; }
.captcha-row input { flex: 1; }
.error-msg { color: var(--danger); font-size: 14px; margin-bottom: 8px; }
button { width: 100%; padding: 14px; background: var(--primary); color: white; border-radius: var(--radius-sm); font-size: 16px; font-weight: 600; border: none; cursor: pointer; }
button:hover:not(:disabled) { background: var(--primary-hover); }
button:disabled { opacity: 0.7; cursor: not-allowed; }
.spinner { width: 22px; height: 22px; border: 2px solid transparent; border-top-color: white; border-radius: 50%; animation: spin 0.6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.switch-text { margin-top: 20px; text-align: center; color: var(--text-secondary); }
.switch-text a { color: var(--primary); font-weight: 600; }
</style>
