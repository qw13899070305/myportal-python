<template>
  <div class="preview-page">
    <button class="back-btn" @click="$router.back()">← 返回</button>
    <iframe :src="`/api/v1/files/preview/${$route.params.id}`" class="preview-frame"></iframe>
  </div>
</template>

<style scoped>
.preview-page { height: calc(100vh - var(--header-height) - 48px); display: flex; flex-direction: column; }
.back-btn { background: var(--bg-secondary); border: 1px solid var(--border); padding: 8px 16px; border-radius: var(--radius-sm); margin-bottom: 16px; color: var(--text); align-self: flex-start; }
.preview-frame { flex: 1; border: 1px solid var(--border); border-radius: var(--radius); background: white; }
</style>
