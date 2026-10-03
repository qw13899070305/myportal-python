import path from 'path'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

/**
 * 后端地址。默认 localhost（兼容 IPv4/IPv6），
 * 需要指向别的机器时用环境变量覆盖：
 *   VITE_BACKEND_ORIGIN=http://192.168.1.2:8000 npm run dev
 */
const BACKEND = process.env.VITE_BACKEND_ORIGIN || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    // 关键：默认 Vite 只监听 localhost，内网（手机 / 别的电脑）根本连不上，
    // 而且不会在终端打印 Network 地址。
    // '::' = 双栈监听，IPv4 与 IPv6 都能访问（Linux bindv6only=0 时通吃）。
    host: '::',
    port: 5173,
    // 端口被占用时自动换一个，启动日志里会打印实际端口
    strictPort: false,
    proxy: {
      // 后端 API 与实时通信都在 /api 下：
      // - REST:      /api/v1/...
      // - WebSocket: /api/v1/chat/ws
      // - socket.io: /ws/socket.io
      // 因此这里必须开启 ws: true，否则 WebSocket 握手会失败。
      '/api': {
        target: BACKEND,
        changeOrigin: true,
        ws: true,
      },
      '/ws': {
        target: BACKEND,
        changeOrigin: true,
        ws: true,
      },
    },
  },
  // vite preview（预览已构建产物）同样要能被内网访问
  preview: {
    host: '::',
    port: 4173,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
})
