<template>
  <div class="profile-page">
    <h1 class="page-title">个人中心</h1>
    <div class="profile-card">
      <div class="avatar-large">{{ auth.user?.username?.charAt(0) || '?' }}</div>
      <h2>{{ auth.user?.username }}</h2>
      <p class="roles">角色：{{ auth.user?.roles?.join(', ') || '无' }}</p>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../../stores/auth'
const auth = useAuthStore()
</script>

<style scoped>
.page-title { font-size: 28px; font-weight: 700; margin-bottom: 24px; }
.profile-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 40px; text-align: center; box-shadow: var(--shadow-sm); }
.avatar-large { width: 80px; height: 80px; border-radius: 50%; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 36px; font-weight: 700; margin: 0 auto 16px; }
h2 { font-size: 22px; margin-bottom: 8px; }
.roles { color: var(--text-secondary); }
</style>
