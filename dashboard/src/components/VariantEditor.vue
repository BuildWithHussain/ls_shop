<script setup>
import { computed, ref } from 'vue'
import { Badge, Button, dialog, toast } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import Thumb from './Thumb.vue'
import EditableValue from './EditableValue.vue'
import VariantDialog from './VariantDialog.vue'
import { useAdminAction } from '../data/api'
import { stockTone } from '../data/format'
import { ia } from '../ia/store'

const props = defineProps({ product: { type: Object, required: true } })
const emit = defineEmits(['saved'])

const selection = ref([])

// A row opens the variant rather than navigating: a variant is a small record,
// and you are usually working down the matrix, not away from it.
const editing = ref(null)
const showVariant = ref(false)

function openVariant(variant) {
  editing.value = variant
  showVariant.value = true
}

// Every real option (Style Attribute Variant) already carries its own single
// attribute value — Color, say — set at product creation. ls_shop has no
// endpoint to add a further axis to an existing product (create_product only
// takes option_attribute/size_attribute once, at insert), so unlike the
// prototype's options[] this list is read-only: it names the one axis this
// product already has and shows its values, nothing more.
const optionValues = computed(() => [...new Set(props.product.variants.map((v) => v.option))])

const priceAction = useAdminAction('catalog.set_variant_price')

async function setPrice(variant, rate) {
  await priceAction.submit({ style_attribute_variant: variant.name, default_rate: rate })
  if (priceAction.error) return
  toast.success(`Price updated for ${variant.option} (${variant.sizes.length} sizes)`)
  emit('saved')
}

async function bulkSetPrice() {
  const ids = [...selection.value]
  dialog.prompt({
    title: `Set price on ${ids.length} ${ids.length === 1 ? 'variant' : 'variants'}`,
    message: 'Sets the price for every size under each selected variant.',
    fields: [{ name: 'value', label: 'Price', type: 'number', required: true }],
    onConfirm: async ({ values }) => {
      const rate = Math.max(0, Number(values.value) || 0)
      for (const name of ids) {
        await priceAction.submit({ style_attribute_variant: name, default_rate: rate })
        // A failure already toasted inside useAdminAction — stop rather than reprice the rest silently.
        if (priceAction.error) return
      }
      selection.value = []
      toast.success(`Price updated on ${ids.length} ${ids.length === 1 ? 'variant' : 'variants'}`)
      emit('saved')
    },
  })
}

// Five columns, because the matrix sits beside the summary panel: the barcode
// is on the variant's own page, where there is room for it.
const columns = ['minmax(7rem,1.3fr)', 'minmax(5rem,1fr)', '6.5rem', '5rem', '4.5rem']
</script>

<template>
  <section class="space-y-5">
    <!-- The axis, first: the matrix below is nothing but its values. -->
    <div id="product-options" class="rounded-5 border border-outline-gray-1">
      <div class="px-4 py-3">
        <h2 class="text-lg-semibold text-ink-gray-8">Options</h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ product.option_attribute ?? 'Option' }}, set at creation.</p>
      </div>

      <div v-if="optionValues.length" class="border-t border-outline-gray-1 px-4 py-3">
        <div class="flex items-start gap-3">
          <span class="w-24 shrink-0 pt-0.5 text-base text-ink-gray-6">{{ product.option_attribute }}</span>
          <div class="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
            <Badge v-for="value in optionValues" :key="value" :label="value" variant="subtle" />
          </div>
        </div>
      </div>

      <div v-else class="border-t border-outline-gray-1 px-4 py-6 text-center">
        <p class="text-base text-ink-gray-7">This product has no options</p>
        <p class="mt-1 text-p-sm text-ink-gray-5">It sells as a single item.</p>
      </div>
    </div>

    <!-- The matrix: one row per option, each with its own sizes underneath. -->
    <div v-if="product.variants.length" id="product-variants" class="rounded-5 border border-outline-gray-1">
      <div class="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
        <h2 class="text-lg-semibold text-ink-gray-8">Variants</h2>
        <div class="flex items-center gap-2">
          <template v-if="selection.length">
            <span class="text-sm text-ink-gray-5">{{ selection.length }} selected</span>
            <Button label="Set price" @click="bulkSetPrice" />
            <Button label="Clear" variant="ghost" @click="selection = []" />
          </template>
        </div>
      </div>

      <div class="overflow-x-auto px-2 pb-2">
        <List
          v-model:selection="selection"
          class="min-w-[30rem]"
          selectable
          :row-height="Math.max(ia.density, 48)"
          :columns="columns"
        >
          <ListHeader>
            <ListHeaderCell>Variant</ListHeaderCell>
            <ListHeaderCell>Sizes</ListHeaderCell>
            <ListHeaderCell>Price</ListHeaderCell>
            <ListHeaderCell>Stock</ListHeaderCell>
            <ListHeaderCell>Photos</ListHeaderCell>
          </ListHeader>
          <ListRows :items="product.variants" row-key="name" v-slot="{ item }">
            <ListRow :value="item.name">
              <ListCell>
                <button class="flex min-w-0 items-center gap-2.5" @click.stop="openVariant(item)">
                  <Thumb :image="item.images[0]" size="size-7" />
                  <span class="truncate text-base text-ink-gray-8">{{ item.option }}</span>
                </button>
              </ListCell>
              <ListCell>
                <span class="truncate text-base text-ink-gray-5">
                  {{ item.sizes.map((s) => s.size).join(', ') || '—' }}
                </span>
              </ListCell>
              <ListCell>
                <!-- One price for the whole row: sets every size under this variant
                     in one pass (catalog.set_variant_price), the same bulk operation
                     create_product uses. Per-size prices are edited on the variant's
                     own page, where there is room to show them individually. -->
                <EditableValue
                  :model-value="item.sizes[0]?.default_rate ?? 0"
                  label="Price"
                  format="money"
                  @update:model-value="(rate) => setPrice(item, rate)"
                />
              </ListCell>
              <ListCell>
                <!-- Read-only: ls_shop only exposes receiving stock (additive), not
                     setting on-hand to an arbitrary number — see VariantDetail. -->
                <EditableValue
                  :model-value="item.sizes.reduce((sum, s) => sum + (s.stock ?? 0), 0)"
                  label="On hand"
                  readonly
                  :class="stockTone(item.sizes.reduce((sum, s) => sum + (s.stock ?? 0), 0))"
                />
              </ListCell>
              <ListCell>
                <!-- Photos are per variant, so the count is a way in, not a stat. -->
                <button
                  class="flex items-center gap-1.5 rounded-4 px-1.5 py-0.5 hover:bg-surface-gray-2"
                  @click.stop="openVariant(item)"
                >
                  <span
                    class="size-3.5"
                    :class="item.images.length ? 'lucide-image text-ink-gray-6' : 'lucide-image-plus text-ink-gray-4'"
                    aria-hidden="true"
                  />
                  <span class="text-base tabular-nums" :class="item.images.length ? 'text-ink-gray-7' : 'text-ink-gray-4'">
                    {{ item.images.length || 'Add' }}
                  </span>
                </button>
              </ListCell>
            </ListRow>
          </ListRows>
        </List>
      </div>
    </div>
  </section>

  <VariantDialog v-model:open="showVariant" :variant="editing" :product="product" @saved="emit('saved')" />
</template>

