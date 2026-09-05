<script setup>
import { computed, ref } from 'vue'
import { Button, Select, dialog, toast } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import Thumb from '../components/Thumb.vue'
import EmptyState from '../components/EmptyState.vue'
import BulkBar from '../components/BulkBar.vue'
import EditableValue from '../components/EditableValue.vue'
import { useAdminRead, useAdminAction } from '../data/api'
import { money } from '../data/format'
import { ia } from '../ia/store'

const selecting = ref(false)
const selection = ref([])

function endSelecting() {
  selecting.value = false
  selection.value = []
}

// ls_shop has no product-type schema at all (confirmed in docs/comera-wiring-map.md — the same
// gap flagged as open question #1 in docs/commera-open-questions.md, where section 1 substituted
// Collection for Type on its own judgement). That substitution needs the owner's yes/no before it
// is repeated, so this stays a single always-selected option rather than silently becoming
// something it isn't.
const type = ref('all')
const typeOptions = [{ label: 'All types', value: 'all' }]

const pricingRequest = useAdminRead('catalog.get_pricing_rows', {
  params: () => ({ page_length: 500 }),
  refetch: true,
})

// Same money semantics as VariantDetail.vue: sale_rate is what a shopper actually pays once a
// discount is on, default_rate is the higher struck-through reference — see
// ls_shop/product_detail.py's get_discount_percent, the source of this convention.
const rows = computed(() =>
  (pricingRequest.data?.rows ?? []).map((row) => {
    const hasSale = row.sale_rate != null && row.sale_rate < (row.default_rate ?? Infinity)
    return {
      ...row,
      price: hasSale ? row.sale_rate : (row.default_rate ?? 0),
      compareAt: hasSale ? row.default_rate : null,
      hasSale,
    }
  }),
)

const priceAction = useAdminAction('catalog.set_variant_price')

// Edits whichever field the shown "Price" actually is — sale_rate once a compare-at exists,
// default_rate otherwise — the same variant-wide bulk write (catalog.set_variant_price) the
// product page's own variant matrix uses, applying one rate to every size under the variant.
async function setPrice(row, rate) {
  const payload = row.hasSale
    ? { style_attribute_variant: row.name, sale_rate: rate }
    : { style_attribute_variant: row.name, default_rate: rate }
  await priceAction.submit(payload)
  if (priceAction.error) return
  toast.success(`Price updated for ${row.title} (${row.size_count} sizes)`)
  pricingRequest.reload()
}

function bulkRaisePrice() {
  const ids = [...selection.value]
  const selected = rows.value.filter((row) => ids.includes(row.name))
  if (!selected.length) return

  dialog.prompt({
    title: `Raise price on ${ids.length} ${ids.length === 1 ? 'item' : 'items'}`,
    message: 'Raises the price a shopper actually pays by this percentage, rounded to the nearest paisa.',
    fields: [{ name: 'value', label: 'Raise by %', type: 'number', required: true }],
    onConfirm: async ({ values }) => {
      const pct = Number(values.value) || 0
      for (const row of selected) {
        const rate = Math.round(row.price * (1 + pct / 100) * 100) / 100
        const payload = row.hasSale
          ? { style_attribute_variant: row.name, sale_rate: rate }
          : { style_attribute_variant: row.name, default_rate: rate }
        await priceAction.submit(payload)
        // A failure already toasted inside useAdminAction — stop rather than reprice the rest silently.
        if (priceAction.error) return
      }
      endSelecting()
      toast.success(`Price raised on ${selected.length} ${selected.length === 1 ? 'item' : 'items'}`)
      pricingRequest.reload()
    },
  })
}

function bulkSetCompareAt() {
  const ids = [...selection.value]
  const selected = rows.value.filter((row) => ids.includes(row.name))
  if (!selected.length) return

  dialog.prompt({
    title: `Set compare-at on ${ids.length} ${ids.length === 1 ? 'item' : 'items'}`,
    message: 'Sets the struck-through reference price shown above the real price.',
    fields: [{ name: 'value', label: 'Compare at', type: 'number', required: true }],
    onConfirm: async ({ values }) => {
      const rate = Math.max(0, Number(values.value) || 0)
      for (const row of selected) {
        await priceAction.submit({ style_attribute_variant: row.name, default_rate: rate })
        if (priceAction.error) return
      }
      endSelecting()
      toast.success(`Compare-at set on ${selected.length} ${selected.length === 1 ? 'item' : 'items'}`)
      pricingRequest.reload()
    },
  })
}
</script>

<template>
  <AppPageHeader
    title="Edit prices"
    back-to="/products"
    :breadcrumbs="[{ label: 'Products', route: '/products' }, { label: 'Edit prices' }]"
  >
    <template #actions>
      <!-- No price-rule engine and no export endpoint exist in ls_shop — left exactly as
           unwired as the prototype had them, just made honestly inert. -->
      <Button class="hidden sm:inline-flex" label="Price rules" icon-left="lucide-percent" disabled />
      <Button label="Export prices" icon-left="lucide-download" variant="solid" theme="gray" disabled />
    </template>
  </AppPageHeader>

  <PageBody>
    <div class="flex flex-wrap items-center gap-3">
      <Select v-model="type" :options="typeOptions" disabled />
      <p v-if="!pricingRequest.loading" class="text-sm text-ink-gray-5">
        {{ rows.length }} sellable units · one row per variant, priced individually on its product
      </p>
      <Button
        class="ml-auto"
        :label="selecting ? 'Cancel selection' : 'Select'"
        icon-left="lucide-list-checks"
        :variant="selecting ? 'solid' : 'subtle'"
        theme="gray"
        @click="selecting ? endSelecting() : (selecting = true)"
      />
    </div>

    <BulkBar v-if="selecting" :count="selection.length" noun="item" @done="endSelecting">
      <Button label="Raise by %" @click="bulkRaisePrice" />
      <Button label="Set compare-at" @click="bulkSetCompareAt" />
    </BulkBar>

    <p v-if="pricingRequest.loading" class="mt-3 text-sm text-ink-gray-5">Loading prices…</p>

    <div v-else class="mt-3 overflow-x-auto">
      <List
      v-model:selection="selection"
      class="min-w-[50rem]"
      :selectable="selecting"
      :row-height="Math.max(ia.density, 44)"
      :columns="['1fr', '11rem', '7rem', '8rem', '6rem']"
    >
      <ListHeader>
        <ListHeaderCell>Item</ListHeaderCell>
        <ListHeaderCell>SKU</ListHeaderCell>
        <ListHeaderCell>Price</ListHeaderCell>
        <ListHeaderCell>Compare at</ListHeaderCell>
        <ListHeaderCell>Margin</ListHeaderCell>
      </ListHeader>
      <ListRows :items="rows" row-key="name" v-slot="{ item }">
        <ListRow :value="item.name">
          <ListCell>
            <div class="flex min-w-0 items-center gap-2.5">
              <Thumb :image="item.image" size="size-7" />
              <div class="min-w-0">
                <p class="truncate text-base text-ink-gray-8">{{ item.title }}</p>
                <p class="truncate text-sm text-ink-gray-5">{{ item.subtitle }}</p>
              </div>
            </div>
          </ListCell>
          <ListCell><span class="truncate text-base text-ink-gray-5">{{ item.sku }}</span></ListCell>
          <ListCell>
            <EditableValue
              :model-value="item.price"
              label="Price"
              format="money"
              @update:model-value="(rate) => setPrice(item, rate)"
            />
          </ListCell>
          <ListCell>
            <span class="text-base tabular-nums" :class="item.compareAt ? 'text-ink-gray-7' : 'text-ink-gray-4'">
              {{ item.compareAt ? money(item.compareAt) : '—' }}
            </span>
          </ListCell>
          <ListCell>
            <!-- Inert: ls_shop has no cost/margin field anywhere (confirmed in
                 docs/comera-wiring-map.md) — the mock's 55%-assumed-COGS margin was a pure
                 client-side fabrication, never a stored value. See
                 docs/commera-open-questions.md, "Pricing: cost and margin — needs a product
                 decision" for the real options; none of them are picked here. -->
            <span class="text-base text-ink-gray-4 tabular-nums">—</span>
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
    </div>

    <EmptyState v-if="!pricingRequest.loading && !rows.length" icon="lucide-tag" title="No sellable items yet" description="Add a product to start pricing it." />
  </PageBody>
</template>

