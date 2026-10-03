<!-- 文章正文零件：把 Markdown 渲染成 HTML，v-html 之前必须经过 DOMPurify 消毒。 -->
<template>
  <div class="article-content" v-html="renderedContent"></div>
</template>

<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed } from 'vue'

const props = defineProps({
  content: { type: String, default: '' },
})

// 正文经过 DOMPurify 消毒后再渲染，避免存储型 XSS
const renderedContent = computed(() =>
  DOMPurify.sanitize(marked.parse(props.content || '', { async: false })),
)
</script>

<style scoped>
.article-content { line-height: 1.85; font-size: 15px; }
.article-content :deep(img) { max-width: 100%; }
.article-content :deep(pre) { background: var(--bg-tertiary); padding: 12px; border-radius: 8px; overflow-x: auto; }
.article-content :deep(blockquote) { border-left: 3px solid var(--border); margin-left: 0; padding-left: 14px; color: var(--text-secondary); }
.article-content :deep(table) { border-collapse: collapse; width: 100%; }
.article-content :deep(th), .article-content :deep(td) { border: 1px solid var(--border); padding: 6px 10px; }
</style>
