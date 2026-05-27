<template>
  <button @click="theme.toggle()" class="theme-toggle">
    {{ theme.dark ? '🌙' : '☀️' }}
  </button>
</template>

<script setup>
import { useThemeStore } from '@/stores/theme'
const theme = useThemeStore()
</script>