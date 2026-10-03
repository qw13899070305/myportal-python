<template>
  <div>
    <h2>管理仪表盘</h2>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

    <div class="stats">
      <div class="stat-card"><span class="icon">📝</span><span class="num">{{ stats.articles ?? '-' }}</span><span class="label">文章总数</span></div>
      <div class="stat-card"><span class="icon">⏳</span><span class="num">{{ stats.pending_articles ?? '-' }}</span><span class="label">待审核</span></div>
      <div class="stat-card"><span class="icon">📁</span><span class="num">{{ stats.files ?? '-' }}</span><span class="label">文件总数</span></div>
      <div class="stat-card"><span class="icon">🗑️</span><span class="num">{{ stats.trashed_files ?? '-' }}</span><span class="label">回收站</span></div>
      <div class="stat-card"><span class="icon">👥</span><span class="num">{{ stats.users ?? '-' }}</span><span class="label">用户总数</span></div>
      <div class="stat-card"><span class="icon">💬</span><span class="num">{{ stats.chat_messages ?? '-' }}</span><span class="label">聊天消息</span></div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import request from '@/utils/request'

const stats = ref({})
const errorMsg = ref('')

onMounted(async () => {
  try {
    stats.value = await request.get('/admin/stats')
  } catch (error) {
    errorMsg.value = error.message
  }
})
</script>

<style scoped>
h2 { margin-bottom: 20px; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 16px; }
.stat-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.icon { font-size: 26px; }
.num { font-size: 26px; font-weight: 700; }
.label { font-size: 13px; color: var(--text-secondary); }
</style>
