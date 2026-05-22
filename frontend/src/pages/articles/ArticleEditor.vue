<template>
  <div class="page">
    <h1>写文章</h1>
    <form @submit.prevent="submit">
      <input v-model="title" placeholder="文章标题" required class="title-input" />
      <textarea v-model="content" placeholder="支持 Markdown 语法..." required class="content-input"></textarea>
      <div class="form-row">
        <label>
          <input type="checkbox" v-model="isInternal" />
          内部文章（仅管理员/作者可见）
        </label>
      </div>
      <button type="submit" class="btn-primary">发布</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const router = useRouter()
const auth = useAuthStore()
const title = ref('')
const content = ref('')
const isInternal = ref(false)

const submit = async () => {
  await axios.post('/api/v1/articles/submit', {
    title: title.value,
    content: content.value,
    is_internal: isInternal.value
  }, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  router.push('/articles')
}
</script>

<style scoped>
.page { max-width: 800px; margin: 0 auto; }
h1 { font-size: 26px; margin-bottom: 24px; }
.title-input, .content-input { width: 100%; padding: 14px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; font-size: 16px; background: var(--bg-secondary); color: var(--text); }
.content-input { min-height: 300px; resize: vertical; }
.form-row { margin-bottom: 16px; }
.btn-primary { background: var(--primary); color: white; padding: 12px 30px; border-radius: 8px; font-weight: 600; cursor: pointer; border: none; }
.btn-primary:hover { background: var(--primary-hover); }
</style>
