<template>
  <div>
    <h2>文件管理</h2>
    <div class="search-bar">
      <input v-model="search" placeholder="搜索文件..." @input="fetchFiles" />
      <button @click="fetchFiles" class="btn-refresh">刷新</button>
    </div>
    <table v-if="files.length > 0">
      <thead>
        <tr><th>ID</th><th>文件名</th><th>大小</th><th>上传时间</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="file in files" :key="file.id">
          <td>{{ file.id }}</td>
          <td>{{ file.name }}</td>
          <td>{{ formatSize(file.size) }}</td>
          <td>{{ new Date(file.time).toLocaleString() }}</td>
          <td>
            <button @click="deleteFile(file.id)" class="btn-small btn-danger">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">暂无文件</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const files = ref([])
const search = ref('')

async function fetchFiles() {
  try {
    const res = await axios.get('/api/v1/files/', {
      params: { search: search.value, limit: 100 },
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    files.value = res.data.items || []
  } catch (e) {
    console.error('获取文件列表失败', e)
  }
}

function formatSize(b) {
  if (!b) return '0 B'
  const k = 1024, s = ['B','KB','MB','GB']
  const i = Math.floor(Math.log(b) / Math.log(k))
  return (b / Math.pow(k, i)).toFixed(1) + ' ' + s[i]
}

async function deleteFile(id) {
  if (!confirm('确定删除该文件？')) return
  try {
    await axios.delete(`/api/v1/files/${id}`, {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    fetchFiles()
  } catch (e) {
    alert('删除失败')
  }
}

onMounted(fetchFiles)
</script>

<style scoped>
.search-bar { display: flex; gap: 12px; margin-bottom: 16px; }
input { padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); width: 250px; }
.btn-refresh { background: var(--bg-secondary); border: 1px solid var(--border); padding: 8px 16px; border-radius: 8px; cursor: pointer; color: var(--text); }
table { width: 100%; border-collapse: collapse; background: var(--bg-secondary); border-radius: 8px; overflow: hidden; margin-top: 12px; }
th, td { padding: 12px; border-bottom: 1px solid var(--border); text-align: left; }
th { background: var(--bg-tertiary); font-size: 14px; color: var(--text-secondary); }
.btn-small { padding: 4px 12px; border-radius: 6px; font-size: 13px; border: none; cursor: pointer; }
.btn-danger { background: var(--danger-light); color: var(--danger); }
.empty { text-align: center; padding: 40px 0; color: var(--text-secondary); }
</style>
