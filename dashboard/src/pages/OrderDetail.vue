<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Button, Dropdown, ScrollArea, toast } from 'frappe-ui'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import StatusBadge from '../components/StatusBadge.vue'
import OrderProgress from '../components/OrderProgress.vue'
import OrderCustomerPanel from '../components/OrderCustomerPanel.vue'
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
//
// "View in ERP" is here unconditionally rather than only below `sm`: the
// labelled button hides at `sm` (min-width: 640px) but a viewport-reactive
// menu would have to match that boundary exactly, and a fractional width in
// (639.98, 640) — reachable under browser zoom — would hide both copies and
// leave the action unreachable. The menu is the one route that always works;
// the labelled button is a desktop convenience on top of it.
const moreActions = [
  {
    label: 'View in ERP',
    icon: 'lucide-external-link',
    onClick: () => window.open(erpLink.value, '_blank', 'noopener'),
  },
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
        <!-- Three full label+icon buttons do not fit a phone header, so this one
             drops out below `sm` and the More menu's own entry carries it. -->
        <Button class="hidden sm:inline-flex" label="View in ERP" icon-right="lucide-external-link" :link="erpLink" />
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

        <!-- Below lg there is no right rail, so the same panel stacks under the
             items rather than the order losing its customer entirely. -->
        <section class="rounded-5 border border-outline-gray-1 lg:hidden">
          <OrderCustomerPanel :order="order" />
        </section>
      </div>
        </PageBody>
      </ScrollArea>

      <aside class="hidden w-[19rem] shrink-0 flex-col border-l border-outline-gray-1 lg:flex">
        <ScrollArea class="min-h-0 flex-1">
          <OrderCustomerPanel :order="order" />
        </ScrollArea>
      </aside>
    </div>
  </template>
</template>

