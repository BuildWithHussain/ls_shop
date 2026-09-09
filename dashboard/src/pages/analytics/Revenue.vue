<script setup>
import { computed, ref } from 'vue'
import { AreaChart, BarChart } from 'frappe-ui/charts'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import ReportHeader from '../../components/ReportHeader.vue'
import ReportStats from '../../components/ReportStats.vue'
import PageBody from '../../components/PageBody.vue'
import { useAdminRead } from '../../data/api'
import { monthsForRange } from '../../data/analytics'
import { compactMoney, money } from '../../data/format'
import { ia } from '../../ia/store'

const range = ref('Last 12 months')
const compare = ref(true)

// Same convention orders.get_overview and the Home screen use: a draft Cash-on-Delivery order is
// still real revenue (see commera.api.admin.orders.is_webshop_order), so this never disagrees with
// what the Orders list or the Home KPI strip report for the same window.
const reportRequest = useAdminRead('analytics.get_revenue_report', {
  params: () => ({ months: monthsForRange(range.value) }),
  refetch: true,
})

const months = computed(() => reportRequest.data?.months ?? [])
const totals = computed(() => reportRequest.data?.stats ?? {})

function delta(stat) {
  if (!stat || !stat.previous) return null
  return Math.round(((stat.value - stat.previous) / stat.previous) * 1000) / 10
}

function deltaLabel(stat) {
  const change = delta(stat)
  return change == null ? null : `${change >= 0 ? '+' : ''}${change}%`
}

const stats = computed(() => {
  const revenue = totals.value.revenue
  const orders = totals.value.orders
  const aov = totals.value.aov
  const refunds = totals.value.refunds
  return [
    { label: 'Gross revenue', value: compactMoney(revenue?.value ?? 0), delta: deltaLabel(revenue), up: (delta(revenue) ?? 0) >= 0 },
    { label: 'Orders', value: (orders?.value ?? 0).toLocaleString('en-IN'), delta: deltaLabel(orders), up: (delta(orders) ?? 0) >= 0 },
    { label: 'Avg. order value', value: money(aov?.value ?? 0), delta: deltaLabel(aov), up: (delta(aov) ?? 0) >= 0 },
    { label: 'Refunded', value: compactMoney(refunds?.value ?? 0), delta: deltaLabel(refunds), up: (delta(refunds) ?? 0) <= 0 },
  ]
})

const rows = computed(() =>
  [...months.value].reverse().map((row) => ({ ...row, net: row.revenue - row.refunds - row.discounts })),
)
</script>

<template>
  <ReportHeader title="Revenue" v-model:range="range" v-model:compare="compare" />

  <PageBody width="narrow">
    <div>
      <h1 class="text-2xl text-ink-gray-9">Revenue</h1>
      <p class="mt-1 text-p-base text-ink-gray-6">
        What the store earned, and what came back off the top. {{ range }}.
      </p>
    </div>

    <p v-if="reportRequest.loading" class="mt-5 text-sm text-ink-gray-5">Loading revenue…</p>

    <template v-else>
      <ReportStats class="mt-5" :stats="stats" :compare="compare" />

      <section class="mt-6 rounded-5 border border-outline-gray-1 p-4">
        <h2 class="text-lg-semibold text-ink-gray-8">Revenue over time</h2>
        <div class="h-72">
          <AreaChart :data="months" x="label" :y="['revenue']" />
        </div>
      </section>

      <div class="mt-6 grid gap-6 lg:grid-cols-2">
        <section class="rounded-5 border border-outline-gray-1 p-4">
          <h2 class="text-lg-semibold text-ink-gray-8">Discounts given</h2>
          <div class="h-56">
            <BarChart :data="months" x="label" :y="['discounts']" />
          </div>
        </section>
        <section class="rounded-5 border border-outline-gray-1 p-4">
          <h2 class="text-lg-semibold text-ink-gray-8">Average order value</h2>
          <div class="h-56">
            <BarChart :data="months" x="label" :y="['aov']" />
          </div>
        </section>
      </div>

      <section class="mt-6 rounded-5 border border-outline-gray-1">
        <h2 class="px-4 py-3 text-lg-semibold text-ink-gray-8">By month</h2>
        <div class="overflow-x-auto px-2 pb-2">
          <List
            class="min-w-[46rem]"
            :columns="['6rem', '8rem', '6rem', '7rem', '7rem', '8rem']"
            :row-height="Math.max(ia.density, 44)"
          >
            <ListHeader>
              <ListHeaderCell>Month</ListHeaderCell>
              <ListHeaderCell>Revenue</ListHeaderCell>
              <ListHeaderCell>Orders</ListHeaderCell>
              <ListHeaderCell>Discounts</ListHeaderCell>
              <ListHeaderCell>Refunds</ListHeaderCell>
              <ListHeaderCell>Net</ListHeaderCell>
            </ListHeader>
            <ListRows :items="rows" row-key="month" v-slot="{ item }">
              <ListRow :value="item.month">
                <ListCell><span class="text-base text-ink-gray-8">{{ item.label }}</span></ListCell>
                <ListCell><span class="text-base text-ink-gray-7 tabular-nums">{{ money(item.revenue) }}</span></ListCell>
                <ListCell><span class="text-base text-ink-gray-6 tabular-nums">{{ item.orders }}</span></ListCell>
                <ListCell><span class="text-base text-ink-gray-6 tabular-nums">{{ money(item.discounts) }}</span></ListCell>
                <ListCell><span class="text-base text-ink-red-6 tabular-nums">{{ money(item.refunds) }}</span></ListCell>
                <ListCell><span class="text-base text-ink-gray-8 tabular-nums">{{ money(item.net) }}</span></ListCell>
              </ListRow>
            </ListRows>
          </List>
        </div>
      </section>
    </template>
  </PageBody>
</template>

