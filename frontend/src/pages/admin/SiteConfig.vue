<template>
  <div>
    <h2>站点配置</h2>
    <form @submit.prevent="save">
      <div class="form-group">
        <label>站点名称</label>
        <input v-model="siteName" />
      </div>
      <div class="form-group">
        <label>公告</label>
        <textarea v-model="announcement" rows="4"></textarea>
      </div>
      <div class="form-actions">
        <button type="submit">保存配置</button>
      </div>
      <p v-if="msg" class="success-msg">{{ msg }}</p>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const siteName = ref('')
const announcement = ref('')
const msg = ref('')

onMounted(async () => {
  try {
    const res = await axios.get('/api/v1/admin/config', {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    siteName.value = res.data.site_name || ''
    announcement.value = res.data.announcement || ''
  } catch (e) {
    console.error('加载配置失败', e)
  }
})

async function save() {
  msg.value = ''
  try {
    await axios.post('/api/v1/admin/config', {
      site_name: siteName.value,
      announcement: announcement.value
    }, {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    msg.value = '配置已保存'
  } catch (e) {
    alert('保存失败：' + (e.response?.data?.detail || '网络错误'))
  }
}
</script>

<style scoped>
.form-group { margin-bottom: 20px; }
label { display: block; font-weight: 600; margin-bottom: 8px; color: var(--text-secondary); }
input, textarea { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); font-size: 15px; }
textarea { resize: vertical; }
.form-actions { margin-top: 20px; }
button { background: var(--primary); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; }
button:hover { background: var(--primary-hover); }
.success-msg { margin-top: 12px; color: var(--success); font-size: 14px; }
</style>
