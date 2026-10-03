/**
 * 导航守卫：登录态/权限校验（beforeEach）与页面标题（afterEach）。
 */
export function setupGuards(router) {
  router.beforeEach(async (to) => {
    const { useAuthStore } = await import('@/stores/auth')
    const auth = useAuthStore()

    // 首次导航时尝试用本地令牌恢复会话
    if (!auth.ready) {
      await auth.restore()
    }

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }

    if (to.meta.requiresAdmin && !auth.isAdmin()) {
      return { name: 'dashboard' }
    }

    if (to.meta.guestOnly && auth.isAuthenticated) {
      return { name: 'dashboard' }
    }

    return true
  })

  router.afterEach((to) => {
    document.title = to.meta.title ? `${to.meta.title} · MyPortal` : 'MyPortal'
  })
}

export default setupGuards
