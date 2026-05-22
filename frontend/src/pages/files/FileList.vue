<template>
  <div>
    <h1 class="page-title">文件管理</h1>
    <div class="search-bar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="search" placeholder="搜索文件..." @input="fetchFiles" />
    </div>
    <div class="file-grid">
      <div v-for="file in files" :key="file.id" class="file-card" @click="$router.push('/files/'+file.id)">
        <span class="file-type">{{ getIcon(file.name) }}</span>
        <span class="file-name">{{ file.name }}</span>
        <span class="file-meta">{{ formatSize(file.size) }}</span>
      </div>
    </div>
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
  const res = await axios.get('/api/v1/files/', { params: { search: search.value }, headers: { Authorization: `Bearer ${auth.token}` } })
  files.value = res.data.items
}
function formatSize(b) { if (!b) return '0 B'; const k = 1024, s = ['B','KB','MB','GB']; const i = Math.floor(Math.log(b)/Math.log(k)); return (b/Math.pow(k,i)).toFixed(1)+' '+s[i] }
function getIcon(n) { const e = n.split('.').pop()?.toLowerCase(); const m = { pdf:'📄',doc:'📝',docx:'📝',xls:'📊',xlsx:'📊',ppt:'📽️',pptx:'📽️',jpg:'🖼️',jpeg:'🖼️',png:'🖼️',gif:'🖼️',mp4:'🎬',mp3:'🎵',zip:'📦' }; return m[e]||'📎' }
onMounted(fetchFiles)
</script>

<style scoped>
.page-title { font-size: 26px; font-weight: 700; margin-bottom: 24px; }
.search-bar { display: flex; align-items: center; gap: 10px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0 14px; max-width: 380px; margin-bottom: 24px; }
.search-bar input { flex: 1; padding: 12px 0; border: none; background: transparent; color: var(--text); font-size: 15px; outline: none; }
.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }
.file-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; text-align: center; cursor: pointer; transition: all var(--transition); display: flex; flex-direction: column; align-items: center; gap: 8px; }
.file-card:hover { border-color: var(--primary); box-shadow: var(--shadow); transform: translateY(-2px); }
.file-type { font-size: 36px; }
.file-name { font-size: 14px; font-weight: 500; word-break: break-all; line-height: 1.3; }
.file-meta { font-size: 12px; color: var(--text-tertiary); }
</style>
