<!-- CategoryManager：文章分类卡片零件，自己增删查 /categories/ 接口，上层的站点配置页不用管分类。 -->
<template>
  <div class="card">
    <h3>文章分类</h3>
    <p class="muted">分类与标签不同：分类是唯一的固定归类。</p>

    <ul class="cat-list" v-if="categories.length > 0">
      <li v-for="cat in categories" :key="cat.id">
        <span>{{ cat.name }}</span>
        <button type="button" class="link-danger" @click="removeCategory(cat)">删除</button>
      </li>
    </ul>
    <p v-else class="muted">还没有分类</p>

    <form class="cat-form" @submit.prevent="addCategory">
      <input v-model.trim="newCategory" placeholder="新分类名称" maxlength="50" />
      <button type="submit" :disabled="!newCategory">添加</button>
    </form>
    <p v-if="categoryMsg" class="success-msg">{{ categoryMsg }}</p>
    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import request from '@/utils/request'

const categories = ref([])
const newCategory = ref('')
const categoryMsg = ref('')
const errorMsg = ref('')

async function loadCategories() {
  try {
    categories.value = await request.get('/categories/')
  } catch {
    categories.value = []
  }
}

async function addCategory() {
  categoryMsg.value = ''
  errorMsg.value = ''
  try {
    await request.post('/categories/', { name: newCategory.value })
    categoryMsg.value = `已添加分类「${newCategory.value}」`
    newCategory.value = ''
    loadCategories()
  } catch (error) {
    errorMsg.value = error.message
  }
}

async function removeCategory(cat) {
  if (!window.confirm(`确定删除分类「${cat.name}」？`)) return
  try {
    await request.delete(`/categories/${cat.id}`)
    loadCategories()
  } catch (error) {
    errorMsg.value = error.message
  }
}

onMounted(loadCategories)
</script>

<style scoped>
h3 { margin-bottom: 14px; font-size: 16px; }
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
input, textarea { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 15px; }
button { background: var(--primary); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; }
button:disabled { opacity: 0.6; cursor: not-allowed; }
.muted { color: var(--text-secondary); font-size: 13px; margin-bottom: 12px; }
.cat-list { list-style: none; padding: 0; margin: 0 0 14px; }
.cat-list li { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); }
.link-danger { background: none; color: var(--danger); padding: 0; font-weight: 400; font-size: 13px; }
.cat-form { display: flex; gap: 10px; }
.cat-form input { flex: 1; }
.success-msg { margin-top: 12px; color: var(--success); font-size: 14px; }
.error-msg { margin-top: 12px; color: var(--danger); font-size: 14px; }
</style>
