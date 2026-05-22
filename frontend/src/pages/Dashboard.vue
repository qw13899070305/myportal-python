<template>
  <div>
    <h1 class="page-title">仪表盘</h1>
    <p v-if="!auth.isAdmin()" class="empty-state">👋 欢迎回来，请通过侧边栏或底部导航访问各项功能。</p>

    <div v-if="auth.isAdmin()" class="stats-row">
      <div class="stat-card accent-purple">
        <div class="stat-icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
        <div class="stat-body"><span class="stat-label">文章总数</span><span class="stat-num">{{ stats.articles || 0 }}</span></div>
      </div>
      <div class="stat-card accent-green">
        <div class="stat-icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg></div>
        <div class="stat-body"><span class="stat-label">文件总数</span><span class="stat-num">{{ stats.files || 0 }}</span></div>
      </div>
      <div class="stat-card accent-amber">
        <div class="stat-icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg></div>
        <div class="stat-body"><span class="stat-label">用户总数</span><span class="stat-num">{{ stats.users || 0 }}</span></div>
      </div>
    </div>

    <div v-if="auth.isAdmin()" class="quick-row">
      <router-link to="/files" class="quick-card">
        <span class="quick-icon">📂</span><span>文件管理</span>
      </router-link>
      <router-link to="/articles" class="quick-card">
        <span class="quick-icon">📰</span><span>文章管理</span>
      </router-link>
      <router-link to="/admin" class="quick-card">
        <span class="quick-icon">⚙️</span><span>管理后台</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const stats = ref({})

onMounted(async () => {
  if (auth.isAdmin()) {
    try {
      const res = await axios.get('/api/v1/admin/stats', { headers: { Authorization: `Bearer ${auth.token}` } })
      stats.value = res.data
    } catch (e) { console.error(e) }
  }
})
</script>

<style scoped>
.page-title { font-size: 26px; font-weight: 700; margin-bottom: 28px; letter-spacing: -0.5px; }
.empty-state { color: var(--text-secondary); font-size: 15px; padding: 60px 0; text-align: center; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; margin-bottom: 32px; }
.stat-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; display: flex; align-items: center; gap: 16px; box-shadow: var(--shadow-xs); transition: box-shadow var(--transition), transform var(--transition); }
.stat-card:hover { box-shadow: var(--shadow); transform: translateY(-2px); }
.stat-icon-box { width: 48px; height: 48px; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.accent-purple .stat-icon-box { background: var(--primary-light); color: var(--primary); }
.accent-green .stat-icon-box { background: var(--success-light); color: var(--success); }
.accent-amber .stat-icon-box { background: var(--warning-light); color: var(--warning); }
.stat-body { display: flex; flex-direction: column; }
.stat-label { font-size: 13px; color: var(--text-secondary); }
.stat-num { font-size: 28px; font-weight: 700; }
.quick-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 14px; }
.quick-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px; font-size: 15px; font-weight: 500; transition: all var(--transition); }
.quick-card:hover { border-color: var(--primary); box-shadow: var(--shadow); transform: translateY(-2px); }
.quick-icon { font-size: 26px; }
</style>
