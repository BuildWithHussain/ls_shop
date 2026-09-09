<script setup>
import { Alert } from 'frappe-ui'

// A lead line plus the explanation: Alert's banner layout wraps, its row
// layout truncates, so the long half always goes in `description`.
defineProps({
  title: { type: String, required: true },
  text: { type: String, required: true },
  icon: { type: String, default: 'lucide-lightbulb' },
  theme: { type: String, default: 'gray' },
})
</script>

<template>
  <Alert :title="title" :description="text" :icon="icon" :theme="theme" />
</template>
