<!--
  兼容入口：转发到 pages/articles/ArticleList.vue。
  保留本文件是为了让早期的 ``import Articles from '@/pages/Articles.vue'`` 依然可用。
-->
<script setup>
import ArticleList from './articles/ArticleList.vue'
</script>

<template>
  <ArticleList />
</template>
