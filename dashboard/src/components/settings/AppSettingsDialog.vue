<script setup>
import { watch } from 'vue'
import {
  SettingsBody,
  SettingsContent,
  SettingsDialog,
  SettingsHeader,
  SettingsNavGroup,
  SettingsNavItem,
  SettingsPanel,
  SettingsSidebar,
} from 'frappe-ui'
// ThemeSwitcher moved out of the frappe-ui root in beta.56 (#1094); the parked copy under
// /experimental keeps the same props, so this is an import path change only.
import { ThemeSwitcher } from 'frappe-ui/experimental'
import AdvancedSettings from './AdvancedSettings.vue'
import AppsSettings from './AppsSettings.vue'
import GeneralSettings from './GeneralSettings.vue'
import IntegrationsPanel from './IntegrationsPanel.vue'
import LocationsSettings from './LocationsSettings.vue'
import { paymentIntegrations, shippingIntegrations } from '../../data/integrations'
import { settings } from '../../ia/settings'

// The counts beside the sidebar entries are the server's answer, not a local tally, so
// they cannot claim a provider is live when the site says otherwise.
const connectedCount = paymentIntegrations.connectedCount
const shippingConnected = shippingIntegrations.connectedCount

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
      </SettingsNavGroup>

      <SettingsNavGroup label="Connections">
        <SettingsNavItem value="apps">
          <template #prefix><span class="lucide-plug size-4" aria-hidden="true" /></template>
          Apps and channels
        </SettingsNavItem>
        <SettingsNavItem value="advanced">
          <template #prefix><span class="lucide-sliders-horizontal size-4" aria-hidden="true" /></template>
          Advanced
        </SettingsNavItem>
      </SettingsNavGroup>
    </SettingsSidebar>

    <SettingsContent>
      <SettingsPanel value="general">
        <GeneralSettings :active="settings.open && settings.tab === 'general'" />
      </SettingsPanel>

      <SettingsPanel value="locations">
        <LocationsSettings :active="settings.open && settings.tab === 'locations'" />
      </SettingsPanel>

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

      <!-- Payments: several gateways can run side by side, each with its own
           keys and environment. Only the checkout default is exclusive. -->
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

      <SettingsPanel value="apps">
        <AppsSettings :active="settings.open && settings.tab === 'apps'" />
      </SettingsPanel>

      <SettingsPanel value="advanced">
        <AdvancedSettings :active="settings.open && settings.tab === 'advanced'" />
      </SettingsPanel>
    </SettingsContent>
  </SettingsDialog>
</template>
