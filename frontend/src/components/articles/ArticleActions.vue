<!-- 文章操作零件：点赞/收藏/下架/通过/拒绝/删除按钮组，只抛事件，接口由页面调用。 -->
<template>
  <div class="actions">
    <button type="button" @click="emit('like')">
      {{ article.is_liked ? '❤️' : '🤍' }} {{ article.likes_count }}
    </button>
    <button type="button" @click="emit('bookmark')">
      {{ article.is_bookmarked ? '⭐' : '☆' }} 收藏
    </button>
    <button v-if="canManage" type="button" @click="emit('withdraw')">下架</button>
    <button v-if="isAdmin" type="button" class="approve" @click="emit('review', 'approve')">通过</button>
    <button v-if="isAdmin" type="button" class="reject" @click="emit('review', 'reject')">拒绝</button>
    <button v-if="canManage" type="button" class="danger" @click="emit('remove')">删除</button>
  </div>
</template>

<script setup>
defineProps({
  article: { type: Object, required: true },
  canManage: { type: Boolean, default: false },
  isAdmin: { type: Boolean, default: false },
})

const emit = defineEmits(['like', 'bookmark', 'withdraw', 'review', 'remove'])
</script>

<style scoped>
.actions { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
.actions button { padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
.actions button.approve { background: var(--success); color: #fff; border-color: var(--success); }
.actions button.reject, .actions button.danger { color: var(--danger); }
</style>
