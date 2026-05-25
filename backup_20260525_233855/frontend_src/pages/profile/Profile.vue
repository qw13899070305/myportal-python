<template>
  <div class="profile">
    <h1>个人中心</h1>
    <div class="card">
      <div class="avatar-row">
        <div class="avatar-lg">{{ auth.user?.username?.charAt(0) }}</div>
        <input type="file" @change="uploadAvatar" accept="image/*" />
      </div>
      <h2>{{ auth.user?.username }}</h2>
      <p>角色：{{ auth.user?.roles?.join(', ') }}</p>
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
    <div class="card">
      <h3>🔒 修改密码</h3>
      <form @submit.prevent="changePassword">
        <input v-model="oldPassword" type="password" placeholder="当前密码" required />
        <input v-model="newPassword" type="password" placeholder="新密码" required />
        <button type="submit">修改密码</button>
      </form>
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
const oldPassword = ref('')
const newPassword = ref('')

onMounted(async () => {
  const [rf, bm] = await Promise.all([
    axios.get('/api/v1/files/recent', { headers: { Authorization: `Bearer ${auth.token}` } }),
    axios.get('/api/v1/articles/bookmarks/list', { headers: { Authorization: `Bearer ${auth.token}` } })
  ])
  recentFiles.value = rf.data.items
  bookmarks.value = bm.data.items
})

async function uploadAvatar(e) {
  const file = e.target.files[0]
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  await axios.post('/api/v1/auth/avatar', form, { headers: { Authorization: `Bearer ${auth.token}` } })
  alert('头像更新成功')
}

async function changePassword() {
  try {
    await axios.post('/api/v1/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value
    }, { headers: { Authorization: `Bearer ${auth.token}` } })
    alert('密码修改成功')
  } catch (e) {
    alert('修改失败：' + (e.response?.data?.detail || '网络错误'))
  }
}
</script>

<style scoped>
.profile { max-width: 600px; margin: 0 auto; }
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.avatar-row { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.avatar-lg { width: 64px; height: 64px; border-radius: 50%; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 700; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; }
ul { list-style: none; padding: 0; }
li { padding: 4px 0; border-bottom: 1px solid var(--border); }
input { padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); margin-bottom: 10px; width: 100%; }
button { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; }
</style>
