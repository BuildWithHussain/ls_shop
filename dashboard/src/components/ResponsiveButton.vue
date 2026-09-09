<script setup>
/**
 * A labelled action on a desktop header, its icon alone on a phone.
 *
 * frappe-ui's Button cannot do this in one element: `isIconButton` keys off the
 * icon props and swaps the whole size scale, so icon-only geometry is only
 * reachable by rendering a second Button. Two of them hand-typed at a call site
 * means the handler and the disabled condition are written twice and can drift,
 * so both copies are declared here once and everything else — @click, :disabled,
 * variant, theme, route — reaches them through $attrs.
 *
 * `label` goes to both copies because frappe-ui maps it to aria-label: it is the
 * accessible name of the icon-only copy, not just its text. Only one copy is ever
 * displayed, so the hidden one is out of the accessibility tree and unclickable.
 */
import { Button } from 'frappe-ui'

defineOptions({ inheritAttrs: false })

defineProps({
  label: { type: String, required: true },
  icon: { type: String, required: true },
  iconPosition: {
    type: String,
    default: 'left',
    validator: (value) => ['left', 'right'].includes(value),
  },
})
</script>

<template>
  <Button
    class="hidden sm:inline-flex"
    :label="label"
    :icon-left="iconPosition === 'left' ? icon : undefined"
    :icon-right="iconPosition === 'right' ? icon : undefined"
    v-bind="$attrs"
  />
  <Button class="sm:hidden" :label="label" :icon="icon" v-bind="$attrs" />
</template>
