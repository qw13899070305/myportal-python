<template>
  <div class="articles">
    <h2>文章列表</h2>
    <div v-if="loading">加载中...</div>
    <div v-for="article in articles" :key="article.id" class="article-card">
      <router-link :to="`/articles/${article.id}`">
        <h3>{{ article.title }}</h3>
        <p>作者: {{ article.author }} | 点赞: {{ article.likes_count }} | 评论: {{ article.comments_count }}</p>
        <span v-for="tag in article.tags" :key="tag" class="tag">{{ tag }}</span>
      </router-link>
    </div>
    <div v-if="total > articles.length" class="load-more">
      <button @click="loadMore" :disabled="loading">加载更多</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const articles = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)

const token = localStorage.getItem('token')
const headers = token ? { Authorization: `Bearer ${token}` } : {}

async function loadArticles() {
  loading.value = true
  try {
    const res = await axios.get(`/api/v1/articles?page=${page.value}&limit=10`, { headers })
    articles.value = [...articles.value, ...res.data.items]
    total.value = res.data.total
    page.value++
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

function loadMore() { loadArticles() }

onMounted(() => loadArticles())
</script>

<style scoped>
.article-card { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 8px; }
.article-card a { text-decoration: none; color: inherit; }
.tag { display: inline-block; background: #eee; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 12px; }
button { padding: 10px 20px; cursor: pointer; }
</style>
