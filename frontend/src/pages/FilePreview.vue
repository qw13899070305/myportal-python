<!--
  兼容入口：转发到 pages/files/FilePreview.vue。

  真正的实现会通过 ?token= 传递访问令牌，
  因为 iframe 无法自定义 Authorization 请求头。
-->
<script setup>
import FilePreview from './files/FilePreview.vue'
</script>

<template>
  <FilePreview />
</template>
