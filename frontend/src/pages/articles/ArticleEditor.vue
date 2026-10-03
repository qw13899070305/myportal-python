<template>
  <div class="page">
    <h1>写文章</h1>

    <form @submit.prevent="submit">
      <div class="form-group">
        <label>标题</label>
        <input v-model.trim="title" maxlength="200" placeholder="文章标题" required />
      </div>

      <div class="form-group">
        <label>标签（逗号分隔，最多 10 个）</label>
        <input v-model="tagsInput" placeholder="例如：技术,前端" />
      </div>

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

      <label class="checkbox-label">
        <input type="checkbox" v-model="isInternal" />
        内部文章（仅登录用户与管理员可见）
      </label>

      <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
      <p v-if="notice" class="notice">{{ notice }}</p>

      <button type="submit" class="btn-primary" :disabled="submitting || !title || !content">
        {{ submitting ? '提交中...' : '发布' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'

const router = useRouter()
const auth = useAuthStore()

const title = ref('')
const content = ref('')
const tagsInput = ref('')
const isInternal = ref(false)
const submitting = ref(false)
const errorMsg = ref('')
const notice = ref('')

// 预览同样要消毒：Markdown 中可以直接内嵌 HTML
const previewHtml = computed(() =>
  DOMPurify.sanitize(marked.parse(content.value || '_预览区域_', { async: false })),
)

async function submit() {
  errorMsg.value = ''
  notice.value = ''
  submitting.value = true

  const tags = tagsInput.value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)

  try {
    // 后端同时提供 /articles 与 /articles/submit，这里用标准 REST 路径
    const article = await request.post('/articles/', {
      title: title.value,
      content: content.value,
      tags,
      is_internal: isInternal.value,
    })
    notice.value = auth.isAdmin() ? '发布成功' : '已提交，等待管理员审核'
    router.push({ name: 'article-detail', params: { id: article.id } })
  } catch (error) {
    errorMsg.value = error.message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page { max-width: 1000px; margin: 0 auto; }
h1 { font-size: 26px; margin-bottom: 24px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-weight: 600; margin-bottom: 6px; }
.form-group input { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); font-size: 15px; }
.editor-wrapper { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 16px; }
@media (max-width: 768px) { .editor-wrapper { grid-template-columns: 1fr; } }
.editor-pane label, .preview-pane label { display: block; font-weight: 600; margin-bottom: 6px; }
textarea { width: 100%; min-height: 400px; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); resize: vertical; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 14px; }
.preview-content { min-height: 400px; padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); line-height: 1.8; overflow-y: auto; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 16px; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.notice { color: var(--success); margin-bottom: 12px; }
.btn-primary { background: var(--primary); color: white; padding: 12px 30px; border-radius: 8px; font-weight: 600; cursor: pointer; border: none; font-size: 16px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
