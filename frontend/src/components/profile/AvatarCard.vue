<!-- AvatarCard：个人中心头像卡片零件，负责头像展示、上传、删除，改完发 changed 通知父组件。 -->
<template>
  <div class="card">
    <div class="avatar-row">
      <img v-if="auth.user?.avatar_url" class="avatar-lg" :src="auth.user.avatar_url" alt="头像" />
      <div v-else class="avatar-lg">{{ initial }}</div>
      <div class="avatar-info">
        <h2>{{ auth.user?.username }}</h2>
        <p class="muted">
          角色：{{ auth.user?.roles?.join('、') || '无' }}
          <span v-if="auth.user?.email"> · {{ auth.user.email }}</span>
        </p>
        <div class="avatar-actions">
          <label class="upload-label">
            <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" @change="uploadAvatar" />
            <span>更换头像</span>
          </label>
          <button v-if="auth.user?.avatar_url" type="button" class="link-btn" @click="removeAvatar">
            删除头像
          </button>
        </div>
      </div>
    </div>
    <p v-if="avatarMsg" :class="avatarOk ? 'success-msg' : 'error-msg'">{{ avatarMsg }}</p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'

const auth = useAuthStore()

const avatarMsg = ref('')
const avatarOk = ref(true)

const emit = defineEmits(['changed'])

// 没有头像时用用户名首字母占位
const initial = computed(() => auth.user?.username?.charAt(0)?.toUpperCase() || '?')

async function uploadAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  avatarMsg.value = ''
  try {
    await auth.uploadAvatar(file)
    await auth.fetchUser()
    avatarOk.value = true
    avatarMsg.value = '头像已更新'
    emit('changed')
  } catch (error) {
    avatarOk.value = false
    avatarMsg.value = error.message
  } finally {
    event.target.value = ''
  }
}

async function removeAvatar() {
  avatarMsg.value = ''
  try {
    await request.delete('/auth/avatar')
    await auth.fetchUser()
    avatarOk.value = true
    avatarMsg.value = '头像已删除'
    emit('changed')
  } catch (error) {
    avatarOk.value = false
    avatarMsg.value = error.message
  }
}
</script>

<style scoped>
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.avatar-row { display: flex; align-items: center; gap: 16px; }
.avatar-lg { width: 72px; height: 72px; border-radius: 50%; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 700; object-fit: cover; flex-shrink: 0; }
.avatar-info { display: flex; flex-direction: column; gap: 4px; }
.avatar-actions { display: flex; align-items: center; gap: 12px; margin-top: 6px; }
.upload-label { display: inline-flex; }
.upload-label input { display: none; }
.upload-label span { background: var(--bg-tertiary); border: 1px solid var(--border); color: var(--text); padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
.link-btn { background: none; border: none; color: var(--danger); cursor: pointer; font-size: 13px; }
.muted { color: var(--text-secondary); font-size: 13px; }
.success-msg { color: var(--success); margin-top: 10px; font-size: 14px; }
.error-msg { color: var(--danger); margin-top: 10px; font-size: 14px; }
</style>
