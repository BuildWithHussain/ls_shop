<script setup>
/**
 * The list of providers a store can turn on, and the screen behind each one.
 *
 * Payments and shipping are the same screen twice: the backend engine behind both
 * registries is provider-agnostic, so this panel only needs telling which store to read.
 * Adding a third kind of integration means a registry on the server and one more instance
 * of this component — nothing else.
 */
import { computed, ref, watch } from 'vue'
import { Badge, Button, SettingsBody, SettingsHeader, toast } from 'frappe-ui'
import IntegrationCard from './IntegrationCard.vue'
import IntegrationConfig from './IntegrationConfig.vue'

const props = defineProps({
  store: { type: Object, required: true },
  title: { type: String, required: true },
  description: { type: String, required: true },
  // Opening the dialog should fetch; switching away and back should not.
  active: { type: Boolean, default: false },
})

const configuring = ref(null)
const current = computed(
  () => props.store.cards.value.find((card) => card.slug === configuring.value) ?? null,
)

watch(() => props.active, (isActive) => isActive && props.store.loadOnce(), { immediate: true })

async function toggle(card, enabled) {
  // Enabling with a required field still blank is refused by the server, which names the
  // field. Nothing is done here to pre-empt it: one rule, on the server, for both screens.
  const saved = await props.store.save(card.slug, enabled, {})
  if (!saved) return

  if (saved.enabled) toast.success(`${saved.label} is on`)
  else toast.success(`${saved.label} is off`)
}

async function saveCurrent({ enabled, values }) {
  const saved = await props.store.save(current.value.slug, enabled, values)
  if (!saved) return

  configuring.value = null
  toast.success(`${saved.label} saved`)
}
</script>

<template>
  <template v-if="!current">
    <SettingsHeader :title="title" :description="description">
      <template #actions>
        <Badge
          v-if="store.incomplete.value.length"
          :label="`${store.incomplete.value.length} ${store.incomplete.value.length === 1 ? 'needs' : 'need'} keys`"
          theme="orange"
          variant="subtle"
        />
      </template>
    </SettingsHeader>
    <SettingsBody>
      <!-- A refused read must not read as "this store has no providers". -->
      <div v-if="store.loadError.value" class="py-6 text-base text-ink-gray-5">
        These could not be loaded.
        <Button label="Try again" variant="ghost" @click="store.load()" />
      </div>
      <div v-else-if="store.loading.value && !store.cards.value.length" class="py-6 text-base text-ink-gray-5">
        Loading…
      </div>
      <div v-else class="divide-y divide-outline-gray-1">
        <IntegrationCard
          v-for="card in store.cards.value"
          :key="card.slug"
          :card="card"
          :busy="store.loading.value"
          @configure="configuring = $event"
          @toggle="toggle(card, $event)"
        />
      </div>
    </SettingsBody>
  </template>

  <IntegrationConfig
    v-else
    :card="current"
    :saving="store.loading.value"
    @back="configuring = null"
    @save="saveCurrent"
  />
</template>
