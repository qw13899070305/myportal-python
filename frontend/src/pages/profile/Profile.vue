<template>
  <div class="profile">
    <h1>个人中心</h1>
    <div class="card">
      <div class="avatar-lg">{{ auth.user?.username?.charAt(0) }}</div>
      <h2>{{ auth.user?.username }}</h2>
      <p>角色：{{ auth.user?.roles?.join(', ') }}</p>
      <p>注册时间：{{ auth.user?.created_at ? new Date(auth.user.created_at).toLocaleDateString() : '-' }}</p>
    </div>
    <div class="grid">
      <div class="card">
        <h3>📁 最近文件</h3>
        <ul><li v-for="f in recentFiles" :key="f.id">{{ f.name }}</li></ul>
      </div>
      <div class="card">
        <h3>⭐ 收藏文章</h3>
        <ul><li v-for="a in bookmarks" :key="a.id">{{ a.title }}</li></ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const recentFiles = ref([])
const bookmarks = ref([])

onMounted(async () => {
  const [rf, bm] = await Promise.all([
    axios.get('/api/v1/files/recent', { headers: { Authorization: `Bearer ${auth.token}` } }),
    axios.get('/api/v1/articles/bookmarks/list', { headers: { Authorization: `Bearer ${auth.token}` } })
  ])
  recentFiles.value = rf.data.items
  bookmarks.value = bm.data.items
})
</script>

<style scoped>
.profile { max-width: 600px; margin: 0 auto; }
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.avatar-lg { width: 64px; height: 64px; border-radius: 50%; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 700; margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; }
ul { list-style: none; padding: 0; }
li { padding: 4px 0; border-bottom: 1px solid var(--border); }
</style>
