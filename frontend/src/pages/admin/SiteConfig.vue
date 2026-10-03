<!-- SiteConfig：站点配置页，只负责读一次 /admin/config，再把基础信息表单和分类管理两块零件拼起来。 -->
<template>
  <div>
    <h2>站点配置</h2>

    <p v-if="loading">加载中...</p>

    <template v-else>
      <SiteBasicForm :config="config" :error="errorMsg" @saved="onSaved" />
      <CategoryManager />
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import CategoryManager from '@/components/admin/CategoryManager.vue'
import SiteBasicForm from '@/components/admin/SiteBasicForm.vue'
import request from '@/utils/request'

const config = ref({})
const loading = ref(true)
const errorMsg = ref('')

async function loadConfig() {
  try {
    config.value = await request.get('/admin/config')
    errorMsg.value = ''
  } catch (error) {
    errorMsg.value = error.message
  } finally {
    loading.value = false
  }
}

// 保存成功后用后端返回的最新配置刷新表单数据源（PUT 会返回完整配置）
function onSaved(data) {
  config.value = data
  errorMsg.value = ''
}

onMounted(loadConfig)
</script>

<style scoped>
h2 { margin-bottom: 20px; }
</style>
