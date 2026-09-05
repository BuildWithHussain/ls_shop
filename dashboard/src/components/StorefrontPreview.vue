<script setup>
/** A drawn stand-in for the live storefront: enough shape to judge a layout. */
defineProps({
  device: { type: String, default: 'desktop' },
  highlight: { type: String, default: 'body' },
})

const ring = (part, highlight) =>
  part === highlight ? 'outline outline-2 outline-outline-blue-3' : ''
</script>

<template>
  <div class="rounded-5 border border-outline-gray-1 bg-surface-gray-1 p-4">
    <div
      class="mx-auto overflow-hidden rounded-4 border border-outline-gray-2 bg-surface-base"
      :class="device === 'mobile' ? 'w-[22rem] max-w-full' : 'w-full'"
    >
      <div
        class="flex items-center gap-2 border-b border-outline-gray-1 px-3 py-2"
        :class="ring('header', highlight)"
      >
        <span class="text-base-semibold text-ink-gray-8">Kirana &amp; Co</span>
        <div class="ml-4 hidden gap-3 sm:flex" :class="ring('nav', highlight)">
          <span v-for="item in ['Shop', 'Books', 'Apparel', 'About']" :key="item" class="text-sm text-ink-gray-6">
            {{ item }}
          </span>
        </div>
        <div class="ml-auto flex gap-2 text-ink-gray-5">
          <span class="lucide-search size-4" aria-hidden="true" />
          <span class="lucide-shopping-bag size-4" aria-hidden="true" />
        </div>
      </div>

      <div class="space-y-3 p-3">
        <div class="grid h-28 place-items-center rounded-4 bg-surface-gray-2 text-sm text-ink-gray-5">
          Hero banner
        </div>
        <div class="grid gap-3" :class="device === 'mobile' ? 'grid-cols-2' : 'grid-cols-4'">
          <div v-for="n in 4" :key="n" class="space-y-1.5">
            <div class="aspect-square rounded-4 bg-surface-gray-2" />
            <div class="h-2 w-3/4 rounded-1 bg-surface-gray-3" />
            <div class="h-2 w-1/3 rounded-1 bg-surface-gray-2" />
          </div>
        </div>
      </div>

      <div
        class="grid grid-cols-3 gap-3 border-t border-outline-gray-1 p-3"
        :class="ring('footer', highlight)"
      >
        <div v-for="n in 3" :key="n" class="space-y-1.5">
          <div class="h-2 w-1/2 rounded-1 bg-surface-gray-3" />
          <div v-for="m in 3" :key="m" class="h-2 w-2/3 rounded-1 bg-surface-gray-2" />
        </div>
      </div>
    </div>
  </div>
</template>
