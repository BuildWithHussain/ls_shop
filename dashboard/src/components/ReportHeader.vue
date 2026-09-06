<script setup>
/**
 * Every report wears the same header: a range, a compare toggle, an export.
 * The sameness is the point. A report answers a question, so it carries no
 * primary action, which is what keeps it from reading like the dashboard.
 */
import { Button, Dropdown } from 'frappe-ui'
import AppPageHeader from './AppPageHeader.vue'
import ResponsiveButton from './ResponsiveButton.vue'

defineProps({
  title: { type: String, required: true },
  range: { type: String, required: true },
  compare: { type: Boolean, default: false },
})

const emit = defineEmits(['update:range', 'update:compare'])

const RANGES = ['Last 7 days', 'Last 30 days', 'Last 12 months', 'All time']
</script>

<template>
  <AppPageHeader
    :title="title"
    back-to="/analytics/revenue"
    :breadcrumbs="[{ label: 'Analytics', route: '/analytics/revenue' }, { label: title }]"
  >
    <template #actions>
      <Dropdown :options="RANGES.map((label) => ({ label, onClick: () => emit('update:range', label) }))">
        <Button :label="range" icon-right="lucide-chevron-down" />
      </Dropdown>
      <!-- Three labelled actions plus the range starve the title on a phone, so
           Compare drops to its icon and the still-unwired Export drops out. -->
      <ResponsiveButton
        label="Compare"
        icon="lucide-git-compare"
        :variant="compare ? 'subtle' : 'ghost'"
        @click="emit('update:compare', !compare)"
      />
      <Button class="hidden sm:inline-flex" icon-left="lucide-download" label="Export" />
    </template>
  </AppPageHeader>
</template>

