<!-- 评论区零件：评论列表 + 发表评论表单；自己提交评论，成功后通知页面刷新。 -->
<template>
  <div class="comment-form" v-if="canComment">
    <textarea v-model="newComment" placeholder="写下你的评论..."></textarea>
    <button type="button" :disabled="submitting" @click="submitComment">发表评论</button>
  </div>
  <p v-else class="hint">
    <router-link :to="{ name: 'login' }">登录</router-link> 后可以评论。
  </p>

  <p v-if="comments.length === 0" class="hint">暂无评论</p>
  <div v-for="comment in comments" :key="comment.id" class="comment">
    <strong>{{ comment.username }}</strong>
    <small>{{ formatDateTime(comment.created_at) }}</small>
    <p>{{ comment.content }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import { formatDateTime } from '@/utils/format'
import request from '@/utils/request'

const props = defineProps({
  articleId: { type: [String, Number], required: true },
  comments: { type: Array, default: () => [] },
  canComment: { type: Boolean, default: false },
})

const emit = defineEmits(['submitted', 'error'])

const newComment = ref('')
const submitting = ref(false)

async function submitComment() {
  if (!newComment.value.trim()) return
  submitting.value = true
  try {
    await request.post(`/articles/${props.articleId}/comments`, {
      content: newComment.value.trim(),
    })
    newComment.value = ''
    emit('submitted')
  } catch (error) {
    // 错误交给页面统一提示，输入框内容保留，方便用户重试
    emit('error', error.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.comment-form { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.comment-form textarea { min-height: 90px; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-secondary); color: var(--text); resize: vertical; }
.comment-form button { align-self: flex-start; padding: 9px 22px; border: none; border-radius: 8px; background: var(--primary); color: #fff; cursor: pointer; }
.comment { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 10px; }
.comment small { color: var(--text-tertiary); margin-left: 10px; }
.comment p { margin-top: 6px; }
.hint { color: var(--text-secondary); padding: 20px 0; }
.hint a { color: var(--primary); }
</style>
