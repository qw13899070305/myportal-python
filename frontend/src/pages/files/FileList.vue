<template>
  <div>
    <h1 class="page-title">文件管理</h1>
    <div class="upload-area"><input type="file" multiple @change="handleUpload" /></div>
    <div class="search-bar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input v-model="search" placeholder="搜索文件..." @input="fetchFiles" />
    </div>
    <div class="file-grid">
      <div v-for="file in files" :key="file.id" class="file-card" @click="openPreview(file)" @contextmenu.prevent="showMenu($event, file)">
        <span class="file-type">{{ getIcon(file.name) }}</span>
        <span class="file-name">{{ file.name }}</span>
        <span class="file-meta">{{ formatSize(file.size) }}</span>
      </div>
    </div>
    <!-- 右键菜单 -->
    <div v-if="contextMenu.visible" class="context-menu" :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }">
      <div @click="renameFile">重命名</div>
      <div @click="deleteFile">删除</div>
      <div @click="contextMenu.visible = false">取消</div>
    </div>
    <!-- 重命名弹窗 -->
    <div v-if="renameDialog.visible" class="modal">
      <input v-model="renameDialog.newName" placeholder="新文件名" />
      <button @click="confirmRename">确认</button>
      <button @click="renameDialog.visible = false">取消</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const router = useRouter()
const auth = useAuthStore()
const files = ref([])
const search = ref('')
const contextMenu = ref({ visible: false, x: 0, y: 0, file: null })
const renameDialog = ref({ visible: false, newName: '', file: null })

async function fetchFiles() {
  const res = await axios.get('/api/v1/files/', { params: { search: search.value }, headers: { Authorization: `Bearer ${auth.token}` } })
  files.value = res.data.items
}

function formatSize(b) { if (!b) return '0 B'; const k = 1024, s = ['B','KB','MB','GB']; const i = Math.floor(Math.log(b)/Math.log(k)); return (b/Math.pow(k,i)).toFixed(1)+' '+s[i] }
function getIcon(n) { const e = n.split('.').pop()?.toLowerCase(); const m = { pdf:'📄',doc:'📝',docx:'📝',xls:'📊',xlsx:'📊',ppt:'📽️',pptx:'📽️',jpg:'🖼️',jpeg:'🖼️',png:'🖼️',gif:'🖼️',mp4:'🎬',mp3:'🎵',zip:'📦' }; return m[e]||'📎' }

function openPreview(file) { router.push('/files/' + file.id) }
function showMenu(e, file) { contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, file } }

function renameFile() {
  contextMenu.value.visible = false
  renameDialog.value = { visible: true, newName: contextMenu.value.file.name, file: contextMenu.value.file }
}
async function confirmRename() {
  await axios.put(`/api/v1/files/rename/${renameDialog.value.file.id}?new_name=${renameDialog.value.newName}`, {}, { headers: { Authorization: `Bearer ${auth.token}` } })
  renameDialog.value.visible = false
  fetchFiles()
}

async function deleteFile() {
  if (confirm('确定删除该文件？')) {
    await axios.delete(`/api/v1/files/${contextMenu.value.file.id}`, { headers: { Authorization: `Bearer ${auth.token}` } })
    contextMenu.value.visible = false
    fetchFiles()
  }
}

async function handleUpload(e) {
  for (let file of e.target.files) {
    const form = new FormData(); form.append('file', file)
    await axios.post('/api/v1/files/upload', form, { headers: { Authorization: `Bearer ${auth.token}` } })
  }
  fetchFiles()
}

onMounted(fetchFiles)
</script>

<style scoped>
.page-title { font-size: 26px; font-weight: 700; margin-bottom: 24px; }
.upload-area { margin-bottom: 16px; }
.upload-area input { background: var(--bg-secondary); color: var(--text); }
.search-bar { display: flex; align-items: center; gap: 10px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 0 14px; max-width: 380px; margin-bottom: 24px; }
.search-bar input { flex: 1; padding: 12px 0; border: none; background: transparent; color: var(--text); outline: none; }
.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }
.file-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 22px; text-align: center; cursor: pointer; transition: 0.2s; }
.file-card:hover { border-color: var(--primary); box-shadow: var(--shadow); transform: translateY(-2px); }
.file-type { font-size: 36px; }
.file-name { font-size: 14px; font-weight: 500; word-break: break-all; }
.file-meta { font-size: 12px; color: var(--text-tertiary); }
.context-menu { position: fixed; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; box-shadow: var(--shadow-lg); z-index: 200; min-width: 120px; }
.context-menu div { padding: 8px 16px; cursor: pointer; }
.context-menu div:hover { background: var(--bg-tertiary); }
.modal { position: fixed; top: 30%; left: 50%; transform: translate(-50%, -50%); background: var(--bg-secondary); padding: 24px; border-radius: 12px; box-shadow: var(--shadow-lg); z-index: 300; }
.modal input { padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); margin-right: 8px; }
.modal button { margin: 0 4px; }
</style>
