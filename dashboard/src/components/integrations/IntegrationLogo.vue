<script setup>
/**
 * A provider's plate: its real logo where the registry has one, and its letter on its own
 * colour where it does not, so a provider the dashboard has never heard of still renders.
 *
 * The markup handed to `v-html` is composed entirely from `logos.js`'s own string
 * literals; the only server value that reaches it is the label, which is XML-escaped into
 * the accessible name and never into markup of its own.
 */
import { computed } from 'vue'
import { brandFor } from '../../data/integrations'
import { escapeXml } from './logos'

const props = defineProps({
  slug: { type: String, required: true },
  label: { type: String, default: '' },
})

const markup = computed(() => {
  const { plate } = brandFor(props.slug)
  return `<svg viewBox="0 0 112 40" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${escapeXml(props.label)}" focusable="false"><rect width="112" height="40" rx="8" fill="${plate.background}" />${plate.svg}</svg>`
})
</script>

<template>
  <div
    class="h-9 w-24 shrink-0 overflow-hidden rounded-5 border border-outline-gray-2"
    v-html="markup"
  />
</template>
