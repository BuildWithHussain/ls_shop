<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Alert, Badge, Button, Spinner } from 'frappe-ui'
import { closeImport, imp } from '../../../data/importFlow'
import { useAdminAction } from '../../../data/api'
import { openSettings } from '../../../ia/settings'
import ProductThumb from '../ProductThumb.vue'

const runImportAction = useAdminAction('imports.run_import')

async function run() {
  if (imp.running || imp.finished) return
  imp.running = true

  await runImportAction.submit({ file_url: imp.fileUrl, column_mapping: { ...imp.mapping } })
  imp.running = false
  imp.finished = true

  if (runImportAction.error) return
  const result = runImportAction.data
  imp.created = result.created
  imp.runRowErrors = result.row_errors
}

onMounted(run)

const router = useRouter()

function finish(path) {
  closeImport()
  router.push(path)
}

const NEXT = [
  { icon: 'lucide-credit-card', title: 'Turn on payments', body: 'Accept cards and UPI at checkout.', run: () => (closeImport(), openSettings('payments')) },
  { icon: 'lucide-truck', title: 'Set shipping rates', body: 'Flat rate, or by weight and pin code.', run: () => (closeImport(), openSettings('shipping')) },
  { icon: 'lucide-globe', title: 'Set up the storefront', body: 'Theme, navigation and pages.', run: () => finish('/storefront/theme') },
]
</script>

<template>
  <div class="space-y-6">
    <!-- Running -->
    <template v-if="!imp.finished">
      <div>
        <h2 class="text-xl text-ink-gray-9">Importing your catalogue</h2>
        <p class="mt-1 text-p-base text-ink-gray-6">This only takes a moment.</p>
      </div>

      <div class="rounded-5 border border-outline-gray-1 p-5">
        <div class="flex items-center gap-3">
          <Spinner class="size-4" />
          <span class="text-base text-ink-gray-8">Creating {{ imp.counts.products }} products…</span>
        </div>
      </div>

      <Alert description="Products appear in your catalogue as they land, so you can start editing right away." />
    </template>

    <!-- Failed outright (e.g. this store has no Color/Size attribute) -->
    <template v-else-if="runImportAction.error">
      <div class="rounded-6 border border-outline-gray-1 px-6 py-8 text-center">
        <div class="mx-auto flex size-12 items-center justify-center rounded-full bg-surface-red-2 text-ink-red-6">
          <span class="lucide-triangle-alert size-6" aria-hidden="true" />
        </div>
        <h2 class="mt-4 text-xl text-ink-gray-9">The import could not run</h2>
        <p class="mx-auto mt-1.5 max-w-[460px] text-p-base text-ink-gray-6">
          {{ runImportAction.error?.message }}
        </p>
        <Button class="mt-4" label="Close" @click="closeImport" />
      </div>
    </template>

    <!-- Done -->
    <template v-else>
      <div class="rounded-6 border border-outline-gray-1 px-6 py-8 text-center">
        <div class="mx-auto flex size-12 items-center justify-center rounded-full bg-surface-green-2 text-ink-green-7">
          <span class="lucide-party-popper size-6" aria-hidden="true" />
        </div>
        <h2 class="mt-4 text-2xl text-ink-gray-9">{{ imp.created.length }} products are live</h2>
        <p class="mx-auto mt-1.5 max-w-[460px] text-p-base text-ink-gray-6">
          Your catalogue now has these products. Add photos from each product page to publish them.
        </p>

        <div v-if="imp.created.length" class="mt-5 flex flex-wrap justify-center gap-2">
          <ProductThumb v-for="p in imp.created.slice(0, 12)" :key="p.item_template" :seed="p.item_template" size="size-12" />
        </div>

        <div class="mt-6 flex flex-wrap items-center justify-center gap-2">
          <Button variant="solid" theme="gray" label="View my products" @click="finish('/products')" />
          <Button label="Back to overview" @click="finish('/')" />
        </div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="rounded-5 border border-outline-gray-1 p-4">
          <div class="text-2xl text-ink-gray-9 tabular-nums">{{ imp.created.length }}</div>
          <div class="mt-0.5 text-sm text-ink-gray-5">products created</div>
        </div>
        <div class="rounded-5 border border-outline-gray-1 p-4">
          <div class="flex items-baseline gap-2">
            <span class="text-2xl text-ink-red-6 tabular-nums">{{ imp.runRowErrors.length }}</span>
            <Badge v-if="imp.runRowErrors.length" label="Fix and re-upload" theme="red" variant="subtle" />
          </div>
          <div class="mt-0.5 text-sm text-ink-gray-5">rows skipped</div>
        </div>
      </div>

      <div v-if="imp.runRowErrors.length" class="rounded-5 border border-outline-gray-1">
        <div class="border-b border-outline-gray-1 px-4 py-3 text-base-semibold text-ink-gray-8">
          Rows that did not import
        </div>
        <div class="max-h-56 divide-y divide-outline-gray-1 overflow-y-auto">
          <div v-for="e in imp.runRowErrors" :key="e.row" class="flex items-start gap-3 px-4 py-2.5">
            <span class="shrink-0 text-sm tabular-nums text-ink-gray-5">Row {{ e.row }}</span>
            <span class="text-sm text-ink-gray-7">{{ e.message }}</span>
          </div>
        </div>
      </div>

      <div class="rounded-5 border border-outline-gray-1 p-4">
        <div class="text-base-semibold text-ink-gray-8">What usually comes next</div>
        <div class="mt-3 divide-y divide-outline-gray-1">
          <div v-for="n in NEXT" :key="n.title" class="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            <span :class="[n.icon, 'size-4 text-ink-gray-6']" aria-hidden="true" />
            <div class="min-w-0 flex-1">
              <div class="text-base text-ink-gray-8">{{ n.title }}</div>
              <div class="text-sm text-ink-gray-5">{{ n.body }}</div>
            </div>
            <Button variant="subtle" label="Start" @click="n.run" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

