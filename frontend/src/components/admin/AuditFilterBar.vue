<!-- AuditFilterBar：审计日志筛选条零件，自己保存两个输入框，只把筛选条件抛给父组件去查数据。 -->
<template>
  <Toolbar wrap input-width="200px">
    <input v-model="action" placeholder="按动作筛选，如 login" @keyup.enter="submit" />
    <input v-model="userId" type="number" placeholder="用户 ID" @keyup.enter="submit" />
    <button type="button" @click="submit">筛选</button>
    <button type="button" @click="reset">重置</button>
  </Toolbar>
</template>

<script setup>
import { ref } from 'vue'

import Toolbar from '@/components/common/Toolbar.vue'

const action = ref('')
const userId = ref('')

const emit = defineEmits(['filter', 'reset'])

// 把当前输入值交给父组件
function submit() {
  emit('filter', { action: action.value, userId: userId.value })
}

// 清空自己的输入框，并通知父组件清掉筛选条件后重查
function reset() {
  action.value = ''
  userId.value = ''
  emit('reset')
}
</script>
