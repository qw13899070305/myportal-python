<!-- 文章筛选条零件：全部/我的/待审核/内部 切换 + 搜索框，只抛事件不查数据。 -->
<template>
  <div class="filter-bar">
    <button :class="{ active: scope === 'all' }" @click="emit('update:scope', 'all')">全部</button>
    <button v-if="isAuthenticated" :class="{ active: scope === 'mine' }" @click="emit('update:scope', 'mine')">
      我的
    </button>
    <button v-if="isAdmin" :class="{ active: scope === 'pending' }" @click="emit('update:scope', 'pending')">
      待审核
    </button>
    <button v-if="isAdmin" :class="{ active: scope === 'internal' }" @click="emit('update:scope', 'internal')">
      内部
    </button>

    <div class="search-bar">
      <input
        :value="search"
        placeholder="搜索标题或内容..."
        @input="emit('update:search', $event.target.value)"
        @keyup.enter="emit('search')"
      />
      <button type="button" @click="emit('search')">搜索</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  scope: { type: String, default: 'all' },
  search: { type: String, default: '' },
  isAuthenticated: { type: Boolean, default: false },
  isAdmin: { type: Boolean, default: false },
})

const emit = defineEmits(['update:scope', 'update:search', 'search'])
</script>

<style scoped>
.filter-bar { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; align-items: center; }
.filter-bar button { background: var(--bg-secondary); border: 1px solid var(--border); padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 13px; color: var(--text); }
.filter-bar button.active { background: var(--primary); color: white; border-color: var(--primary); }
.search-bar { display: flex; gap: 8px; margin-left: auto; }
.search-bar input { padding: 8px 14px; border: 1px solid var(--border); border-radius: 20px; background: var(--bg-secondary); color: var(--text); width: 220px; }
.search-bar button { padding: 8px 16px; border-radius: 20px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
</style>
