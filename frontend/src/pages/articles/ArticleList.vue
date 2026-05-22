<template>
  <div class="page">
    <div class="page-header">
      <h1>文章列表</h1>
      <router-link to="/articles/new" class="btn-primary">写文章</router-link>
    </div>
    <div class="filter-bar">
      <button :class="{ active: filter === 'all' }" @click="setFilter('all')">全部</button>
      <button :class="{ active: filter === 'public' }" @click="setFilter('public')">公开</button>
      <button v-if="auth.isAdmin()" :class="{ active: filter === 'internal' }" @click="setFilter('internal')">内部</button>
      <div class="tag-filter">
        <span v-for="tag in allTags" :key="tag" :class="['tag-btn', { active: currentTag === tag }]" @click="filterByTag(tag)">{{ tag }}</span>
      </div>
    </div>
    <div v-if="articles.length === 0" class="empty">暂无文章</div>
    <div v-else class="article-list">
      <div v-for="article in articles" :key="article.id" class="article-card">
        <router-link :to="'/articles/' + article.id" class="article-title">
          <span v-if="article.is_pinned" class="pin-badge">📌</span>
          <span v-if="article.is_internal" class="internal-badge">🔒</span>
          {{ article.title }}
        </router-link>
        <div class="article-meta">
          <span>作者：{{ article.author }}</span>
          <span>👍 {{ article.likes_count }} · 💬 {{ article.comments_count }}</span>
          <span>{{ new Date(article.created_at).toLocaleDateString() }}</span>
        </div>
        <div class="article-tags" v-if="article.tags?.length">
          <span v-for="t in article.tags" :key="t" class="mini-tag">{{ t }}</span>
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
const allTags = ref([])
const currentTag = ref('')
const filter = ref('public')
const total = ref(0)
const page = ref(1)
const loading = ref(false)

async function fetchArticles(reset = false) {
  if (reset) { page.value = 1; articles.value = [] }
  loading.value = true
  const params = { page: page.value, limit: 10 }
  if (currentTag.value) params.tag = currentTag.value
  // 根据筛选添加参数
  if (filter.value === 'internal') {
    params.internal = 'true'
  } else if (filter.value === 'public') {
    params.public = 'true'  // 后端需处理此参数，暂时用 is_internal=false 表示公开
  }
  const res = await axios.get('/api/v1/articles/', { params, headers: { Authorization: `Bearer ${auth.token}` } })
  articles.value = reset ? res.data.items : [...articles.value, ...res.data.items]
  total.value = res.data.total
  page.value++
  loading.value = false
}

function setFilter(f) { filter.value = f; fetchArticles(true) }
function loadMore() { fetchArticles() }
function filterByTag(tag) {
  currentTag.value = currentTag.value === tag ? '' : tag
  fetchArticles(true)
}

onMounted(async () => {
  fetchArticles()
  const res = await axios.get('/api/v1/articles/?limit=1000', { headers: { Authorization: `Bearer ${auth.token}` } })
  const tags = new Set()
  res.data.items.forEach(a => a.tags?.forEach(t => tags.add(t)))
  allTags.value = [...tags]
})
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h1 { font-size: 26px; font-weight: 700; }
.btn-primary { background: var(--primary); color: white; padding: 10px 20px; border-radius: 8px; font-weight: 600; text-decoration: none; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
.filter-bar button { background: var(--bg-secondary); border: 1px solid var(--border); padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 13px; color: var(--text); }
.filter-bar button.active { background: var(--primary); color: white; border-color: var(--primary); }
.tag-filter { display: flex; gap: 8px; flex-wrap: wrap; margin-left: 12px; }
.tag-btn { background: var(--bg-secondary); border: 1px solid var(--border); padding: 6px 14px; border-radius: 20px; cursor: pointer; font-size: 13px; }
.tag-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
.empty { text-align: center; color: var(--text-secondary); padding: 60px 0; }
.article-list { display: flex; flex-direction: column; gap: 12px; }
.article-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.article-card:hover { box-shadow: var(--shadow); }
.article-title { font-size: 18px; font-weight: 600; color: var(--text); text-decoration: none; }
.pin-badge { margin-right: 4px; }
.internal-badge { margin-right: 4px; color: var(--danger); }
.article-meta { display: flex; gap: 20px; margin-top: 8px; font-size: 13px; color: var(--text-secondary); flex-wrap: wrap; }
.article-tags { margin-top: 8px; display: flex; gap: 6px; }
.mini-tag { background: var(--primary-light); color: var(--primary); padding: 2px 10px; border-radius: 12px; font-size: 12px; }
.load-more { text-align: center; margin-top: 20px; }
.load-more button { background: var(--bg-secondary); border: 1px solid var(--border); padding: 10px 30px; border-radius: 8px; cursor: pointer; color: var(--text); }
</style>
