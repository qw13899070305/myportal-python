<template>
  <div class="page">
    <div class="page-header">
      <h1>文章管理</h1>
      <router-link to="/articles/new" class="btn-primary">写文章</router-link>
    </div>
    <div v-if="articles.length === 0" class="empty">暂无文章</div>
    <div v-else class="article-list">
      <div v-for="article in articles" :key="article.id" class="article-card">
        <router-link :to="'/articles/' + article.id" class="article-title">{{ article.title }}</router-link>
        <div class="article-meta">
          <span>作者：{{ article.author }}</span>
          <span>点赞 {{ article.likes_count }} · 评论 {{ article.comments_count }}</span>
          <span>{{ new Date(article.created_at).toLocaleDateString() }}</span>
        </div>
      </div>
    </div>
    <div v-if="total > articles.length" class="load-more">
      <button @click="loadMore" :disabled="loading">加载更多</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const articles = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)

const fetchArticles = async () => {
  loading.value = true
  const res = await axios.get('/api/v1/articles/', {
    params: { page: page.value, limit: 10 },
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  articles.value = [...articles.value, ...res.data.items]
  total.value = res.data.total
  page.value++
  loading.value = false
}

const loadMore = () => fetchArticles()

onMounted(() => fetchArticles())
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h1 { font-size: 26px; font-weight: 700; }
.btn-primary { background: var(--primary); color: white; padding: 10px 20px; border-radius: 8px; font-weight: 600; text-decoration: none; transition: 0.2s; }
.btn-primary:hover { background: var(--primary-hover); }
.empty { text-align: center; color: var(--text-secondary); padding: 60px 0; }
.article-list { display: flex; flex-direction: column; gap: 12px; }
.article-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: 0.2s; }
.article-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.article-title { font-size: 18px; font-weight: 600; color: var(--text); text-decoration: none; }
.article-meta { display: flex; gap: 20px; margin-top: 8px; font-size: 13px; color: var(--text-secondary); }
.load-more { text-align: center; margin-top: 20px; }
.load-more button { background: var(--bg-secondary); border: 1px solid var(--border); padding: 10px 30px; border-radius: 8px; cursor: pointer; color: var(--text); }
</style>
