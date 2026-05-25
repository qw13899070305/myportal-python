<template>
  <div>
    <h2>文章审核</h2>
    <div v-if="articles.length === 0">暂无待审核文章</div>
    <div v-for="a in articles" :key="a.id" class="card">
      <div>
        <strong>{{ a.title }}</strong> - {{ a.author }}
        <div class="actions">
          <button @click="review(a.id, 'approve')">通过</button>
          <button @click="review(a.id, 'reject')">拒绝</button>
          <button @click="deleteArticle(a.id)" class="btn-delete">删除</button>
          <router-link :to="'/articles/'+a.id" target="_blank" class="btn-preview">查看</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const articles = ref([])

const fetchPending = async () => {
  const res = await axios.get('/api/v1/articles/?status=pending', { headers: { Authorization: `Bearer ${auth.token}` } })
  articles.value = res.data.items
}

const review = async (id, action) => {
  await axios.post(`/api/v1/articles/review/${id}?action=${action}`, {}, { headers: { Authorization: `Bearer ${auth.token}` } })
  await fetchPending()
}

const deleteArticle = async (id) => {
  if (!confirm('确定永久删除该文章？')) return
  await axios.delete(`/api/v1/articles/admin/${id}`, { headers: { Authorization: `Bearer ${auth.token}` } })
  await fetchPending()
}

onMounted(fetchPending)
</script>

<style scoped>
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
.actions { display: flex; gap: 8px; margin-top: 8px; }
button { padding: 6px 14px; border-radius: 6px; border: none; cursor: pointer; }
button:first-of-type { background: var(--success); color: white; }
button:nth-of-type(2) { background: var(--danger); color: white; }
.btn-delete { background: var(--danger-light); color: var(--danger); }
.btn-preview { padding: 6px 14px; border-radius: 6px; background: var(--bg-tertiary); color: var(--text); text-decoration: none; font-size: 14px; }
</style>
