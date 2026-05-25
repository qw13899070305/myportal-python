<template>
  <div>
    <h2>用户管理</h2>
    <table>
      <thead><tr><th>用户名</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.username }}</td>
          <td>{{ user.roles.join(', ') }}</td>
          <td>{{ user.is_active ? '正常' : '禁用' }}</td>
          <td>
            <button @click="toggleActive(user)">{{ user.is_active ? '禁用' : '启用' }}</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const users = ref([])

const fetchUsers = async () => {
  const res = await axios.get('/api/v1/admin/users', { headers: { Authorization: `Bearer ${auth.token}` } })
  users.value = res.data.items
}

const toggleActive = async (user) => {
  await axios.post(`/api/v1/admin/users/${user.id}/toggle-active`, {}, { headers: { Authorization: `Bearer ${auth.token}` } })
  await fetchUsers()
}

onMounted(fetchUsers)
</script>

<style scoped>
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px; border-bottom: 1px solid var(--border); text-align: left; }
button { padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
</style>
