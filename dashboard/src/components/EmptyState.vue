<script setup>
defineProps({
  icon: { type: String, default: 'lucide-inbox' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
    <div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
      <span :class="[icon, 'size-6']" aria-hidden="true" />
    </div>
    <p class="text-base text-ink-gray-7">{{ title }}</p>
    <p v-if="description" class="text-sm text-ink-gray-5">{{ description }}</p>
    <slot />
  </div>
</template>

