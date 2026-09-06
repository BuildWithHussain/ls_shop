<script setup>
import { computed } from 'vue'
import { MultiSelect, Select, TextInput } from 'frappe-ui'
import { useAdminRead } from '../../data/api'

const props = defineProps({
  product: { type: Object, required: true },
  layout: { type: String, default: 'stacked' },
})

const statusOptions = [
  { label: 'Active', value: 'active' },
  { label: 'Draft', value: 'draft' },
  { label: 'Archived', value: 'archived' },
]

const collectionsRequest = useAdminRead('catalog.get_collections')
const collectionOptions = computed(() => (collectionsRequest.data ?? []).map((name) => ({ label: name, value: name })))

// Item.item_group is a single collection, not the mock's array of them — the
// MultiSelect widget stays (it is the approved control), wrapped around one
// value, so picking a second collection here replaces the first rather than
// adding to it.
const productCollections = computed({
  get: () => (props.product.collection ? [props.product.collection] : []),
  set: (values) => {
    props.product.collection = values.at(-1) ?? null
  },
})
</script>

<template>
  <section :class="layout === 'stacked' ? '' : 'space-y-4'">
    <h2 v-if="layout === 'stacked'" class="text-lg-semibold text-ink-gray-8">Organisation</h2>
    <h3 v-else class="text-sm text-ink-gray-5">Organisation</h3>

    <div :class="layout === 'stacked' ? 'mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2' : 'mt-4 space-y-4'">
      <!-- Status is read-only here: it is really Item.disabled, and the page's
           "Archive"/"Restore from archive" action (in the ⋯ menu) is the one real
           write path for it — a second editable control here would just race it. -->
      <Select :model-value="product.status" class="w-full" label="Status" :options="statusOptions" disabled />
      <!-- ls_shop's Item has no vendor/brand field surfaced by the admin API. -->
      <TextInput :model-value="product.vendor" class="w-full" label="Vendor" disabled />
      <MultiSelect v-model="productCollections" class="w-full" label="Collections" :options="collectionOptions" />
      <!-- No tag concept exposed by the admin API. -->
      <TextInput
        :model-value="(product.tags ?? []).join(', ')"
        class="w-full"
        label="Tags"
        :class="layout === 'stacked' ? 'sm:col-span-2' : ''"
        disabled
      />
    </div>
  </section>
</template>
