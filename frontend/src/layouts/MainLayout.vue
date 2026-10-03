<!-- MainLayout：应用外壳，只负责组合 侧边栏 / 顶栏 / 移动端导航 三个零件，维护抽屉开关与退出登录。 -->
<template>
  <div class="app-shell">
    <div class="overlay" :class="{ visible: sidebarOpen }" @click="sidebarOpen = false"></div>

    <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />

    <div class="main-panel">
      <AppTopbar @toggle-sidebar="sidebarOpen = !sidebarOpen" @logout="handleLogout" />

      <main class="page-content">
        <router-view />
      </main>
    </div>

    <MobileNav />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppTopbar from '@/components/layout/AppTopbar.vue'
import MobileNav from '@/components/layout/MobileNav.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const sidebarOpen = ref(false)

async function handleLogout() {
  sidebarOpen.value = false
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.app-shell { display: flex; min-height: 100vh; }
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 90; opacity: 0; pointer-events: none; transition: opacity var(--transition); }
.overlay.visible { opacity: 1; pointer-events: auto; }
.main-panel { flex: 1; margin-left: var(--sidebar-width); display: flex; flex-direction: column; min-height: 100vh; }
.page-content { flex: 1; padding: 28px; max-width: 1280px; width: 100%; margin: 0 auto; }

@media (max-width: 768px) {
  .main-panel { margin-left: 0; }
  .page-content { padding: 16px; padding-bottom: 80px; }
}
</style>
