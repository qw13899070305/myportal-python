<!-- frontend/src/pages/articles/ArticleDetail.vue -->
<template>
  <div class="article-detail">
    <button @click="$router.back()" class="back-btn">← 返回列表</button>

    <h1>{{ article.title }}</h1>

    <div class="article-meta">
      <span>作者：{{ article.author }}</span>
      <span>{{ new Date(article.created_at).toLocaleDateString() }}</span>
      <span v-if="article.is_pinned" class="badge pin">置顶</span>
      <span v-if="article.is_internal" class="badge internal">内部</span>
    </div>

    <div class="tags">
      <span v-for="tag in article.tags" :key="tag" class="tag">{{ tag }}</span>
    </div>

    <div class="actions">
      <button @click="toggleLike">
        {{ article.is_liked ? '❤️' : '' }} {{ article.likes_count }}
      </button>
      <button @click="toggleBookmark">
        {{ article.is_bookmarked ? '⭐' : '☆' }} 收藏
      </button>
      <button v-if="canManage" @click="unpublish" class="danger">下架文章</button>
    </div>

    <!-- ✅ 修复：使用 sanitizedContent 代替直接 v-html -->
    <div class="article-content" v-html="sanitizedContent"></div>

    <hr />

    <h3>评论 ({{ article.comments_count }})</h3>

    <div class="comment-form">
      <textarea v-model="newComment" placeholder="写下你的评论..."></textarea>
      <button @click="submitComment">发表评论</button>
    </div>

    <div v-if="comments.length === 0" class="no-comments">暂无评论</div>

    <div v-for="c in comments" :key="c.id" class="comment">
      <strong>{{ c.user?.username || '用户' }}</strong>
      <small>{{ new Date(c.created_at).toLocaleString() }}</small>
      <p>{{ c.content }}</p>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import DOMPurify from 'dompurify'

const route = useRoute()
const article = ref({})
const comments = ref([])
const loading = ref(false)
const newComment = ref('')

// 消毒后的 HTML 内容，防止 XSS
const sanitizedContent = computed(() => {
  return DOMPurify.sanitize(article.value.content || '')
})

onMounted(async () => {
  const id = route.params.id
  const response = await api.get(`/articles/${id}`)
  article.value = response.data
})
</script>