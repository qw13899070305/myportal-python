<!-- DataTable：通用表格零件，只按 columns 渲染表头和数据行；单元格可用 cell-<key> 插槽自定义，操作列用 actions 插槽。 -->
<template>
  <div class="data-table" :style="{ '--dt-padding': cellPadding, '--dt-font-size': cellFontSize }">
    <table v-if="rows.length > 0">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" :style="col.width ? { width: col.width } : null">
            {{ col.label }}
          </th>
          <th v-if="$slots.actions">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="row.id ?? index">
          <td v-for="col in columns" :key="col.key" :class="col.class">
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">{{ row[col.key] }}</slot>
          </td>
          <td v-if="$slots.actions">
            <slot name="actions" :row="row"></slot>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="loading" class="hint">加载中...</p>
    <p v-else class="hint">{{ emptyText }}</p>
  </div>
</template>

<script setup>
defineProps({
  // 列定义：[{ key, label, width?, class? }]，class 会加到该列单元格上，方便页面用 :deep() 微调
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂无数据' },
  // 单元格内边距与字号：各页面换成通用表格后仍保持原来的行高
  cellPadding: { type: String, default: '12px' },
  cellFontSize: { type: String, default: '14px' },
})
</script>

<style scoped>
table { width: 100%; border-collapse: collapse; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
th, td { padding: var(--dt-padding); border-bottom: 1px solid var(--border); text-align: left; font-size: var(--dt-font-size); }
th { background: var(--bg-tertiary); color: var(--text-secondary); font-size: 13px; }
.hint { color: var(--text-secondary); padding: 30px 0; text-align: center; }
</style>
