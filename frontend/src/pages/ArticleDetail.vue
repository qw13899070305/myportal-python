<!--
  兼容入口：转发到 pages/articles/ArticleDetail.vue。

  旧实现用 ``v-html="marked(content)"`` 直接渲染 Markdown，存在存储型 XSS；
  真正的实现里已经用 DOMPurify 消毒，因此这里统一转发过去。
-->
<script setup>
import ArticleDetail from './articles/ArticleDetail.vue'
</script>

<template>
  <ArticleDetail />
</template>
