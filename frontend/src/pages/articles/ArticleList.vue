<!--
  文章列表页：只负责取数（分页/筛选/搜索）、组装筛选条、标签条和卡片，
  具体展示交给 components/articles 下的小零件。
-->
<template>
  <div class="page">
    <div class="page-header">
      <h1>文章</h1>
      <router-link v-if="auth.isAuthenticated" :to="{ name: 'article-new' }" class="btn-primary">
        写文章
      </router-link>
    </div>

    <ArticleFilterBar
      :scope="scope"
      :search="search"
      :is-authenticated="auth.isAuthenticated"
      :is-admin="auth.isAdmin()"
      @update:scope="setScope"
      @update:search="search = $event"
      @search="reload"
    />

    <ArticleTagFilter :tags="allTags" :active="currentTag" @select="filterByTag" />

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    <SkeletonLoader v-if="loading && articles.length === 0" :count="3" />
    <p v-else-if="articles.length === 0" class="hint">暂无文章</p>

    <div v-else class="article-list">
      <ArticleCard v-for="article in articles" :key="article.id" :article="article" />
    </div>

    <div v-if="total > articles.length" class="load-more">
      <button type="button" :disabled="loading" @click="loadMore">加载更多</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import ArticleCard from '@/components/articles/ArticleCard.vue'
import ArticleFilterBar from '@/components/articles/ArticleFilterBar.vue'
import ArticleTagFilter from '@/components/articles/ArticleTagFilter.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'

const PAGE_SIZE = 10

const auth = useAuthStore()

const articles = ref([])
const allTags = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const errorMsg = ref('')
const search = ref('')
const currentTag = ref('')
const scope = ref('all')

const params = computed(() => {
  const query = { page: page.value, size: PAGE_SIZE }
  if (search.value.trim()) query.search = search.value.trim()
  if (currentTag.value) query.tag = currentTag.value
  if (scope.value === 'mine') query.mine = true
  if (scope.value === 'pending') query.status = 'pending'
  if (scope.value === 'internal') query.internal = true
  return query
})

async function fetchArticles({ append = false } = {}) {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await request.get('/articles/', { params: params.value })
    articles.value = append ? [...articles.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  } finally {
    loading.value = false
  }
}

async function loadTags() {
  try {
    allTags.value = await request.get('/articles/tags')
  } catch {
    allTags.value = []
  }
}

function reload() {
  page.value = 1
  fetchArticles()
}

function loadMore() {
  page.value += 1
  fetchArticles({ append: true })
}

function setScope(next) {
  scope.value = next
  reload()
}

function filterByTag(tag) {
  currentTag.value = currentTag.value === tag ? '' : tag
  reload()
}

onMounted(() => {
  reload()
  loadTags()
})
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h1 { font-size: 26px; font-weight: 700; }
.btn-primary { background: var(--primary); color: white; padding: 10px 20px; border-radius: 8px; font-weight: 600; text-decoration: none; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.hint { text-align: center; color: var(--text-secondary); padding: 60px 0; }
.article-list { display: flex; flex-direction: column; gap: 12px; }
.load-more { text-align: center; margin-top: 20px; }
.load-more button { background: var(--bg-secondary); border: 1px solid var(--border); padding: 10px 30px; border-radius: 8px; cursor: pointer; color: var(--text); }
</style>
