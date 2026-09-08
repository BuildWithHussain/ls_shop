<script setup>
import { Badge } from 'frappe-ui'
import { label, statusTheme } from '../data/format'

// `label` overrides format.js's static lookup — the Orders screens' status keys
// (order lifecycle stages, payment states) carry their own server-translated
// text already, so there is no need to duplicate it client-side.
const props = defineProps({
  status: { type: String, required: true },
  label: { type: String, default: null },
})
</script>

<template>
  <Badge :label="props.label ?? label(status)" :theme="statusTheme(status)" variant="subtle" />
</template>
