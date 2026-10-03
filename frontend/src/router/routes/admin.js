/**
 * 后台路由：/admin 及其全部子页面。
 *
 * path 用的是相对路径 'admin'，也就是说本文件是「主布局的子路由」，
 * 必须由 routes/index.js 挂到 '/' 之下才会变成 /admin
 * （AdminLayout 要渲染在 MainLayout 里面，所以这里保持拆分前的写法）。
 */
export default [
  {
    path: 'admin',
    name: 'admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', redirect: { name: 'admin-dashboard' } },
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('@/pages/admin/Dashboard.vue'),
        meta: { title: '管理仪表盘' },
      },
      {
        path: 'articles',
        name: 'admin-articles',
        component: () => import('@/pages/admin/ArticlesManage.vue'),
        meta: { title: '文章管理' },
      },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('@/pages/admin/UsersManage.vue'),
        meta: { title: '用户管理' },
      },
      {
        path: 'files',
        name: 'admin-files',
        component: () => import('@/pages/admin/FilesManage.vue'),
        meta: { title: '文件管理' },
      },
      {
        path: 'trash',
        name: 'admin-trash',
        component: () => import('@/pages/admin/TrashManage.vue'),
        meta: { title: '回收站' },
      },
      {
        path: 'chat',
        name: 'admin-chat',
        component: () => import('@/pages/admin/ChatManage.vue'),
        meta: { title: '聊天管理' },
      },
      {
        path: 'audit',
        name: 'admin-audit',
        component: () => import('@/pages/admin/AuditLog.vue'),
        meta: { title: '审计日志' },
      },
      {
        path: 'config',
        name: 'admin-config',
        component: () => import('@/pages/admin/SiteConfig.vue'),
        meta: { title: '站点配置' },
      },
    ],
  },
]
