<!-- MobileNav：移动端底部导航零件，只在窄屏显示，纯链接无逻辑。 -->
<template>
  <nav class="mobile-nav">
    <router-link to="/" class="mob-link"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></router-link>
    <router-link to="/files" class="mob-link"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg></router-link>
    <router-link to="/articles" class="mob-link"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></router-link>
    <router-link to="/chat" class="mob-link"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg></router-link>
  </nav>
</template>

<style scoped>
.mobile-nav { display: none; position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg-secondary); border-top: 1px solid var(--border); z-index: 100; justify-content: space-around; padding: 8px 0; backdrop-filter: blur(20px); }
.mob-link { padding: 8px 16px; border-radius: var(--radius-sm); color: var(--text-tertiary); transition: all var(--transition); }
.mob-link.router-link-active { color: var(--primary); }

@media (max-width: 768px) {
  .mobile-nav { display: flex; }
}
</style>
