<!-- ArticlesManage：文章管理页，只负责按状态取文章（分页）和审核/删除，卡片展示交给 ArticleReviewCard。 -->
<template>
  <div>
    <PageHeader title="文章管理" />

    <div class="tabs">
      <button :class="{ active: status === 'pending' }" @click="setStatus('pending')">待审核</button>
      <button :class="{ active: status === 'approved' }" @click="setStatus('approved')">已发布</button>
      <button :class="{ active: status === 'rejected' }" @click="setStatus('rejected')">未通过</button>
      <button :class="{ active: status === '' }" @click="setStatus('')">全部</button>
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

    <p v-if="articles.length === 0" class="hint">没有符合条件的文章</p>
    <ArticleReviewCard
      v-for="article in articles"
      :key="article.id"
      :article="article"
      @review="review"
      @remove="removeArticle"
    />

    <LoadMore :total="total" :loaded="articles.length" @load="loadMore" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import ArticleReviewCard from '@/components/admin/ArticleReviewCard.vue'
import LoadMore from '@/components/common/LoadMore.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import request from '@/utils/request'

const PAGE_SIZE = 20

const articles = ref([])
const total = ref(0)
const page = ref(1)
const status = ref('pending')
const errorMsg = ref('')

async function fetchArticles({ append = false } = {}) {
  errorMsg.value = ''
  try {
    const params = { page: page.value, size: PAGE_SIZE }
    if (status.value) params.status = status.value
    const data = await request.get('/articles/', { params })
    articles.value = append ? [...articles.value, ...data.items] : data.items
    total.value = data.total
  } catch (error) {
    errorMsg.value = error.message
  }
}

function setStatus(next) {
  status.value = next
  page.value = 1
  fetchArticles()
}

function loadMore() {
  page.value += 1
  fetchArticles({ append: true })
}

async function review(id, action) {
  try {
    // 后端提供 /articles/review/{id}?action= 这个入口
    await request.post(`/articles/review/${id}`, null, { params: { action } })
    fetchArticles()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function removeArticle(id) {
  if (!window.confirm('确定永久删除该文章？')) return
  try {
    await request.delete(`/articles/admin/${id}`)
    fetchArticles()
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(() => fetchArticles())
</script>

<style scoped>
.tabs { display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; }
.tabs button { padding: 8px 18px; border-radius: 20px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; font-size: 13px; }
.tabs button.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.hint { color: var(--text-secondary); padding: 30px 0; text-align: center; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
</style>
