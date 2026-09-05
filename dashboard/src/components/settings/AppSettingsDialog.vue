<script setup>
import { computed, ref, watch } from 'vue'
import {
  Badge,
  Button,
  Select,
  SettingsBody,
  SettingsContent,
  SettingsDialog,
  SettingsHeader,
  SettingsNavGroup,
  SettingsNavItem,
  SettingsPanel,
  SettingsRow,
  SettingsSidebar,
  Switch,
  dialog,
  toast,
} from 'frappe-ui'
// ThemeSwitcher moved out of the frappe-ui root in beta.56 (#1094); the parked copy under
// /experimental keeps the same props, so this is an import path change only.
import { ThemeSwitcher } from 'frappe-ui/experimental'
import BrandMark from './BrandMark.vue'
import IntegrationsPanel from './IntegrationsPanel.vue'
import { paymentIntegrations, shippingIntegrations } from '../../data/integrations'
import { appIntegrations, locations } from '../../data/mock'
import { company, erpnextLink } from '../../data/erpnext'
import { settings } from '../../ia/settings'

const taxInclusive = ref(true)
const weightUnit = ref('g')
const notifyOrders = ref(true)
const notifyLowStock = ref(true)
const notifyPayouts = ref(false)

// The counts beside the sidebar entries are the server's answer, not a local tally, so
// they cannot claim a provider is live when the site says otherwise.
const connectedCount = paymentIntegrations.connectedCount
const shippingConnected = shippingIntegrations.connectedCount
const appsConnected = computed(() => appIntegrations.filter((a) => a.connected).length)

// Both registries load when the dialog opens, not when their tab is first shown: the
// counts sit in the sidebar from the start, and an unread registry counts zero, which
// reads as "nothing is connected" rather than "not looked yet".
watch(
  () => settings.open,
  (isOpen) => {
    if (!isOpen) return
    paymentIntegrations.loadOnce()
    shippingIntegrations.loadOnce()
  },
  { immediate: true },
)

const appsByCategory = computed(() => {
  const groups = new Map()
  for (const app of appIntegrations) {
    if (!groups.has(app.category)) groups.set(app.category, [])
    groups.get(app.category).push(app)
  }
  return [...groups].map(([category, items]) => ({ category, items }))
})

const users = [
  ['Aarti Mehta', 'aarti@kirana.co', 'Owner', 'Everything'],
  ['Devansh Rao', 'devansh@kirana.co', 'Fulfilment', 'Orders, stock'],
  ['Meera Iyer', 'meera@kirana.co', 'Catalogue', 'Products, collections'],
]

function inviteUser() {
  dialog.prompt({
    title: 'Invite a user',
    message: 'They get an email with a sign-in link. Roles can be changed later.',
    fields: [
      { name: 'email', label: 'Email', required: true },
      {
        name: 'role',
        label: 'Role',
        type: 'select',
        options: ['Owner', 'Fulfilment', 'Catalogue', 'Read only'],
      },
    ],
    onConfirm: ({ values }) => toast.success(`Invite sent to ${values.email}`),
  })
}
</script>

<template>
  <SettingsDialog v-model:open="settings.open" v-model:tab="settings.tab" :unmount-on-hide="false">
    <template #title>Commera settings</template>

    <SettingsSidebar>
      <SettingsNavGroup>
        <SettingsNavItem value="general">
          <template #prefix><span class="lucide-store size-4" aria-hidden="true" /></template>
          General
        </SettingsNavItem>
        <SettingsNavItem value="locations">
          <template #prefix><span class="lucide-map-pin size-4" aria-hidden="true" /></template>
          Locations
        </SettingsNavItem>
        <SettingsNavItem value="users">
          <template #prefix><span class="lucide-users size-4" aria-hidden="true" /></template>
          Users
        </SettingsNavItem>
        <SettingsNavItem value="appearance">
          <template #prefix><span class="lucide-sun-moon size-4" aria-hidden="true" /></template>
          Appearance
        </SettingsNavItem>
      </SettingsNavGroup>

      <SettingsNavGroup label="Selling">
        <SettingsNavItem value="payments">
          <template #prefix><span class="lucide-credit-card size-4" aria-hidden="true" /></template>
          Payments
          <template #suffix>
            <span class="text-sm text-ink-gray-5 tabular-nums">{{ connectedCount }}</span>
          </template>
        </SettingsNavItem>
        <SettingsNavItem value="shipping">
          <template #prefix><span class="lucide-truck size-4" aria-hidden="true" /></template>
          Shipping
          <template #suffix>
            <span class="text-sm text-ink-gray-5 tabular-nums">{{ shippingConnected }}</span>
          </template>
        </SettingsNavItem>
        <SettingsNavItem value="taxes">
          <template #prefix><span class="lucide-receipt size-4" aria-hidden="true" /></template>
          Taxes
        </SettingsNavItem>
      </SettingsNavGroup>

      <SettingsNavGroup label="Connections">
        <SettingsNavItem value="apps">
          <template #prefix><span class="lucide-plug size-4" aria-hidden="true" /></template>
          Apps and channels
          <template #suffix>
            <span class="text-sm text-ink-gray-5 tabular-nums">{{ appsConnected }}</span>
          </template>
        </SettingsNavItem>
        <SettingsNavItem value="notifications">
          <template #prefix><span class="lucide-bell size-4" aria-hidden="true" /></template>
          Notifications
        </SettingsNavItem>
      </SettingsNavGroup>
    </SettingsSidebar>

    <SettingsContent>
      <!-- Company, tax and accounting records are owned by the books, not by
           Commera. Shown read-only, with one way out to the full record. -->
      <SettingsPanel value="general">
        <SettingsHeader title="General" description="Your company record. Change it in the books and it updates here.">
          <template #actions>
            <Button
              label="Open company record"
              icon-right="lucide-external-link"
              :link="erpnextLink('Company', company.name)"
            />
          </template>
        </SettingsHeader>
        <SettingsBody>
          <div class="divide-y divide-outline-gray-1">
            <SettingsRow title="Store name" description="Taken from the company name. It is what customers see on the storefront.">
              <p class="text-base text-ink-gray-7">{{ company.name }}</p>
            </SettingsRow>
            <SettingsRow title="Registered address">
              <p class="max-w-xs text-right text-p-base text-ink-gray-7">{{ company.address }}</p>
            </SettingsRow>
            <SettingsRow title="Contact email" description="Order confirmations are sent from this address.">
              <p class="text-base text-ink-gray-7">{{ company.email }}</p>
            </SettingsRow>
            <SettingsRow title="Phone">
              <p class="text-base text-ink-gray-7">{{ company.phone }}</p>
            </SettingsRow>
            <SettingsRow title="Currency">
              <p class="text-base text-ink-gray-7">{{ company.currency }} · {{ company.country }}</p>
            </SettingsRow>
            <SettingsRow title="Financial year">
              <p class="text-base text-ink-gray-7 tabular-nums">{{ company.fiscalYear }}</p>
            </SettingsRow>
            <SettingsRow title="Weight unit" description="Set here, and used for shipping rates.">
              <Select
                v-model="weightUnit"
                class="w-64"
                :options="[
                  { label: 'Grams', value: 'g' },
                  { label: 'Kilograms', value: 'kg' },
                ]"
              />
            </SettingsRow>
          </div>
        </SettingsBody>
      </SettingsPanel>

      <SettingsPanel value="locations">
        <SettingsHeader title="Locations" description="Stock is tracked per location.">
          <template #actions>
            <Button label="Add location" icon-left="lucide-plus" @click="toast.info('New location')" />
          </template>
        </SettingsHeader>
        <SettingsBody>
          <div class="divide-y divide-outline-gray-1">
            <div v-for="location in locations" :key="location.id" class="flex items-center justify-between py-3">
              <div>
                <p class="text-base text-ink-gray-8">{{ location.name }}</p>
                <p class="mt-1 text-sm text-ink-gray-5">{{ location.code }} · fulfils online orders</p>
              </div>
              <Button label="Edit" variant="ghost" />
            </div>
          </div>
        </SettingsBody>
      </SettingsPanel>

      <SettingsPanel value="users">
        <SettingsHeader title="Users" description="Who can sign in, and what they can reach.">
          <template #actions>
            <Button
              label="Invite user"
              icon-left="lucide-user-plus"
              variant="solid"
              theme="gray"
              @click="inviteUser"
            />
          </template>
        </SettingsHeader>
        <SettingsBody>
          <div class="divide-y divide-outline-gray-1">
            <div v-for="person in users" :key="person[1]" class="flex items-center justify-between py-3">
              <div class="min-w-0">
                <p class="truncate text-base text-ink-gray-8">{{ person[0] }}</p>
                <p class="mt-1 truncate text-sm text-ink-gray-5">
                  {{ person[1] }} · {{ person[2] }} · {{ person[3] }}
                </p>
              </div>
              <Button label="Permissions" variant="ghost" />
            </div>
          </div>
        </SettingsBody>
      </SettingsPanel>

      <!-- Payments: several gateways can run side by side, each with its own
           keys and environment. Only the checkout default is exclusive. -->
      <!-- Light and dark are a property of this browser, not of the store, so
           Appearance sits with the other personal settings and nowhere near
           the storefront theme. -->
      <SettingsPanel value="appearance">
        <SettingsHeader title="Appearance" description="How Commera looks on this device." />
        <SettingsBody>
          <ThemeSwitcher name="Commera" label="" description="" />
          <p class="mt-3 text-p-sm text-ink-gray-5">
            Saved on this device. The storefront's own look is set under Storefront → Theme.
          </p>
        </SettingsBody>
      </SettingsPanel>

      <SettingsPanel value="payments">
        <IntegrationsPanel
          :store="paymentIntegrations"
          :active="settings.tab === 'payments'"
          title="Payments"
          description="Turn on as many providers as you like. Each keeps its own keys."
        />
      </SettingsPanel>

      <SettingsPanel value="shipping">
        <IntegrationsPanel
          :store="shippingIntegrations"
          :active="settings.tab === 'shipping'"
          title="Shipping"
          description="Carriers this store books with. Each quotes its own rates at checkout."
        />
      </SettingsPanel>

      <SettingsPanel value="taxes">
        <SettingsHeader title="Taxes" description="How tax is calculated and displayed." />
        <SettingsBody>
          <div class="divide-y divide-outline-gray-1">
            <SettingsRow title="Prices include tax" description="Shoppers see one number; tax is backed out on the invoice.">
              <Switch v-model="taxInclusive" size="sm" />
            </SettingsRow>
            <SettingsRow title="GSTIN" description="From the company record.">
              <p class="text-base text-ink-gray-7 tabular-nums">{{ company.gstin }}</p>
            </SettingsRow>
            <SettingsRow title="Default GST rate">
              <Select
                model-value="5"
                class="w-64"
                :options="[
                  { label: '0% — exempt', value: '0' },
                  { label: '5%', value: '5' },
                  { label: '12%', value: '12' },
                  { label: '18%', value: '18' },
                ]"
              />
            </SettingsRow>
          </div>
        </SettingsBody>
      </SettingsPanel>

      <SettingsPanel value="apps">
        <SettingsHeader
          title="Apps and channels"
          description="Shipping, analytics and marketing services this store talks to."
        />
        <SettingsBody>
          <div v-for="group in appsByCategory" :key="group.category" class="pb-6 pt-1">
            <h3 class="text-sm text-ink-gray-5">{{ group.category }}</h3>
            <div class="mt-1 divide-y divide-outline-gray-1">
              <div v-for="app in group.items" :key="app.id" class="flex items-center gap-3 py-3">
                <BrandMark :mark="app.mark" :brand="app.brand" size="size-8" />
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <p class="truncate text-base text-ink-gray-8">{{ app.name }}</p>
                    <Badge v-if="app.connected" label="Connected" theme="green" variant="subtle" />
                  </div>
                  <p class="mt-1 truncate text-sm text-ink-gray-5">{{ app.blurb }}</p>
                </div>
                <Button :label="app.connected ? 'Manage' : 'Connect'" />
              </div>
            </div>
          </div>
        </SettingsBody>
      </SettingsPanel>

      <SettingsPanel value="notifications">
        <SettingsHeader title="Notifications" description="What Commera tells you about, and where." />
        <SettingsBody>
          <div class="divide-y divide-outline-gray-1">
            <SettingsRow title="New orders" description="Email the moment an order is paid.">
              <Switch v-model="notifyOrders" size="sm" />
            </SettingsRow>
            <SettingsRow title="Low stock" description="When a variant drops to five units or fewer.">
              <Switch v-model="notifyLowStock" size="sm" />
            </SettingsRow>
            <SettingsRow title="Payouts" description="When a gateway settles money to your account.">
              <Switch v-model="notifyPayouts" size="sm" />
            </SettingsRow>
          </div>
        </SettingsBody>
      </SettingsPanel>
    </SettingsContent>
  </SettingsDialog>
</template>

