<script setup>
/**
 * The analytics services this store reports to.
 *
 * Each is the same shape — a switch, public ids, and one credential the server keeps — so they are
 * described as docfields and rendered by the same row renderer the provider screens use, rather
 * than hand-built a third time.
 */
import { computed, watch } from 'vue'
import { Button, LoadingText, SettingsBody, SettingsHeader, toast } from 'frappe-ui'
import SettingsFieldRows from './SettingsFieldRows.vue'
import { useAdminAction, useAdminRead } from '../../data/api'
import { useSettingsDraft } from '../../data/useSettingsDraft'
import { errorMessage } from '../../data/errors'

const props = defineProps({
  active: { type: Boolean, default: false },
})

const PLAIN_FIELDS = [
  'enable_first_party',
  'enable_ga4',
  'ga4_measurement_id',
  'ga4_property_id',
  'enable_facebook',
  'fb_pixel_id',
]

const SECRET_FIELDS = ['ga4_service_account_json', 'fb_access_token']

const analytics = useAdminRead('analytics.get_analytics_settings', { immediate: false })
const save = useAdminAction('analytics.save_analytics_settings')

const { values, changes, changed, adopt, set } = useSettingsDraft()

// A secret is never returned, so it starts blank on every load and blank means "keep it".
function blankSecrets() {
  return Object.fromEntries(SECRET_FIELDS.map((fieldname) => [fieldname, '']))
}

function adoptSettings(data) {
  adopt({
    ...Object.fromEntries(PLAIN_FIELDS.map((fieldname) => [fieldname, data[fieldname]])),
    ...blankSecrets(),
  })
}

watch(
  () => analytics.data,
  (data) => data && adoptSettings(data),
  { immediate: true },
)

watch(
  () => props.active,
  (isActive) => isActive && !analytics.isFinished && analytics.reload(),
  { immediate: true },
)

const groups = computed(() => [
  {
    label: 'This store',
    fields: [
      {
        fieldname: 'enable_first_party',
        label: 'Track visits in Commera',
        fieldtype: 'Check',
        description: 'Powers the Storefront report. Nothing leaves this site.',
      },
    ],
  },
  {
    label: 'Google Analytics 4',
    fields: [
      { fieldname: 'enable_ga4', label: 'Send events to GA4', fieldtype: 'Check' },
      {
        fieldname: 'ga4_measurement_id',
        label: 'Measurement ID',
        fieldtype: 'Data',
        description: 'Starts with G-. In GA4 it is under Admin, Data streams.',
      },
      {
        fieldname: 'ga4_property_id',
        label: 'Property ID',
        fieldtype: 'Data',
        description: 'The numeric property, used to read reports back out of GA4.',
      },
      {
        fieldname: 'ga4_service_account_json',
        label: 'Service account JSON',
        fieldtype: 'Data',
        is_secret: true,
        is_set: Boolean(analytics.data?.ga4_service_account_json_is_set),
      },
    ],
  },
  {
    label: 'Meta',
    fields: [
      { fieldname: 'enable_facebook', label: 'Send events to Meta', fieldtype: 'Check' },
      { fieldname: 'fb_pixel_id', label: 'Pixel ID', fieldtype: 'Data' },
      {
        fieldname: 'fb_access_token',
        label: 'Access token',
        fieldtype: 'Data',
        is_secret: true,
        is_set: Boolean(analytics.data?.fb_access_token_is_set),
      },
    ],
  },
])

async function submit() {
  const saved = await save.submit({ ...changes.value })
  if (save.error) return

  adoptSettings(saved)
  toast.success('Analytics saved')
}
</script>

<template>
  <SettingsHeader
    title="Apps and channels"
    description="The analytics and marketing services this store reports to."
  >
    <template #actions>
      <Button
        v-if="analytics.data"
        label="Save"
        variant="solid"
        theme="gray"
        :loading="save.loading"
        :disabled="!changed"
        @click="submit"
      />
    </template>
  </SettingsHeader>

  <SettingsBody>
    <!-- These are site-wide credentials, so the server only opens them to a System Manager. A
         refusal must read as "not yours to change", never as "nothing is connected". -->
    <p v-if="analytics.error" class="py-6 text-base text-ink-gray-5">
      {{ errorMessage(analytics.error, 'Only a System Manager can see these credentials.') }}
    </p>

    <LoadingText v-else-if="!analytics.data" class="py-10" />

    <div v-else class="divide-y divide-outline-gray-1">
      <SettingsFieldRows :groups="groups" :values="values" @update="set" />
    </div>
  </SettingsBody>
</template>
