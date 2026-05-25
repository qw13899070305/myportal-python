<template>
  <div class="preview-page">
    <div class="toolbar">
      <button @click="$router.back()" class="back-btn">← 返回</button>
      <a :href="downloadUrl" class="download-btn" v-if="isAdmin">下载文件</a>
    </div>
    <iframe :src="previewUrl" class="preview-frame"></iframe>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const fileId = route.params.id
const previewUrl = computed(() => `/api/v1/files/preview/${fileId}`)
const downloadUrl = computed(() => `/api/v1/files/download/${fileId}`)
const isAdmin = computed(() => auth.isAdmin())
</script>

<style scoped>
.preview-page { height: calc(100vh - var(--header-height) - 48px); display: flex; flex-direction: column; }
.toolbar { display: flex; gap: 12px; margin-bottom: 12px; align-items: center; }
.back-btn, .download-btn { padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; cursor: pointer; }
.back-btn { background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text); }
.download-btn { background: var(--primary); color: white; }
.preview-frame { flex: 1; border: 1px solid var(--border); border-radius: var(--radius); background: white; }
</style>
