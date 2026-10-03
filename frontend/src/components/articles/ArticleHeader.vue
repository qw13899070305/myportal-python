<!-- 文章头部零件：只负责展示标题、元信息（作者/时间/置顶/内部/状态徽章）和标签。 -->
<template>
  <h1>{{ article.title }}</h1>

  <div class="article-meta">
    <span>作者：{{ article.author }}</span>
    <span>{{ formatDateTime(article.created_at) }}</span>
    <span v-if="article.is_pinned" class="badge">置顶</span>
    <span v-if="article.is_internal" class="badge">内部</span>
    <span v-if="article.status !== 'approved'" class="badge warning">
      {{ statusLabel(article.status) }}
    </span>
  </div>

  <div class="tags" v-if="article.tags?.length">
    <span v-for="tag in article.tags" :key="tag" class="tag">{{ tag }}</span>
  </div>
</template>

<script setup>
import { formatDateTime } from '@/utils/format'

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
h1 { font-size: 28px; margin-bottom: 12px; }
.article-meta { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
.badge { background: var(--bg-tertiary); padding: 2px 8px; border-radius: 6px; }
.badge.warning { background: var(--warning-light); color: var(--warning); }
.tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.tag { background: var(--primary-light); color: var(--primary); padding: 2px 10px; border-radius: 12px; font-size: 12px; }
</style>
