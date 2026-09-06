<script setup>
/**
 * Where the storefront ships from. This shop sells out of one warehouse, so this is a statement of
 * fact rather than a list to manage — the warehouse itself is set up in the books.
 */
import { watch } from 'vue'
import { Badge, LoadingText, SettingsBody, SettingsHeader } from 'frappe-ui'
import { useAdminRead } from '../../data/api'

const props = defineProps({
  active: { type: Boolean, default: false },
})

const locations = useAdminRead('settings.get_locations', { immediate: false })

watch(
  () => props.active,
  (isActive) => isActive && !locations.isFinished && locations.reload(),
  { immediate: true },
)
</script>

<template>
  <SettingsHeader title="Locations" description="The warehouse online orders are fulfilled from." />

  <SettingsBody>
    <LoadingText v-if="locations.loading && !locations.data" class="py-10" />

    <p v-else-if="!locations.data?.length" class="py-6 text-base text-ink-gray-5">
      No ecommerce warehouse is set yet, so orders have nothing to reserve stock against. Set one
      under Advanced → Ecommerce Warehouse.
    </p>

    <div v-else class="divide-y divide-outline-gray-1">
      <div
        v-for="location in locations.data"
        :key="location.name"
        class="flex items-center justify-between gap-3 py-3"
      >
        <div class="min-w-0">
          <p class="truncate text-base text-ink-gray-8">{{ location.warehouse_name }}</p>
          <p class="mt-1 truncate text-sm text-ink-gray-5">
            {{ location.name }}<span v-if="location.company"> · {{ location.company }}</span>
          </p>
        </div>
        <Badge
          :label="location.disabled ? 'Disabled' : 'Fulfils online orders'"
          :theme="location.disabled ? 'orange' : 'green'"
          variant="subtle"
        />
      </div>
    </div>
  </SettingsBody>
</template>
