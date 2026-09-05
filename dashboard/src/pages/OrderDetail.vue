<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Avatar, Badge, Button, Dropdown, ScrollArea, toast } from 'frappe-ui'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import StatusBadge from '../components/StatusBadge.vue'
import OrderProgress from '../components/OrderProgress.vue'
import Thumb from '../components/Thumb.vue'
import { useAdminRead, useAdminAction } from '../data/api'
import { erpnextLink } from '../data/erpnext'
import { longDate, money } from '../data/format'

const route = useRoute()

const orderRequest = useAdminRead('orders.get_order', {
  params: () => ({ sales_order: route.params.id }),
  refetch: true,
})
const order = computed(() => orderRequest.data)

watch(
  () => route.params.id,
  () => orderRequest.reload(),
)

const erpLink = computed(() => (order.value ? erpnextLink('Sales Order', order.value.name) : null))

// Refund and admin-initiated cancel have no wired backend — see
// docs/commera-open-questions.md, "Order Detail — Refund and Cancel order".
const moreActions = [
  { label: 'Duplicate', icon: 'lucide-copy', onClick: () => toast.info('Duplicate is coming soon') },
  { label: 'Print invoice', icon: 'lucide-printer', onClick: () => toast.info('Printing is coming soon') },
  {
    label: 'Refund',
    icon: 'lucide-rotate-ccw',
    onClick: () => toast.info('Refunds aren\'t available from the dashboard yet'),
  },
  {
    label: 'Cancel order',
    icon: 'lucide-x-circle',
    onClick: () => toast.info('Cancelling from the dashboard isn\'t available yet'),
  },
]

const fulfilAction = useAdminAction('orders.fulfil_order')

async function fulfil() {
  await fulfilAction.submit({ sales_order: order.value.name })
  if (fulfilAction.error) return
  toast.success('Fulfilment created')
  orderRequest.reload()
}
</script>

<template>
  <template v-if="order">
    <AppPageHeader
      :title="order.name"
      back-to="/orders"
      :breadcrumbs="[{ label: 'Orders', route: '/orders' }, { label: order.name }]"
    >
      <template #actions>
        <Button label="View in ERP" icon-right="lucide-external-link" :link="erpLink" />
        <Dropdown :options="moreActions">
          <Button icon="lucide-ellipsis" label="More actions" />
        </Dropdown>
        <Button
          label="Fulfil items"
          icon-left="lucide-truck"
          variant="solid"
          theme="gray"
          :disabled="!order.can_fulfil"
          @click="fulfil"
        />
      </template>
    </AppPageHeader>

    <!-- Two panes, each with its own scroll: the order is worked down the left,
         and who it is for stays put on the right. -->
    <div class="flex min-h-0 flex-1 overflow-hidden">
      <ScrollArea class="min-w-0 flex-1">
        <PageBody width="narrow">
      <div class="flex flex-wrap items-center gap-2">
        <StatusBadge
          v-if="order.payment_state.key !== 'paid'"
          :status="order.payment_state.key"
          :label="order.payment_state.label"
        />
        <StatusBadge v-if="order.state.key === 'cancelled'" :status="order.state.key" :label="order.state.label" />
        <span class="text-sm text-ink-gray-5">{{ longDate(order.placed_on) }}</span>
      </div>

      <!-- Where the order has reached, read left to right. -->
      <OrderProgress class="mt-6" :progress="order.progress" />

      <!-- The lines and what they add up to are one thing, so they are one
           card: the total is the last row of the same table. -->
      <div class="mt-5 space-y-6">
        <section class="rounded-5 border border-outline-gray-1">
            <div class="flex items-center justify-between px-4 py-3">
              <h2 class="text-lg-semibold text-ink-gray-8">Items</h2>
              <div class="flex items-center gap-2">
                <span class="text-sm text-ink-gray-5">
                  {{ order.items.length }} {{ order.items.length === 1 ? 'line' : 'lines' }}
                </span>
                <StatusBadge :status="order.state.key" :label="order.state.label" />
              </div>
            </div>

            <div class="divide-y divide-outline-gray-1 border-t border-outline-gray-1">
              <div v-for="item in order.items" :key="item.item_code" class="flex items-center gap-3 px-4 py-3">
                <Thumb :image="item.image" size="size-10" />
                <div class="min-w-0 flex-1">
                  <p class="truncate text-base text-ink-gray-8">{{ item.title }}</p>
                  <p class="mt-1 truncate text-sm text-ink-gray-5">
                    <span v-if="item.size">{{ item.size }} · </span>{{ item.item_code }}
                  </p>
                </div>
                <span class="w-28 text-right text-base text-ink-gray-5 tabular-nums">
                  {{ money(item.rate) }} × {{ item.qty }}
                </span>
                <span class="w-24 text-right text-base text-ink-gray-8 tabular-nums">
                  {{ money(item.amount) }}
                </span>
              </div>
            </div>

            <div class="space-y-1.5 border-t border-outline-gray-1 px-4 py-3">
              <div class="flex justify-between text-base text-ink-gray-6">
                <span>Subtotal</span><span class="tabular-nums">{{ money(order.net_total) }}</span>
              </div>
              <div class="flex justify-between text-base text-ink-gray-6">
                <span>Shipping</span>
                <span class="tabular-nums">{{ order.shipping ? money(order.shipping) : 'Free' }}</span>
              </div>
              <div v-if="order.cod_charge" class="flex justify-between text-base text-ink-gray-6">
                <span>Cash on delivery charge</span><span class="tabular-nums">{{ money(order.cod_charge) }}</span>
              </div>
              <div class="flex justify-between text-base text-ink-gray-6">
                <span>Tax</span><span class="tabular-nums">{{ money(order.tax) }}</span>
              </div>
              <div class="flex justify-between pt-1 text-base-semibold text-ink-gray-9">
                <span>Total</span><span class="tabular-nums">{{ money(order.grand_total) }}</span>
              </div>
            </div>
        </section>
      </div>
        </PageBody>
      </ScrollArea>

      <aside class="hidden w-[19rem] shrink-0 flex-col border-l border-outline-gray-1 lg:flex">
        <ScrollArea class="min-h-0 flex-1">
          <div class="divide-y divide-outline-gray-1">
          <section class="px-4 py-4">
            <p class="text-sm text-ink-gray-5">Customer</p>
            <router-link :to="`/customers/${order.customer_id}`" class="mt-2 flex items-center gap-2.5">
              <Avatar :label="order.customer" size="md" />
              <div class="min-w-0">
                <p class="truncate text-base text-ink-gray-8">{{ order.customer }}</p>
                <p v-if="order.phone" class="truncate text-sm text-ink-gray-5">{{ order.phone }}</p>
              </div>
            </router-link>
            <p v-if="order.email" class="mt-3 truncate text-sm text-ink-blue-link">{{ order.email }}</p>
          </section>

          <section class="px-4 py-4">
            <p class="text-sm text-ink-gray-5">Shipping address</p>
            <p class="mt-1.5 whitespace-pre-line text-p-base text-ink-gray-7">
              {{ order.shipping_address || 'No shipping address on file.' }}
            </p>
          </section>

          <section class="px-4 py-4">
            <p class="text-sm text-ink-gray-5">Tags</p>
            <div class="mt-1.5 flex flex-wrap gap-1.5">
              <Badge v-for="tag in order.tags" :key="tag" :label="tag" variant="subtle" />
              <span v-if="!order.tags.length" class="text-sm text-ink-gray-5">None</span>
            </div>
          </section>

          <section class="px-4 py-4">
            <p class="text-sm text-ink-gray-5">Note</p>
            <!-- Sales Order carries no note/remarks field in this data model — always the empty
                 state rather than a control that can never do anything. -->
            <p class="mt-1.5 text-p-base text-ink-gray-4">No note on this order.</p>
          </section>
          </div>
        </ScrollArea>
      </aside>
    </div>
  </template>
</template>

