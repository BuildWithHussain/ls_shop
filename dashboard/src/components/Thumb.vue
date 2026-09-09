<script setup>
defineProps({
  emoji: { type: String, default: '📦' },
  // Real catalog rows carry an uploaded image URL rather than a mock emoji —
  // optional so every existing emoji-only caller keeps rendering unchanged.
  image: { type: String, default: null },
  size: { type: String, default: 'size-8' },
})
</script>

<template>
  <img
    v-if="image"
    :src="image"
    class="shrink-0 rounded-4 bg-surface-gray-2 object-cover"
    :class="size"
    alt=""
  />
  <div
    v-else
    class="grid shrink-0 place-content-center rounded-4 bg-surface-gray-2 text-ink-gray-7"
    :class="size"
    aria-hidden="true"
  >
    {{ emoji }}
  </div>
</template>
