/**
 * ESLint 配置（ESLint 8 + eslint-plugin-vue 9，使用传统的 .eslintrc 格式）。
 *
 * 只启用「正确性」相关规则（essential + recommended），
 * 不启用排版类规则，避免和既有代码风格冲突产生上百条无效告警。
 */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
  extends: ['eslint:recommended', 'plugin:vue/vue3-essential'],
  rules: {
    // 组件名允许单个单词（页面文件就是 Login.vue / Chat.vue 这种命名）
    'vue/multi-word-component-names': 'off',
    // 允许下划线开头的未使用参数
    'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
  },
  ignorePatterns: ['dist/', 'node_modules/', 'public/sw.js'],
}
