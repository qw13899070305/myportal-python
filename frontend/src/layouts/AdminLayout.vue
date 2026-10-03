<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <h3>管理后台</h3>
      <router-link :to="{ name: 'admin-dashboard' }">📊 仪表盘</router-link>
      <router-link :to="{ name: 'admin-articles' }">📝 文章管理</router-link>
      <router-link :to="{ name: 'admin-users' }">👥 用户管理</router-link>
      <router-link :to="{ name: 'admin-files' }">📁 文件管理</router-link>
      <router-link :to="{ name: 'admin-trash' }">🗑️ 回收站</router-link>
      <router-link :to="{ name: 'admin-chat' }">💬 聊天管理</router-link>
      <router-link :to="{ name: 'admin-audit' }">🧾 审计日志</router-link>
      <router-link :to="{ name: 'admin-config' }">⚙️ 站点配置</router-link>
    </aside>
    <main class="admin-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.admin-layout { display: flex; min-height: calc(100vh - var(--header-height) - 48px); gap: 20px; }
.admin-sidebar { width: 200px; flex-shrink: 0; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; display: flex; flex-direction: column; gap: 4px; height: fit-content; }
.admin-sidebar h3 { margin-bottom: 12px; font-size: 16px; }
.admin-sidebar a { padding: 9px 12px; border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 14px; }
.admin-sidebar a:hover { background: var(--bg-tertiary); color: var(--text); }
.admin-sidebar a.router-link-active { background: var(--primary); color: #fff; }
.admin-content { flex: 1; min-width: 0; }
@media (max-width: 900px) {
  .admin-layout { flex-direction: column; }
  .admin-sidebar { width: 100%; flex-direction: row; flex-wrap: wrap; }
  .admin-sidebar h3 { width: 100%; }
}
</style>
