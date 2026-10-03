<template>
  <div>
    <h1 class="page-title">{{ t('nav.dashboard') }}</h1>

    <p v-if="!auth.isAuthenticated" class="empty-state">
      👋 欢迎访问 MyPortal。<router-link :to="{ name: 'login' }">登录</router-link>
      后可以上传文件、发布文章和参与聊天。
    </p>
    <p v-else-if="!auth.isAdmin()" class="empty-state">
      👋 欢迎回来，{{ auth.user?.username }}。请通过侧边栏访问各项功能。
    </p>

    <template v-else>
      <div class="stats-row">
        <div class="stat-card">
          <span class="stat-label">文章总数</span>
          <span class="stat-num">{{ stats.articles ?? '-' }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">待审核</span>
          <span class="stat-num">{{ stats.pending_articles ?? '-' }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">文件总数</span>
          <span class="stat-num">{{ stats.files ?? '-' }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">用户总数</span>
          <span class="stat-num">{{ stats.users ?? '-' }}</span>
        </div>
      </div>

      <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

      <div class="quick-row">
        <router-link :to="{ name: 'files' }" class="quick-card">
          <span class="quick-icon">📂</span><span>文件管理</span>
        </router-link>
        <router-link :to="{ name: 'articles' }" class="quick-card">
          <span class="quick-icon">📰</span><span>文章管理</span>
        </router-link>
        <router-link :to="{ name: 'admin' }" class="quick-card">
          <span class="quick-icon">⚙️</span><span>管理后台</span>
        </router-link>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'

const { t } = useI18n()
const auth = useAuthStore()

const stats = ref({})
const errorMsg = ref('')

async function loadStats() {
  if (!auth.isAdmin()) {
    stats.value = {}
    return
  }
  errorMsg.value = ''
  try {
    stats.value = await request.get('/admin/stats')
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(loadStats)
// 登录状态可能在挂载之后才恢复完成，这里补一次
watch(() => auth.user, loadStats)
</script>

<style scoped>
.page-title { font-size: 26px; font-weight: 700; margin-bottom: 28px; letter-spacing: -0.5px; }
.empty-state { color: var(--text-secondary); font-size: 15px; padding: 60px 0; text-align: center; }
.empty-state a { color: var(--primary); font-weight: 600; }
.error-msg { color: var(--danger); margin-bottom: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 18px; margin-bottom: 32px; }
.stat-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; display: flex; flex-direction: column; gap: 6px; box-shadow: var(--shadow-xs); transition: box-shadow var(--transition), transform var(--transition); }
.stat-card:hover { box-shadow: var(--shadow); transform: translateY(-2px); }
.stat-label { font-size: 13px; color: var(--text-secondary); }
.stat-num { font-size: 28px; font-weight: 700; }
.quick-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 14px; }
.quick-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px; font-size: 15px; font-weight: 500; transition: all var(--transition); }
.quick-card:hover { border-color: var(--primary); box-shadow: var(--shadow); transform: translateY(-2px); }
.quick-icon { font-size: 26px; }
</style>
