<script setup>
import { computed, ref, watch } from 'vue'
import { Button, TabButtons, TextInput, toast } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListHeaderCellSort, ListRow, ListRows } from 'frappe-ui/list'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import ListPagination from '../components/ListPagination.vue'
import StatusBadge from '../components/StatusBadge.vue'
import EmptyState from '../components/EmptyState.vue'
import BulkBar from '../components/BulkBar.vue'
import { useAdminRead, useAdminAction } from '../data/api'
import { printUrl } from '../data/erpnext'
import { money, shortDate } from '../data/format'
import { ia } from '../ia/store'

const TABS = [
  { label: 'All', value: 'all' },
  { label: 'Unfulfilled', value: 'unfulfilled' },
  { label: 'Unpaid', value: 'unpaid' },
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
]

const tab = ref('all')
const query = ref('')
const selecting = ref(false)
const selection = ref([])

function endSelecting() {
  selecting.value = false
  selection.value = []
}

const sort = ref({ key: 'date', direction: 'desc' })
const page = ref(1)
const pageSize = ref(20)

const ordersRequest = useAdminRead('orders.get_orders', {
  params: () => ({
    status: tab.value === 'all' ? undefined : tab.value,
    search: query.value || undefined,
    start: (page.value - 1) * pageSize.value,
    page_length: pageSize.value,
  }),
  refetch: true,
})

// A filter changes what page one is, so it sends you back to it.
watch([query, tab], () => (page.value = 1))

const total = computed(() => ordersRequest.data?.total ?? 0)

// The endpoint orders by newest first — the header toggle re-sorts the loaded
// page itself, same convention Products.vue's list uses.
const rows = computed(() => {
  const orders = ordersRequest.data?.orders ?? []
  const { key, direction } = sort.value
  const dir = direction === 'asc' ? 1 : -1
  const valueFor = (row) => {
    if (key === 'total') return row.total
    if (key === 'date') return row.placed_on
    return row.customer
  }
  return [...orders].sort((a, b) => {
    const av = valueFor(a)
    const bv = valueFor(b)
    return av > bv ? dir : av < bv ? -dir : 0
  })
})

function toggleSort(key) {
  sort.value =
    sort.value.key === key
      ? { key, direction: sort.value.direction === 'asc' ? 'desc' : 'asc' }
      : { key, direction: 'asc' }
}

const directionFor = (key) => (sort.value.key === key ? sort.value.direction : null)

const fulfilAction = useAdminAction('orders.fulfil_order')

// There is no bulk-fulfil endpoint (fulfil_order ships one order at a time) — same
// sequential-loop shape Products.vue's bulk archive already uses for the same reason.
async function markFulfilled() {
  const names = [...selection.value]
  if (!names.length) return

  for (const name of names) {
    await fulfilAction.submit({ sales_order: name })
    // A failure already toasted inside useAdminAction — stop rather than fulfil the rest silently.
    if (fulfilAction.error) return
  }

  toast.success(`${names.length} order(s) marked fulfilled`)
  endSelecting()
  ordersRequest.reload()
}

// A packing slip is the Delivery Note, not the invoice: a prepaid order is
// invoiced at payment time, long before anything is packed, so an order can be
// fully invoiced and still have nothing to pack.
function printDeliveryNotes() {
  const ordersByName = new Map(rows.value.map((row) => [row.name, row]))
  const deliveryNotes = []
  const nothingToPrint = []

  for (const name of selection.value) {
    const deliveries = ordersByName.get(name)?.deliveries ?? []
    if (deliveries.length) deliveryNotes.push(...deliveries)
    else nothingToPrint.push(name)
  }

  // Named, not silently dropped — otherwise a mixed selection prints short and
  // the merchant packs one parcel fewer than they selected.
  if (nothingToPrint.length) {
    toast.warning(`No delivery note yet for ${nothingToPrint.join(', ')} — nothing to print.`)
  }
  if (!deliveryNotes.length) return

  window.open(printUrl('Delivery Note', deliveryNotes), '_blank', 'noopener')
}
</script>

<template>
  <AppPageHeader title="Orders">
    <template #actions>
      <!-- Export has no backend concept in ls_shop — kept as an inert affordance in this
           frozen layout rather than wired to nothing. Hidden on a phone, where the header
           has room for one action and this one does nothing yet. -->
      <Button
        class="hidden sm:inline-flex"
        label="Export"
        icon-left="lucide-download"
        @click="() => toast.info('Export is coming soon')"
      />
      <!-- Staff placing an order on a shopper's behalf isn't a supported flow in ls_shop (see the
           order-ownership rule in ls_shop/utils.py) — kept inert rather than pointed at nothing. -->
      <Button
        label="Create order"
        icon-left="lucide-plus"
        variant="solid"
        theme="gray"
        @click="() => toast.info('Creating an order from the dashboard isn\'t supported yet')"
      />
    </template>
  </AppPageHeader>

  <PageBody>
    <div class="flex flex-wrap items-center gap-2">
      <TabButtons v-model="tab" size="sm" :options="TABS" />
      <TextInput
        v-model="query"
        class="ml-auto w-56"
        placeholder="Search orders"
        icon-left="lucide-search"
      />
      <Button
        :label="selecting ? 'Cancel selection' : 'Select'"
        icon-left="lucide-list-checks"
        :variant="selecting ? 'solid' : 'subtle'"
        theme="gray"
        @click="selecting ? endSelecting() : (selecting = true)"
      />
    </div>

    <BulkBar v-if="selecting" :count="selection.length" noun="order" @done="endSelecting">
      <Button label="Mark fulfilled" @click="markFulfilled" />
      <Button label="Print delivery notes" @click="printDeliveryNotes" />
    </BulkBar>

    <p v-if="ordersRequest.loading" class="mt-3 text-sm text-ink-gray-5">Loading orders…</p>

    <div v-else class="mt-3 overflow-x-auto">
      <List
      v-model:selection="selection"
      class="min-w-[54rem]"
      :selectable="selecting"
      :row-height="ia.density"
      :columns="['1fr', '7rem', '9rem', '9rem', '6rem', '7rem']"
    >
      <ListHeader>
        <ListHeaderCellSort :direction="directionFor('customer')" @click="toggleSort('customer')">
          Order
        </ListHeaderCellSort>
        <ListHeaderCellSort :direction="directionFor('date')" @click="toggleSort('date')">
          Date
        </ListHeaderCellSort>
        <ListHeaderCell>Payment</ListHeaderCell>
        <ListHeaderCell>Fulfilment</ListHeaderCell>
        <ListHeaderCell>Items</ListHeaderCell>
        <ListHeaderCellSort align="end" :direction="directionFor('total')" @click="toggleSort('total')">
          Total
        </ListHeaderCellSort>
      </ListHeader>

      <ListRows :items="rows" row-key="name" v-slot="{ item }">
        <ListRow :to="`/orders/${item.name}`" :value="item.name">
          <ListCell>
            <div class="min-w-0">
              <p class="truncate text-base text-ink-gray-8">{{ item.customer }}</p>
              <p class="truncate text-sm text-ink-gray-4 tabular-nums">{{ item.name }}</p>
            </div>
          </ListCell>
          <ListCell>
            <span class="text-base text-ink-gray-5">{{ shortDate(item.placed_on) }}</span>
          </ListCell>
          <ListCell>
            <StatusBadge :status="item.payment_state.key" :label="item.payment_state.label" />
          </ListCell>
          <ListCell>
            <StatusBadge :status="item.state.key" :label="item.state.label" />
          </ListCell>
          <ListCell>
            <span class="text-base text-ink-gray-7 tabular-nums">{{ item.item_count }}</span>
          </ListCell>
          <ListCell>
            <span class="w-full text-right text-base text-ink-gray-8 tabular-nums">
              {{ money(item.total) }}
            </span>
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
    </div>

    <ListPagination
      v-if="total"
      v-model:page="page"
      v-model:page-size="pageSize"
      :total="total"
    />

    <EmptyState
      v-if="!ordersRequest.loading && !rows.length"
      icon="lucide-shopping-bag"
      title="No orders here"
      description="Try a different filter or search term."
    />
  </PageBody>
</template>

