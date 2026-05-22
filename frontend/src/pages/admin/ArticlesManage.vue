<template>
  <div>
    <h2>文章审核</h2>
    <div v-if="articles.length === 0">暂无待审核文章</div>
    <div v-for="a in articles" :key="a.id" class="card">
      <strong>{{ a.title }}</strong> - {{ a.author }}
      <div class="actions">
        <button @click="review(a.id, 'approve')">通过</button>
        <button @click="review(a.id, 'reject')">拒绝</button>
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

onMounted(fetchPending)
</script>

<style scoped>
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
.actions { display: flex; gap: 8px; }
button { padding: 6px 14px; border-radius: 6px; border: none; cursor: pointer; }
button:first-child { background: var(--success); color: white; }
button:last-child { background: var(--danger); color: white; }
</style>
