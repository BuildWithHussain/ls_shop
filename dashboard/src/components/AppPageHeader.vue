<script setup>
import { Breadcrumbs, PageHeader } from 'frappe-ui'

defineProps({
  title: { type: String, required: true },
  backTo: { type: [String, Object], default: null },
  breadcrumbs: { type: Array, default: null },
})
</script>

<template>
  <PageHeader>
    <!-- PageHeader's own row is `flex items-center justify-between` with nothing
         allowed to shrink, so without min-w-0 the title reports its full width and
         the page overflows sideways instead of the title ellipsising. -->
    <Breadcrumbs v-if="breadcrumbs" class="min-w-0" :items="breadcrumbs" />
    <h1 v-else class="min-w-0 truncate text-lg-semibold text-ink-gray-8">{{ title }}</h1>
    <div class="flex shrink-0 items-center gap-2">
      <slot name="actions" />
    </div>
  </PageHeader>
</template>

