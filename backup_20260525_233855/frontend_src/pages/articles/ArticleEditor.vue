<template>
  <div class="page">
    <h1>写文章</h1>
    <form @submit.prevent="submit">
      <div class="form-group"><label>标题</label><input v-model="title" placeholder="文章标题" required /></div>
      <div class="form-group"><label>标签（逗号分隔）</label><input v-model="tagsInput" placeholder="例如：技术,前端" /></div>
      <div class="editor-wrapper">
        <div class="editor-pane">
          <label>内容（Markdown）</label>
          <textarea v-model="content" placeholder="支持 Markdown..." required></textarea>
        </div>
        <div class="preview-pane">
          <label>预览</label>
          <div class="preview-content" v-html="previewHtml"></div>
        </div>
      </div>
      <div class="form-row">
        <label class="checkbox-label"><input type="checkbox" v-model="isInternal" /> 内部文章</label>
      </div>
      <button type="submit" class="btn-primary" :disabled="!title.trim() || !content.trim()">发布</button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'
import { marked } from 'marked'

const router = useRouter()
const auth = useAuthStore()
const title = ref('')
const content = ref('')
const tagsInput = ref('')
const isInternal = ref(false)
const previewHtml = computed(() => content.value ? marked(content.value) : '<p style="color:#999">预览区域</p>')

async function submit() {
  const tags = tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  await axios.post('/api/v1/articles/submit', {
    title: title.value, content: content.value, is_internal: isInternal.value, tags
  }, { headers: { Authorization: `Bearer ${auth.token}` } })
  router.push('/articles')
}
</script>

<style scoped>
.page { max-width: 1000px; margin: 0 auto; }
h1 { font-size: 26px; margin-bottom: 24px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-weight: 600; margin-bottom: 6px; }
input { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); font-size: 15px; }
.editor-wrapper { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 16px; }
@media (max-width: 768px) { .editor-wrapper { grid-template-columns: 1fr; } }
.editor-pane label, .preview-pane label { display: block; font-weight: 600; margin-bottom: 6px; }
textarea { width: 100%; min-height: 400px; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); resize: vertical; font-family: monospace; }
.preview-content { min-height: 400px; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); line-height: 1.8; overflow-y: auto; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 16px; }
.btn-primary { background: var(--primary); color: white; padding: 12px 30px; border-radius: 8px; font-weight: 600; cursor: pointer; border: none; font-size: 16px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
