<script setup>
// One place for the page gutters and bottom padding so every screen agrees.
defineProps({ width: { type: String, default: 'full' } })

const WIDTHS = {
  full: '',
  wide: 'mx-auto max-w-[940px]',
  narrow: 'mx-auto max-w-4xl',
  form: 'mx-auto max-w-xl',
}
</script>

<template>
  <div class="px-3 pb-32 pt-5 sm:px-5">
    <div :class="WIDTHS[width]">
      <slot />
    </div>
  </div>
</template>
