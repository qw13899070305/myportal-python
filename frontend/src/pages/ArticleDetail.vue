<template>
  <div class="article-detail" v-if="article">
    <h1>{{ article.title }}</h1>
    <p>作者: {{ article.author }} | {{ article.created_at }}</p>
    <div class="tags">
      <span v-for="tag in article.tags" :key="tag" class="tag">{{ tag }}</span>
    </div>
    <hr />
    <!-- Markdown 渲染区域 -->
    <div class="content" v-html="renderedContent"></div>
    <div class="actions">
      <button @click="toggleLike">{{ article.is_liked ? '❤️ 已赞' : '🤍 点赞' }} ({{ article.likes_count }})</button>
      <button @click="toggleBookmark">{{ article.is_bookmarked ? '⭐ 已收藏' : '☆ 收藏' }}</button>
    </div>
  </div>
  <div v-else>加载中...</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { marked } from 'marked'

const route = useRoute()
const article = ref(null)
const token = localStorage.getItem('token')
const headers = token ? { Authorization: `Bearer ${token}` } : {}

const renderedContent = computed(() => article.value ? marked(article.value.content) : '')

async function loadArticle() {
  try {
    const res = await axios.get(`/api/v1/articles/${route.params.id}`, { headers })
    article.value = res.data
  } catch (e) { console.error(e) }
}

async function toggleLike() {
  await axios.post(`/api/v1/articles/${article.value.id}/like`, {}, { headers })
  await loadArticle()
}

async function toggleBookmark() {
  await axios.post(`/api/v1/articles/${article.value.id}/bookmark`, {}, { headers })
  await loadArticle()
}

onMounted(() => loadArticle())
</script>

<style scoped>
.content { max-width: 800px; line-height: 1.8; }
.tag { display: inline-block; background: #eee; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 12px; }
.actions { margin-top: 20px; }
button { margin-right: 10px; padding: 8px 16px; cursor: pointer; }
</style>
