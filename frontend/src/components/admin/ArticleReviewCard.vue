<!-- ArticleReviewCard：单条待审文章卡片零件，只展示标题/作者/时间/状态，把通过、拒绝、删除抛给父组件。 -->
<template>
  <div class="card">
    <div class="info">
      <strong>{{ article.title }}</strong>
      <span class="meta">
        作者：{{ article.author }} · {{ formatDateTime(article.created_at) }}
        <span :class="['tag', article.status]">{{ statusLabel(article.status) }}</span>
      </span>
    </div>
    <div class="actions">
      <router-link :to="{ name: 'article-detail', params: { id: article.id } }" class="btn">查看</router-link>
      <button type="button" class="approve" @click="emit('review', article.id, 'approve')">通过</button>
      <button type="button" class="reject" @click="emit('review', article.id, 'reject')">拒绝</button>
      <button type="button" class="delete" @click="emit('remove', article.id)">删除</button>
    </div>
  </div>
</template>

<script setup>
import { formatDateTime } from '@/utils/format'

// 状态值到中文标签的映射
const STATUS_LABELS = { pending: '待审核', approved: '已发布', rejected: '未通过' }

defineProps({
  // 要展示的文章对象
  article: { type: Object, required: true },
})

const emit = defineEmits(['review', 'remove'])

function statusLabel(value) {
  return STATUS_LABELS[value] || value
}
</script>

<style scoped>
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.info { display: flex; flex-direction: column; gap: 4px; }
.meta { font-size: 12px; color: var(--text-tertiary); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tag { padding: 1px 8px; border-radius: 8px; font-size: 11px; background: var(--bg-tertiary); }
.tag.approved { background: var(--success-light); color: var(--success); }
.tag.pending { background: var(--warning-light); color: var(--warning); }
.tag.rejected { background: var(--danger-light); color: var(--danger); }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.actions button, .actions .btn { padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-tertiary); color: var(--text); cursor: pointer; font-size: 13px; text-decoration: none; }
.actions .approve { background: var(--success); color: #fff; border-color: var(--success); }
.actions .reject, .actions .delete { color: var(--danger); }
</style>
