<template>
  <div>
    <h2>聊天管理</h2>
    <div class="toolbar">
      <button @click="fetchMessages" class="btn-refresh">刷新</button>
      <button @click="clearAll" class="btn-danger">清空所有记录</button>
    </div>
    <table v-if="messages.length > 0">
      <thead><tr><th>ID</th><th>用户</th><th>内容</th><th>时间</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="msg in messages" :key="msg.id">
          <td>{{ msg.id }}</td>
          <td>{{ msg.user }}</td>
          <td>{{ msg.content }}</td>
          <td>{{ new Date(msg.time).toLocaleString() }}</td>
          <td>
            <button @click="deleteMsg(msg.id)" class="btn-small">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">暂无聊天记录</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const messages = ref([])

async function fetchMessages() {
  const res = await axios.get('/api/v1/admin/chat/messages', {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  messages.value = res.data.items || []
}

async function deleteMsg(id) {
  await axios.delete(`/api/v1/admin/chat/messages/${id}`, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  fetchMessages()
}

async function clearAll() {
  if (!confirm('确定清空所有聊天记录？')) return
  await axios.delete('/api/v1/admin/chat/clear', {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  fetchMessages()
}

onMounted(fetchMessages)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.btn-refresh { background: var(--bg-secondary); border: 1px solid var(--border); padding: 8px 16px; border-radius: 8px; cursor: pointer; color: var(--text); }
.btn-danger { background: var(--danger); color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
table { width: 100%; border-collapse: collapse; background: var(--bg-secondary); border-radius: 8px; overflow: hidden; }
th, td { padding: 10px 14px; border-bottom: 1px solid var(--border); text-align: left; }
th { background: var(--bg-tertiary); font-size: 14px; color: var(--text-secondary); }
.btn-small { background: var(--danger-light); color: var(--danger); border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.empty { text-align: center; padding: 40px 0; color: var(--text-secondary); }
</style>
