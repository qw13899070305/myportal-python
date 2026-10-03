<!-- 文章卡片零件：只渲染单篇文章的标题、徽章、元信息、摘要和标签。 -->
<template>
  <div class="article-card">
    <router-link :to="{ name: 'article-detail', params: { id: article.id } }" class="article-title">
      <span v-if="article.is_pinned" class="pin-badge">📌</span>
      <span v-if="article.is_internal" class="internal-badge">🔒</span>
      {{ article.title }}
    </router-link>

    <div class="article-meta">
      <span>作者：{{ article.author }}</span>
      <span>👍 {{ article.likes_count }} · 💬 {{ article.comments_count }}</span>
      <span>{{ formatDate(article.created_at) }}</span>
      <span v-if="article.status !== 'approved'" class="status">{{ statusLabel(article.status) }}</span>
    </div>

    <p class="summary">{{ article.summary }}</p>

    <div class="article-tags" v-if="article.tags?.length">
      <span v-for="tag in article.tags" :key="tag" class="mini-tag">{{ tag }}</span>
    </div>
  </div>
</template>

<script setup>
import { formatDate } from '@/utils/format'

defineProps({
  article: { type: Object, required: true },
})

const STATUS_LABELS = { pending: '待审核', approved: '已发布', rejected: '未通过' }

/** 后端英文状态码转中文标签。 */
function statusLabel(status) {
  return STATUS_LABELS[status] || status
}
</script>

<style scoped>
.article-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.article-card:hover { box-shadow: var(--shadow); }
.article-title { font-size: 18px; font-weight: 600; color: var(--text); text-decoration: none; }
.pin-badge { margin-right: 4px; }
.internal-badge { margin-right: 4px; }
.article-meta { display: flex; gap: 18px; margin-top: 8px; font-size: 13px; color: var(--text-secondary); flex-wrap: wrap; }
.status { color: var(--warning); }
.summary { margin-top: 10px; color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
.article-tags { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.mini-tag { background: var(--primary-light); color: var(--primary); padding: 2px 10px; border-radius: 12px; font-size: 12px; }
</style>
