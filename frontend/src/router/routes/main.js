/**
 * 主布局（MainLayout）下的前台页面路由。
 *
 * 只包含需要主布局外壳的页面；后台路由由 ./admin.js 提供，
 * 在 routes/index.js 里并回本路由的 children（保持原有嵌套层级）。
 */
export default [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/pages/Dashboard.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'files',
        name: 'files',
        component: () => import('@/pages/files/FileList.vue'),
        meta: { requiresAuth: true, title: '文件' },
      },
      {
        path: 'files/:id',
        name: 'file-preview',
        component: () => import('@/pages/files/FilePreview.vue'),
        meta: { requiresAuth: true, title: '文件预览' },
      },
      {
        path: 'articles',
        name: 'articles',
        component: () => import('@/pages/articles/ArticleList.vue'),
        meta: { title: '文章' },
      },
      {
        path: 'articles/new',
        name: 'article-new',
        component: () => import('@/pages/articles/ArticleEditor.vue'),
        meta: { requiresAuth: true, title: '写文章' },
      },
      {
        path: 'articles/:id',
        name: 'article-detail',
        component: () => import('@/pages/articles/ArticleDetail.vue'),
        meta: { title: '文章详情' },
      },
      {
        path: 'chat',
        name: 'chat',
        component: () => import('@/pages/chat/Chat.vue'),
        meta: { requiresAuth: true, title: '聊天' },
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@/pages/profile/Profile.vue'),
        meta: { requiresAuth: true, title: '个人中心' },
      },
    ],
  },
]
