<template>
  <div>
    <h1>管理仪表盘</h1>
    <div class="stats">
      <div class="stat-card">📝 文章数: {{ stats.articles }}</div>
      <div class="stat-card">📁 文件数: {{ stats.files }}</div>
      <div class="stat-card">👥 用户数: {{ stats.users }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'
const auth = useAuthStore()
const stats = ref({})
onMounted(async () => {
  const res = await axios.get('/api/v1/admin/stats', { headers: { Authorization: `Bearer ${auth.token}` } })
  stats.value = res.data
})
</script>

<style scoped>
.stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-top: 20px; }
.stat-card { background: var(--bg-secondary); border: 1px solid var(--border); padding: 24px; border-radius: 12px; text-align: center; font-size: 18px; }
</style>
