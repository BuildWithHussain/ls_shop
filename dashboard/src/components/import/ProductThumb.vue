<script setup>
import { computed } from 'vue'

const props = defineProps({
  seed: { type: String, default: '' },
  icon: { type: String, default: 'lucide-shirt' },
  size: { type: String, default: 'size-10' },
  iconSize: { type: String, default: 'size-4' },
  empty: { type: Boolean, default: false },
})

// Stand-in for a real product photo: a deterministic gradient per SKU.
const hue = computed(() => {
  let h = 0
  for (const ch of props.seed) h = (h * 31 + ch.charCodeAt(0)) % 360
  return h
})

const style = computed(() => ({
  background: `linear-gradient(135deg, hsl(${hue.value} 42% 82%), hsl(${(hue.value + 40) % 360} 38% 66%))`,
}))
</script>

<template>
  <div
    v-if="empty"
    class="flex shrink-0 items-center justify-center rounded-4 border border-dashed border-outline-gray-2 bg-surface-gray-1 text-ink-gray-4"
    :class="size"
  >
    <span class="lucide-image-off" :class="iconSize" aria-hidden="true" />
  </div>
  <div
    v-else
    class="flex shrink-0 items-center justify-center overflow-hidden rounded-4 border border-outline-gray-1"
    :class="size"
    :style="style"
  >
    <span class="text-white/85" :class="[icon, iconSize]" aria-hidden="true" />
  </div>
</template>
