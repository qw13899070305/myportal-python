<!--
  兼容入口：页面早期直接放在 pages/ 下，重构后移到了 pages/admin/。
  这里转发到真正的实现，保证仍然引用本文件的地方都能正常工作。
-->
<script setup>
import AdminDashboard from './admin/Dashboard.vue'
</script>

<template>
  <AdminDashboard />
</template>
