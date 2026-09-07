<script setup>
import { computed } from 'vue'
import { Avatar, Button } from 'frappe-ui'
import { LineChart } from 'frappe-ui/charts'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import StatusBadge from '../components/StatusBadge.vue'
import Thumb from '../components/Thumb.vue'
import { useAdminRead } from '../data/api'
import { compactMoney, money, shortDate } from '../data/format'
import { ia } from '../ia/store'

// The whole screen in three calls: orders.get_overview already backs the Home screen's stats,
// recent orders and low-stock/needs-attention panels; catalog.get_top_products and
// analytics.get_revenue_report add the bestseller row and the revenue trend the overview call
// doesn't carry. Every id these calls return is a real record name, so every link on this screen
// (the audit's #1 "fix this first") resolves on the real Orders/Products screens instead of
// throwing on a mock slug.
const overviewRequest = useAdminRead('orders.get_overview')
const topProductsRequest = useAdminRead('catalog.get_top_products', { params: () => ({ limit: 4 }) })
const revenueRequest = useAdminRead('analytics.get_revenue_report', { params: () => ({ months: 12 }) })

const overview = computed(() => overviewRequest.data)

const kpiTiles = computed(() =>
  (overview.value?.stats ?? []).map((stat) => ({
    key: stat.key,
    label: stat.label,
    value: stat.format === 'currency' ? money(stat.value) : Number(stat.value).toLocaleString('en-IN'),
    delta: stat.delta,
    note: stat.note,
  })),
)

// Only what is actually waiting: a block that lists a zero is a block that teaches you to stop
// reading it. "Payments pending" is gone from this list on purpose — every seeded order here is
// Cash on Delivery, which orders.describe_payment_state always reports as pending until the
// courier collects it at the door, so a count here would just be "how many COD orders exist",
// not something the owner can act on.
const attention = computed(() => {
  if (!overview.value) return []
  const toFulfil = overview.value.stats.find((stat) => stat.key === 'to_fulfil')
  // The panels below carry five rows each; these tiles count the whole store, so they read the
  // totals the endpoint sends rather than the length of the preview.
  const lowStockCount = overview.value.running_low_total
  const needsAttentionCount = overview.value.needs_attention_total
  return [
    {
      icon: 'lucide-package-open',
      title: `${toFulfil?.value ?? 0} ${toFulfil?.value === 1 ? 'order' : 'orders'} to fulfil`,
      note: toFulfil?.note,
      action: 'Fulfil orders',
      to: '/orders',
    },
    {
      icon: 'lucide-triangle-alert',
      title: `${lowStockCount} ${lowStockCount === 1 ? 'variant' : 'variants'} low on stock`,
      note: 'At or below five units',
      action: 'Restock',
      to: '/inventory',
    },
    {
      icon: 'lucide-file-pen-line',
      title: `${needsAttentionCount} ${needsAttentionCount === 1 ? 'product needs' : 'products need'} attention`,
      note: 'Missing a photo or a size before it can publish',
      action: 'Open catalogue',
      to: '/products',
    },
  ].filter((row) => !row.title.startsWith('0 '))
})

const recentOrders = computed(() => overview.value?.recent_orders ?? [])
const topProducts = computed(() => topProductsRequest.data?.products ?? [])
const revenueByMonth = computed(() => revenueRequest.data?.months ?? [])
</script>

<template>
  <AppPageHeader title="Overview">
    <template #actions>
      <Button label="Add product" icon-left="lucide-plus" variant="solid" theme="gray" route="/products" />
    </template>
  </AppPageHeader>

  <PageBody width="narrow">
    <p v-if="overviewRequest.loading" class="text-sm text-ink-gray-5">Loading overview…</p>

    <template v-else>
      <div class="grid grid-cols-2 rounded-5 border border-outline-gray-1 sm:grid-cols-4 sm:divide-x sm:divide-outline-gray-2">
        <div v-for="kpi in kpiTiles" :key="kpi.key" class="px-4 py-3.5">
          <p class="text-sm text-ink-gray-5">{{ kpi.label }}</p>
          <p class="mt-1 text-2xl text-ink-gray-9 tabular-nums">{{ kpi.value }}</p>
          <p
            v-if="kpi.delta != null"
            class="mt-1 text-sm"
            :class="kpi.delta >= 0 ? 'text-ink-green-6' : 'text-ink-red-6'"
          >
            {{ kpi.delta >= 0 ? '+' : '' }}{{ kpi.delta }}% vs. last period
          </p>
          <p v-else class="mt-1 truncate text-sm text-ink-gray-5">{{ kpi.note }}</p>
        </div>
      </div>

      <section v-if="attention.length" class="mt-6">
        <h2 class="text-lg-semibold text-ink-gray-8">Needs attention</h2>
        <div class="mt-2 divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-1">
          <div v-for="row in attention" :key="row.title" class="flex items-center gap-3 px-4 py-3">
            <span class="grid size-8 shrink-0 place-items-center rounded-full bg-surface-gray-2 text-ink-gray-6">
              <span :class="[row.icon, 'size-4']" aria-hidden="true" />
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-base text-ink-gray-8">{{ row.title }}</p>
              <p class="mt-1 truncate text-sm text-ink-gray-5">{{ row.note }}</p>
            </div>
            <Button :label="row.action" :route="row.to" />
          </div>
        </div>
      </section>
    </template>

    <section class="mt-6 rounded-5 border border-outline-gray-1 p-4">
      <div class="flex items-center justify-between">
        <h2 class="text-lg-semibold text-ink-gray-8">Revenue</h2>
        <div class="flex items-center gap-2">
          <span class="text-sm text-ink-gray-5">Last 12 months</span>
          <Button
            variant="ghost"
            label="Revenue report"
            icon-right="lucide-arrow-right"
            route="/analytics/revenue"
          />
        </div>
      </div>
      <div class="h-72">
        <LineChart :data="revenueByMonth" x="label" :y="['revenue']" />
      </div>
    </section>

    <section class="mt-6 rounded-5 border border-outline-gray-1">
      <div class="flex items-center justify-between px-4 py-3">
        <h2 class="text-lg-semibold text-ink-gray-8">Recent orders</h2>
        <Button variant="ghost" label="View all" icon-right="lucide-arrow-right" route="/orders" />
      </div>
      <div class="overflow-x-auto px-2 pb-2">
        <!-- Four of the five tracks are fixed at 31rem between them, so the
             floor is not about the table's own width: below 44rem the only
             flexible track, the customer name, is starved to a few characters.
             The wrapper scrolls horizontally instead. -->
        <List
          class="min-w-[44rem]"
          :columns="['9rem', 'minmax(0,1fr)', '9rem', '7rem', '6rem']"
          :row-height="Math.max(ia.density, 48)"
        >
          <ListHeader>
            <ListHeaderCell>Order</ListHeaderCell>
            <ListHeaderCell>Customer</ListHeaderCell>
            <ListHeaderCell>Status</ListHeaderCell>
            <ListHeaderCell>Total</ListHeaderCell>
            <ListHeaderCell>Placed</ListHeaderCell>
          </ListHeader>
          <ListRows :items="recentOrders" row-key="name" v-slot="{ item }">
            <ListRow :to="`/orders/${item.name}`" :value="item.name">
              <ListCell>
                <span class="truncate text-base text-ink-gray-5 tabular-nums">{{ item.name }}</span>
              </ListCell>
              <ListCell>
                <div class="flex min-w-0 items-center gap-2">
                  <Avatar :label="item.customer" size="sm" />
                  <span class="truncate text-base text-ink-gray-8">{{ item.customer }}</span>
                </div>
              </ListCell>
              <ListCell>
                <div class="flex items-center gap-1.5">
                  <StatusBadge :status="item.payment_state.key" :label="item.payment_state.label" />
                  <StatusBadge :status="item.state.key" :label="item.state.label" />
                </div>
              </ListCell>
              <ListCell>
                <span class="text-base text-ink-gray-7 tabular-nums">{{ money(item.total) }}</span>
              </ListCell>
              <ListCell>
                <span class="text-base text-ink-gray-5">{{ shortDate(item.placed_on) }}</span>
              </ListCell>
            </ListRow>
          </ListRows>
        </List>
      </div>
    </section>

    <section class="mt-6 rounded-5 border border-outline-gray-1">
      <div class="flex items-center justify-between px-4 py-3">
        <h2 class="text-lg-semibold text-ink-gray-8">Top products</h2>
        <Button variant="ghost" label="All products" icon-right="lucide-arrow-right" route="/products" />
      </div>
      <div class="divide-y divide-outline-gray-1 border-t border-outline-gray-1">
        <RouterLink
          v-for="product in topProducts"
          :key="product.name"
          :to="`/products/${product.name}`"
          class="flex items-center gap-3 px-4 py-3 hover:bg-surface-gray-1"
        >
          <Thumb :image="product.image" size="size-8" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-base text-ink-gray-8">{{ product.title }}</p>
            <p class="mt-1 text-sm text-ink-gray-5">{{ product.stock }} in stock</p>
          </div>
          <span class="w-20 text-right text-sm text-ink-gray-5 tabular-nums">{{ product.units }} sold</span>
          <span class="w-24 text-right text-base text-ink-gray-7 tabular-nums">
            {{ compactMoney(product.revenue) }}
          </span>
        </RouterLink>
      </div>
    </section>
  </PageBody>
</template>

