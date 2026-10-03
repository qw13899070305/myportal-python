<template>
  <div class="not-found">
    <h1>404</h1>
    <h2>{{ t('notFound.title') }}</h2>
    <p>{{ t('notFound.description') }}</p>
    <router-link class="btn" :to="{ name: 'dashboard' }">
      {{ t('notFound.backHome') }}
    </router-link>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.not-found { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; text-align: center; padding: 24px; }
h1 { font-size: 72px; color: var(--primary); margin: 0; }
h2 { margin: 0; }
p { color: var(--text-secondary); }
.btn { margin-top: 16px; padding: 10px 24px; border-radius: var(--radius-sm); background: var(--primary); color: #fff; text-decoration: none; }
</style>
