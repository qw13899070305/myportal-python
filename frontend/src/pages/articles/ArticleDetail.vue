<!--
  文章详情页：只负责取数（文章 + 评论）、调用接口、错误提示，
  展示全部交给 components/articles 下的四个小零件。
-->
<template>
  <div class="page">
    <button type="button" class="back-btn" @click="$router.back()">← 返回列表</button>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    <p v-if="loading" class="hint">加载中...</p>

    <template v-if="article">
      <ArticleHeader :article="article" />

      <ArticleActions
        v-if="auth.isAuthenticated"
        :article="article"
        :can-manage="canManage"
        :is-admin="auth.isAdmin()"
        @like="toggleLike"
        @bookmark="toggleBookmark"
        @withdraw="withdraw"
        @review="review"
        @remove="removeArticle"
      />

      <ArticleBody :content="article.content" />

      <hr />

      <h3>评论 ({{ article.comments_count }})</h3>

      <CommentSection
        :article-id="articleId"
        :comments="comments"
        :can-comment="auth.isAuthenticated"
        @submitted="onCommentSubmitted"
        @error="onCommentError"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ArticleActions from '@/components/articles/ArticleActions.vue'
import ArticleBody from '@/components/articles/ArticleBody.vue'
import ArticleHeader from '@/components/articles/ArticleHeader.vue'
import CommentSection from '@/components/articles/CommentSection.vue'
import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const article = ref(null)
const comments = ref([])
const loading = ref(false)
const errorMsg = ref('')

const articleId = computed(() => route.params.id)

const canManage = computed(() => {
  if (!article.value || !auth.isAuthenticated) return false
  return auth.isAdmin() || article.value.author_id === auth.user?.id
})

async function loadArticle() {
  loading.value = true
  errorMsg.value = ''
  try {
    article.value = await request.get(`/articles/${articleId.value}`)
  } catch (error) {
    errorMsg.value = error.message
    article.value = null
  } finally {
    loading.value = false
  }
}

async function loadComments() {
  try {
    const data = await request.get(`/articles/${articleId.value}/comments`)
    comments.value = data.items || []
  } catch {
    comments.value = []
  }
}

/** 评论提交成功：评论区和文章（评论数）一起刷新。 */
async function onCommentSubmitted() {
  await Promise.all([loadComments(), loadArticle()])
}

/** 评论提交失败：沿用页面顶部的错误提示。 */
function onCommentError(message) {
  errorMsg.value = message
}

async function toggleLike() {
  try {
    const data = await request.post(`/articles/${articleId.value}/like`)
    article.value.is_liked = data.liked
    article.value.likes_count = data.likes_count
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function toggleBookmark() {
  try {
    const data = await request.post(`/articles/${articleId.value}/bookmark`)
    article.value.is_bookmarked = data.bookmarked
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function withdraw() {
  if (!window.confirm('确定下架这篇文章？')) return
  try {
    await request.post(`/articles/${articleId.value}/withdraw`)
    await loadArticle()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function review(action) {
  try {
    article.value = await request.post(`/articles/${articleId.value}/review`, { action })
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function removeArticle() {
  if (!window.confirm('确定删除这篇文章？该操作不可恢复。')) return
  try {
    await request.delete(`/articles/${articleId.value}`)
    router.push({ name: 'articles' })
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(() => {
  loadArticle()
  loadComments()
})

watch(articleId, () => {
  loadArticle()
  loadComments()
})
</script>

<style scoped>
.page { max-width: 860px; margin: 0 auto; }
.back-btn { background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-bottom: 20px; }
hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
.error-msg { color: var(--danger); margin-bottom: 12px; }
.hint { color: var(--text-secondary); padding: 20px 0; }
</style>
