<!-- FileSearchBar：搜索栏零件，v-model 绑定关键字，回车或点按钮时发出 search 由父组件拉取数据。 -->
<template>
  <div class="search-bar">
    <input
      :value="modelValue"
      placeholder="搜索文件..."
      @input="emit('update:modelValue', $event.target.value)"
      @keyup.enter="emit('search')"
    />
    <button type="button" @click="emit('search')">搜索</button>
  </div>
</template>

<script setup>
defineProps({
  //: 搜索关键字（配合 v-model 使用）
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'search'])
</script>

<style scoped>
.search-bar { display: flex; gap: 8px; }
.search-bar input { padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-secondary); color: var(--text); width: 240px; }
.search-bar button { padding: 10px 16px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-secondary); color: var(--text); cursor: pointer; }
</style>
