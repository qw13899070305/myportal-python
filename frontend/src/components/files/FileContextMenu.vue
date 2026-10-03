<!-- FileContextMenu：通用右键菜单零件。只负责「定位 + 展示 + 抛意图」，不含任何业务逻辑。 -->
<template>
  <div
    v-if="visible"
    class="context-backdrop"
    @click="emit('close')"
    @contextmenu.prevent="emit('close')"
  >
    <div class="context-menu" :style="menuStyle" @click.stop>
      <button
        v-for="item in items"
        :key="item.action"
        type="button"
        class="context-item"
        :class="{ danger: item.danger }"
        @click="pick(item)"
      >
        {{ item.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
/**
 * 右键菜单。
 *
 * 用一层透明遮罩来接管「点空白关闭」，避免在 document 上挂全局监听；
 * 菜单会按视口边缘自动收拢，不会跑出屏幕外。
 */
import { computed } from 'vue'

const props = defineProps({
  //: 是否显示
  visible: { type: Boolean, default: false },
  //: 鼠标位置（clientX / clientY）
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  //: 菜单项 [{ action, label, danger? }]
  items: { type: Array, default: () => [] },
  //: 菜单大致尺寸，用于边缘收拢
  width: { type: Number, default: 140 },
  itemHeight: { type: Number, default: 34 },
})

const emit = defineEmits(['select', 'close'])

const menuStyle = computed(() => {
  const maxX = window.innerWidth - props.width - 8
  const maxY = window.innerHeight - props.items.length * props.itemHeight - 8
  return {
    left: `${Math.max(4, Math.min(props.x, maxX))}px`,
    top: `${Math.max(4, Math.min(props.y, maxY))}px`,
  }
})

function pick(item) {
  emit('select', item.action)
  emit('close')
}
</script>

<style scoped>
.context-backdrop { position: fixed; inset: 0; z-index: 900; }
.context-menu { position: fixed; min-width: 130px; padding: 5px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius-sm); box-shadow: var(--shadow); display: flex; flex-direction: column; }
.context-item { text-align: left; padding: 7px 12px; font-size: 13px; border: none; border-radius: 6px; background: none; color: var(--text); cursor: pointer; }
.context-item:hover { background: var(--bg-tertiary); }
.context-item.danger { color: var(--danger); }
</style>
