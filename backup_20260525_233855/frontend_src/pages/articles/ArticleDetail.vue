<template>
  <div class="page" v-if="article">
    <router-link to="/articles" class="back">← 返回列表</router-link>
    <h1>{{ article.title }}</h1>
    <div class="meta">
      <span>作者：{{ article.author }}</span>
      <span>{{ new Date(article.created_at).toLocaleDateString() }}</span>
      <span v-if="article.is_pinned" class="pinned">📌 置顶</span>
      <span v-if="article.is_internal" class="internal">🔒 内部</span>
    </div>
    <div class="tags" v-if="article.tags?.length">
      <span v-for="tag in article.tags" :key="tag" class="tag">{{ tag }}</span>
    </div>
    <div class="content" v-html="rendered"></div>
    <div class="actions">
      <button @click="toggleLike">{{ article.is_liked ? '❤️' : '🤍' }} {{ article.likes_count }}</button>
      <button @click="toggleBookmark">{{ article.is_bookmarked ? '⭐' : '☆' }} 收藏</button>
      <!-- 作者下架按钮 -->
      <button
        v-if="isAuthor && article.status === 'approved'"
        @click="withdrawArticle"
        class="btn-withdraw"
      >下架文章</button>
    </div>
    <div class="comments-section">
      <h3>评论 ({{ article.comments_count }})</h3>
      <div class="comment-form">
        <textarea v-model="newComment" placeholder="写下你的评论..." rows="3"></textarea>
        <button @click="submitComment" :disabled="!newComment.trim()">发表评论</button>
      </div>
      <div v-if="comments.length === 0" class="no-comments">暂无评论</div>
      <div v-for="c in comments" :key="c.id" class="comment">
        <div class="comment-header">
          <strong>{{ c.user?.username || '用户' }}</strong>
          <span class="comment-time">{{ new Date(c.created_at).toLocaleString() }}</span>
        </div>
        <p class="comment-content">{{ c.content }}</p>
      </div>
    </div>
  </div>
  <div v-else class="loading">加载中...</div>
</template>

<script setup>
import DOMPurify from "dompurify";
import DOMPurify from "dompurify";
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import axios from 'axios'
import { marked } from 'marked'

const route = useRoute()
const auth = useAuthStore()
const article = ref(null)
const comments = ref([])
const newComment = ref('')

const rendered = computed(() => article.value ? marked(article.value.content) : '')
const isAuthor = computed(() => article.value?.author === auth.user?.username)

async function fetchArticle() {
  const res = await axios.get(`/api/v1/articles/${route.params.id}`, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  article.value = res.data
}

async function fetchComments() {
  const res = await axios.get(`/api/v1/articles/${route.params.id}/comments`, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  comments.value = res.data.items || []
}

async function toggleLike() {
  await axios.post(`/api/v1/articles/${article.value.id}/like`, {}, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  fetchArticle()
}

async function toggleBookmark() {
  await axios.post(`/api/v1/articles/${article.value.id}/bookmark`, {}, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  fetchArticle()
}

async function submitComment() {
  if (!newComment.value.trim()) return
  await axios.post(`/api/v1/articles/${article.value.id}/comment`, {
    content: newComment.value
  }, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  newComment.value = ''
  fetchComments()
}

async function withdrawArticle() {
  if (!confirm('确定下架这篇文章？')) return
  await axios.post(`/api/v1/articles/${article.value.id}/withdraw`, {}, {
    headers: { Authorization: `Bearer ${auth.token}` }
  })
  fetchArticle()
}

onMounted(() => { fetchArticle(); fetchComments() })
</script>

<style scoped>
.page { max-width: 800px; margin: 0 auto; }
.back { color: var(--primary); text-decoration: none; font-size: 14px; }
h1 { font-size: 32px; margin: 16px 0 8px; }
.meta { color: var(--text-secondary); font-size: 14px; display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 16px; }
.pinned { color: var(--warning); font-weight: 600; }
.internal { color: var(--danger); }
.tags { display: flex; gap: 8px; margin-bottom: 20px; }
.tag { background: var(--primary-light); color: var(--primary); padding: 4px 12px; border-radius: 20px; font-size: 13px; }
.content { line-height: 1.8; font-size: 16px; margin-bottom: 24px; }
.actions { display: flex; gap: 12px; margin-bottom: 32px; flex-wrap: wrap; }
.actions button { padding: 10px 20px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
.btn-withdraw { background: var(--danger-light); color: var(--danger); border-color: var(--danger) !important; }
.comments-section { border-top: 1px solid var(--border); padding-top: 24px; }
.comments-section h3 { margin-bottom: 16px; }
.comment-form { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.comment-form textarea { padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); resize: vertical; }
.comment-form button { align-self: flex-end; padding: 8px 20px; background: var(--primary); color: white; border: none; border-radius: 8px; cursor: pointer; }
.comment-form button:disabled { opacity: 0.5; cursor: not-allowed; }
.comment { padding: 12px 0; border-bottom: 1px solid var(--border); }
.comment-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
.comment-time { font-size: 12px; color: var(--text-secondary); }
.comment-content { color: var(--text); line-height: 1.6; }
.no-comments { text-align: center; color: var(--text-secondary); padding: 20px 0; }
.loading { text-align: center; padding: 60px 0; color: var(--text-secondary); }
</style>
