<!-- AppTopbar：顶栏零件，只负责「菜单按钮 + 语言切换 + 主题切换 + 通知铃 + 退出/登录入口」，自身不碰登录态，退出交给父组件。 -->
<template>
  <header class="topbar">
    <button class="menu-toggle" @click="emit('toggle-sidebar')" aria-label="菜单">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>

    <div class="topbar-actions">
      <select
        class="locale-select"
        :value="locale"
        :title="t('common.language')"
        @change="changeLocale($event.target.value)"
      >
        <option v-for="item in LOCALES" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>

      <ThemeToggle />
      <NotificationBell />

      <button
        v-if="auth.isAuthenticated"
        class="icon-btn logout-btn"
        :title="t('common.logout')"
        @click="emit('logout')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </button>
      <router-link v-else class="btn-login" :to="{ name: 'login' }">{{ t('common.login') }}</router-link>
    </div>
  </header>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

import NotificationBell from '@/components/NotificationBell.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { LOCALES, setLocale } from '@/i18n'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits(['toggle-sidebar', 'logout'])

const auth = useAuthStore()
const { t, locale } = useI18n()

function changeLocale(value) {
  setLocale(value)
}
</script>

<style scoped>
.topbar { height: var(--header-height); background: var(--bg-secondary); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; position: sticky; top: 0; z-index: 50; backdrop-filter: blur(20px); }
.menu-toggle { display: none; background: none; color: var(--text); border: none; cursor: pointer; }
.topbar-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.locale-select { background: var(--bg-tertiary); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 6px 8px; font-size: 13px; cursor: pointer; }
.icon-btn { width: 36px; height: 36px; border-radius: var(--radius-sm); background: transparent; color: var(--text-secondary); display: flex; align-items: center; justify-content: center; transition: all var(--transition); border: none; cursor: pointer; }
.icon-btn:hover { background: var(--bg-tertiary); color: var(--text); }
.logout-btn:hover { background: var(--danger-light); color: var(--danger); }
.btn-login { padding: 7px 16px; border-radius: var(--radius-sm); background: var(--primary); color: #fff; font-size: 14px; text-decoration: none; }

@media (max-width: 768px) {
  .menu-toggle { display: block; }
}
</style>
