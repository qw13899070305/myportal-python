<template>
  <div class="page" v-if="article">
    <router-link to="/articles" class="back">← 返回列表</router-link>
    <h1>{{ article.title }}</h1>
    <div class="meta">
      <span>作者：{{ article.author }}</span>
      <span>{{ new Date(article.created_at).toLocaleDateString() }}</span>
    </div>
    <div class="content" v-html="rendered"></div>
    <div class="actions">
      <button @click="toggleLike">{{ article.is_liked ? '❤️' : '🤍' }} {{ article.likes_count }}</button>
      <button @click="toggleBookmark">{{ article.is_bookmarked ? '⭐' : '☆' }} 收藏</button>
    </div>
  </div>
  <div v-else class="loading">加载中...</div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'
import { marked } from 'marked'

const route = useRoute()
const auth = useAuthStore()
const article = ref(null)

const rendered = computed(() => article.value ? marked(article.value.content) : '')

const fetchArticle = async () => {
  const res = await axios.get(`/api/v1/articles/${route.params.id}`, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  article.value = res.data
}

const toggleLike = async () => {
  await axios.post(`/api/v1/articles/${article.value.id}/like`, {}, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  await fetchArticle()
}

const toggleBookmark = async () => {
  await axios.post(`/api/v1/articles/${article.value.id}/bookmark`, {}, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  await fetchArticle()
}

onMounted(() => fetchArticle())
</script>

<style scoped>
.page { max-width: 800px; margin: 0 auto; }
.back { color: var(--primary); text-decoration: none; font-size: 14px; }
h1 { font-size: 32px; margin: 16px 0 8px; }
.meta { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; display: flex; gap: 20px; }
.content { line-height: 1.8; font-size: 16px; }
.actions { margin-top: 32px; display: flex; gap: 12px; }
.actions button { padding: 10px 20px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
.loading { text-align: center; padding: 60px 0; color: var(--text-secondary); }
</style>
