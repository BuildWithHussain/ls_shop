<script setup>
defineProps({
  stats: { type: Array, required: true },
  compare: { type: Boolean, default: false },
})
</script>

<template>
  <div class="grid grid-cols-2 rounded-5 border border-outline-gray-1 sm:grid-cols-4 sm:divide-x sm:divide-outline-gray-2">
    <div v-for="stat in stats" :key="stat.label" class="px-4 py-3.5">
      <p class="text-sm text-ink-gray-5">{{ stat.label }}</p>
      <p class="mt-1 text-2xl text-ink-gray-9 tabular-nums">{{ stat.value }}</p>
      <p
        v-if="compare && stat.delta"
        class="mt-1 text-sm"
        :class="stat.up ? 'text-ink-green-6' : 'text-ink-red-6'"
      >
        {{ stat.delta }} vs. previous period
      </p>
      <p v-else class="mt-1 text-sm text-ink-gray-4">&nbsp;</p>
    </div>
  </div>
</template>
