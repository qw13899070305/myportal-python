<!-- PasswordForm：修改密码表单零件，自己校验两次输入并调用 auth.changePassword。 -->
<template>
  <div class="card">
    <h3>🔒 修改密码</h3>
    <form @submit.prevent="changePassword">
      <input v-model="oldPassword" type="password" placeholder="当前密码" autocomplete="current-password" required />
      <input v-model="newPassword" type="password" placeholder="新密码（≥8 位，含大小写/数字/特殊字符）" autocomplete="new-password" required />
      <input v-model="confirmPassword" type="password" placeholder="确认新密码" autocomplete="new-password" required />
      <button type="submit" :disabled="submitting">修改密码</button>
    </form>
    <p v-if="message" :class="messageType">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const message = ref('')
const messageType = ref('success-msg')

async function changePassword() {
  message.value = ''
  if (newPassword.value !== confirmPassword.value) {
    messageType.value = 'error-msg'
    message.value = '两次输入的新密码不一致'
    return
  }
  submitting.value = true
  try {
    await auth.changePassword(oldPassword.value, newPassword.value)
    messageType.value = 'success-msg'
    message.value = '密码修改成功'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (error) {
    messageType.value = 'error-msg'
    message.value = error.message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
form { display: flex; flex-direction: column; gap: 10px; margin-top: 10px; }
form input { padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); }
form button { align-self: flex-start; background: var(--primary); color: white; border: none; padding: 10px 22px; border-radius: 8px; cursor: pointer; }
form button:disabled { opacity: 0.6; cursor: not-allowed; }
.success-msg { color: var(--success); margin-top: 10px; font-size: 14px; }
.error-msg { color: var(--danger); margin-top: 10px; font-size: 14px; }
</style>
