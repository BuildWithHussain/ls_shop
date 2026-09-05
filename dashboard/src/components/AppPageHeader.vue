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
    <Breadcrumbs v-if="breadcrumbs" :items="breadcrumbs" />
    <h1 v-else class="text-lg-semibold text-ink-gray-8">{{ title }}</h1>
    <div class="flex items-center gap-2">
      <slot name="actions" />
    </div>
  </PageHeader>
</template>

