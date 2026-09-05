<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Avatar, Button, toast } from 'frappe-ui'
import { List, ListCell, ListRow, ListRows } from 'frappe-ui/list'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAdminRead } from '../data/api'
import { erpnextLink } from '../data/erpnext'
import { longDate, money, shortDate } from '../data/format'
import { ia } from '../ia/store'

const route = useRoute()

const customerRequest = useAdminRead('customers.get_customer', {
  params: () => ({ customer: route.params.id }),
  refetch: true,
})

const customer = computed(() => customerRequest.data)
const theirOrders = computed(() => customer.value?.recent_orders ?? [])
</script>

<template>
  <p v-if="customerRequest.loading" class="p-5 text-sm text-ink-gray-5">Loading customer…</p>

  <template v-else-if="customer">
    <AppPageHeader
      :title="customer.name"
      back-to="/customers"
      :breadcrumbs="[{ label: 'Customers', route: '/customers' }, { label: customer.name }]"
    >
      <template #actions>
        <!-- A Desk deep link is not a phone action, and two labelled buttons
             leave the breadcrumb nothing — so it steps aside below sm. -->
        <Button
          class="hidden sm:inline-flex"
          label="View in ERP"
          icon-right="lucide-external-link"
          :link="erpnextLink('Customer', customer.id)"
        />
        <!-- No email address on this customer record has anything wired to send through yet — kept
             inert rather than pointed at nothing. -->
        <Button
          label="Email customer"
          icon-left="lucide-mail"
          variant="solid"
          theme="gray"
          @click="() => toast.info('Emailing a customer isn\'t wired up yet')"
        />
      </template>
    </AppPageHeader>

    <PageBody width="wide">
      <div class="flex items-center gap-3">
        <Avatar :label="customer.name" size="2xl" />
        <div>
          <p class="text-xl text-ink-gray-9">{{ customer.name }}</p>
          <p class="mt-1 text-sm text-ink-gray-5">
            {{ customer.email ?? 'No email on file' }} · {{ customer.city ?? 'No city on file' }} · since
            {{ longDate(customer.since) }}
          </p>
          <p class="mt-1 text-sm text-ink-gray-4">
            Contact and billing details are kept on the customer record.
          </p>
        </div>
      </div>

      <section
        class="mt-6 grid grid-cols-2 rounded-5 border border-outline-gray-1 sm:grid-cols-3 sm:divide-x sm:divide-outline-gray-2"
      >
        <div class="px-4 py-3.5">
          <p class="text-sm text-ink-gray-5">Orders</p>
          <p class="mt-1 text-2xl text-ink-gray-9 tabular-nums">{{ customer.orders }}</p>
        </div>
        <div class="px-4 py-3.5">
          <p class="text-sm text-ink-gray-5">Lifetime spend</p>
          <p class="mt-1 text-2xl text-ink-gray-9 tabular-nums">{{ money(customer.spend) }}</p>
        </div>
        <div class="px-4 py-3.5">
          <p class="text-sm text-ink-gray-5">Average order</p>
          <p class="mt-1 text-2xl text-ink-gray-9 tabular-nums">
            {{ customer.orders ? money(customer.average_order) : '—' }}
          </p>
        </div>
      </section>

      <section class="mt-8">
        <div class="flex items-baseline justify-between">
          <h2 class="text-lg-semibold text-ink-gray-8">Recent orders</h2>
          <span class="text-sm text-ink-gray-5">{{ customer.orders }} orders all time</span>
        </div>
        <div class="mt-1 overflow-x-auto">
          <List class="min-w-[34rem]" :row-height="Math.max(ia.density, 48)">
            <ListRows :items="theirOrders" row-key="name" v-slot="{ item }">
              <ListRow :to="`/orders/${item.name}`" :value="item.name">
                <ListCell>
                  <span class="text-base text-ink-gray-4 tabular-nums">{{ item.name }}</span>
                </ListCell>
                <ListCell>
                  <div class="min-w-0">
                    <p class="truncate text-base text-ink-gray-8">
                      {{ item.item_count }} item{{ item.item_count > 1 ? 's' : '' }} · {{ money(item.total) }}
                    </p>
                    <p class="mt-1 text-sm text-ink-gray-5">{{ shortDate(item.placed_on) }}</p>
                  </div>
                </ListCell>
                <ListCell>
                  <div class="flex items-center gap-3">
                    <StatusBadge :status="item.payment_state.key" :label="item.payment_state.label" />
                    <StatusBadge :status="item.state.key" :label="item.state.label" />
                    <span class="lucide-chevron-right size-4 text-ink-gray-4" aria-hidden="true" />
                  </div>
                </ListCell>
              </ListRow>
            </ListRows>
          </List>
        </div>
      </section>
    </PageBody>
  </template>
</template>

