<!-- SideLists：个人中心侧边卡片零件，自己拉取「最近文件」和「收藏文章」两份数据。 -->
<template>
  <div class="grid">
    <div class="card">
      <h3>📁 最近文件</h3>
      <p v-if="recentFiles.length === 0" class="muted">暂无文件</p>
      <ul v-else>
        <li v-for="file in recentFiles" :key="file.id">
          <router-link :to="{ name: 'file-preview', params: { id: file.id } }">
            {{ file.name }}
          </router-link>
          <small>{{ formatSize(file.size) }}</small>
        </li>
      </ul>
    </div>

    <div class="card">
      <h3>⭐ 收藏文章</h3>
      <p v-if="bookmarks.length === 0" class="muted">暂无收藏</p>
      <ul v-else>
        <li v-for="article in bookmarks" :key="article.id">
          <router-link :to="{ name: 'article-detail', params: { id: article.id } }">
            {{ article.title }}
          </router-link>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import { formatSize } from '@/utils/format'
import request from '@/utils/request'

const recentFiles = ref([])
const bookmarks = ref([])

async function loadSidebarData() {
  try {
    const files = await request.get('/files/recent', { params: { limit: 5 } })
    recentFiles.value = files || []
  } catch {
    recentFiles.value = []
  }
  try {
    const data = await request.get('/articles/bookmarks/mine', { params: { size: 5 } })
    bookmarks.value = data.items || []
  } catch {
    bookmarks.value = []
  }
}

onMounted(loadSidebarData)
</script>

<style scoped>
.card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.muted { color: var(--text-secondary); font-size: 13px; }
ul { list-style: none; padding: 0; margin-top: 8px; }
li { padding: 6px 0; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; gap: 10px; }
li:last-child { border-bottom: none; }
li a { color: var(--primary); }
li small { color: var(--text-tertiary); }
</style>
