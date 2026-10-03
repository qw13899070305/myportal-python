/**
 * 认证区路由：登录、注册，以及兜底的 404 通配路由。
 *
 * 这些页面都在主布局之外（整屏页面），所以单独成组；
 * 404 放在本文件里，汇总时由 routes/index.js 保证它排在最后。
 */
export default [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/Login.vue'),
    meta: { guestOnly: true, title: '登录' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/pages/Register.vue'),
    meta: { guestOnly: true, title: '注册' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFound.vue'),
    meta: { title: '页面不存在' },
  },
]
