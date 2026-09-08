<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, Dropdown, ScrollArea, toast } from 'frappe-ui'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import StatusBadge from '../components/StatusBadge.vue'
import VariantEditor from '../components/VariantEditor.vue'
import ProductBasics from '../components/product/ProductBasics.vue'
import ProductPricing from '../components/product/ProductPricing.vue'
import ProductStock from '../components/product/ProductStock.vue'
import ProductOrganization from '../components/product/ProductOrganization.vue'
import ProductStorefront from '../components/product/ProductStorefront.vue'
import ProductSummaryPanel from '../components/product/ProductSummaryPanel.vue'
import { useAdminRead, useAdminAction } from '../data/api'
import { longDate } from '../data/format'
import { useProductStats } from '../data/product'
import { asDropdownOptions, buildProductActions } from '../ia/productActions'

const route = useRoute()
const router = useRouter()

const productRequest = useAdminRead('catalog.get_product', {
  params: () => ({ item_template: route.params.id }),
  refetch: true,
})

// The rest of this screen was written against mock.js's flat, mutable product
// shape (status, title, sku, updated) with ProductBasics/ProductOrganization
// v-modelling straight onto it — this ref is that seam: a real `ref()` (so
// edits are properly reactive, unlike a plain object returned from a
// computed) reseeded from catalog.get_product every time it reloads.
const product = ref(null)
watch(
  () => productRequest.data,
  (data) => {
    if (!data) return
    product.value = {
      id: data.name,
      title: data.title,
      description: data.description,
      image: data.image,
      collection: data.collection,
      // Item only carries a disabled flag — there is no "draft" state in the
      // catalog (same fact Products.vue's list screen already works around).
      status: data.disabled ? 'archived' : 'active',
      restock_level: data.restock_level,
      sku: data.name,
      updated: data.updated,
      variants: data.variants,
      option_attribute: data.option_attribute,
      hasVariants: data.variants.length > 0,
      recent_sales: data.recent_sales,
    }
  },
  { immediate: true },
)

const stats = useProductStats(product)

const updateAction = useAdminAction('catalog.update_product')
const publishAction = useAdminAction('catalog.set_product_published')

async function togglePublish() {
  const publish = !product.value.variants.some((variant) => variant.is_published)
  const result = await publishAction.submit({ item_template: product.value.id, publish })
  if (publishAction.error) return
  productRequest.reload()
  if (result.skipped.length) {
    toast.warning(`Published ${result.updated.length}, skipped ${result.skipped.join(', ')} — missing a photo or size`)
  } else {
    toast.success(publish ? 'Published' : 'Hidden from the storefront')
  }
}

async function toggleArchive() {
  const disabled = product.value.status !== 'archived'
  await updateAction.submit({ item_template: product.value.id, disabled: disabled ? 1 : 0 })
  if (updateAction.error) return
  toast.success(disabled ? 'Archived' : 'Restored')
  productRequest.reload()
}

// The ⋯ menu's three "jump to a section" rows land here rather than reaching
// into the DOM themselves. The sections sit inside a ScrollArea viewport, which
// is a real overflow-scroll element, so scrollIntoView drives it. Instant, not
// smooth: the dropdown closing restores focus to its trigger, which cancels a
// smooth scroll still in flight and leaves the page where it started.
function scrollToSection(sectionId) {
  document.getElementById(sectionId)?.scrollIntoView({ behavior: 'instant', block: 'start' })
}

const actions = computed(() =>
  product.value
    ? buildProductActions(product.value, router, {
        onTogglePublish: togglePublish,
        onToggleArchive: toggleArchive,
        onScrollTo: scrollToSection,
        onReload: () => productRequest.reload(),
      })
    : { groups: [], quick: [] },
)

// ProductBasics/ProductOrganization write straight onto this ref's own
// fields via v-model (see their templates), so one Save just pushes whatever
// is currently on it — there is no separate draft to track.
async function save() {
  if (!product.value) return
  await updateAction.submit({
    item_template: product.value.id,
    title: product.value.title,
    collection: product.value.collection,
    description: product.value.description,
  })
  if (updateAction.error) return
  toast.success('Saved')
  productRequest.reload()
}

watch(
  () => route.params.id,
  () => productRequest.reload(),
)
</script>

<template>
  <template v-if="product">
    <AppPageHeader
      :title="product.title"
      back-to="/products"
      :breadcrumbs="[{ label: 'Products', route: '/products' }, { label: product.title }]"
    >
      <template #actions>
        <Dropdown :options="asDropdownOptions(actions.groups)">
          <Button icon="lucide-ellipsis" label="More actions" />
        </Dropdown>
        <Button label="Save" variant="solid" theme="gray" @click="save" />
      </template>
    </AppPageHeader>

    <!-- Two panes, each with its own scroll: the form is long and the summary
         beside it should stay put while you work down the form. -->
    <div class="flex min-h-0 flex-1 overflow-hidden">
      <ScrollArea class="min-w-0 flex-1">
        <PageBody width="narrow">
          <div class="flex flex-wrap items-center gap-2">
            <StatusBadge :status="product.status" />
            <span class="text-sm text-ink-gray-5">
              {{ product.sku }} · updated {{ longDate(product.updated) }}
            </span>
          </div>

          <div class="mt-6 space-y-11">
            <ProductBasics :product="product" />
            <ProductPricing :product="product" />
            <VariantEditor :product="product" @saved="productRequest.reload()" />
            <ProductStock :product="product" @received="productRequest.reload()" />
            <ProductStorefront :product="product" />
            <ProductOrganization :product="product" />
          </div>
        </PageBody>
      </ScrollArea>

      <aside class="hidden w-[19rem] shrink-0 flex-col border-l border-outline-gray-1 lg:flex">
        <ScrollArea class="min-h-0 flex-1">
          <ProductSummaryPanel :product="product" :stats="stats" />
        </ScrollArea>
      </aside>
    </div>
  </template>
</template>

