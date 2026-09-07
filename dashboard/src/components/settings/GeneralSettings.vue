<script setup>
/**
 * The store's own contact details, which this screen writes, beside the company record, which it
 * only reads. Company, currency, tax id and financial year belong to the books — this shows what
 * they say and hands off to Desk for the rest.
 */
import { computed, watch } from 'vue'
import {
  Button,
  LoadingText,
  SettingsBody,
  SettingsHeader,
  SettingsRow,
  TextInput,
  toast,
} from 'frappe-ui'
import { useAdminAction, useAdminRead } from '../../data/api'
import { useSettingsDraft } from '../../data/useSettingsDraft'

const props = defineProps({
  // Opening the dialog should fetch; switching away and back should not.
  active: { type: Boolean, default: false },
})

const STORE_FIELDS = ['store_name', 'contact_email', 'contact_phone', 'working_hours']

const store = useAdminRead('settings.get_store_settings', { immediate: false })
const company = useAdminRead('settings.get_company_profile', { immediate: false })
const save = useAdminAction('settings.save_store_settings')

const { values, changes, changed, adopt } = useSettingsDraft()

function pickStoreFields(record) {
  return Object.fromEntries(STORE_FIELDS.map((fieldname) => [fieldname, record[fieldname]]))
}

watch(
  () => store.data,
  (data) => data && adopt(pickStoreFields(data)),
  { immediate: true },
)

watch(
  () => props.active,
  (isActive) => {
    if (!isActive) return
    if (!store.isFinished) store.reload()
    if (!company.isFinished) company.reload()
  },
  { immediate: true },
)

async function submit() {
  const saved = await save.submit({ ...changes.value })
  if (save.error) return

  adopt(pickStoreFields(saved))
  toast.success('Store details saved')
}

// This site's own Desk, on this site's own origin — the dashboard and the books are one install.
const companyLink = computed(() =>
  company.data ? `/app/company/${encodeURIComponent(company.data.name)}` : '',
)
</script>

<template>
  <SettingsHeader title="General" description="How your storefront names itself, and how customers reach you.">
    <template #actions>
      <Button
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
    <LoadingText v-if="store.loading && !store.data" class="py-10" />

    <div v-else class="divide-y divide-outline-gray-1">
      <SettingsRow title="Store name" description="Shown across your storefront and in the browser tab.">
        <TextInput v-model="values.store_name" class="w-72" />
      </SettingsRow>
      <SettingsRow title="Contact email" description="Where customers reach you, and who order mail comes from.">
        <TextInput v-model="values.contact_email" class="w-72" type="email" />
      </SettingsRow>
      <SettingsRow title="Contact phone">
        <TextInput v-model="values.contact_phone" class="w-72" />
      </SettingsRow>
      <SettingsRow title="Working hours" description="Shown alongside your contact details.">
        <TextInput v-model="values.working_hours" class="w-72" />
      </SettingsRow>
    </div>

    <!-- Read-only on purpose: these are accounting facts, and changing them here would mean
         changing them in one place and not the other. -->
    <div class="mt-8 border-t border-outline-gray-1 pt-6">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h3 class="text-base font-medium text-ink-gray-8">Company</h3>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            Your books own this record. Change it there and it updates here.
          </p>
        </div>
        <Button
          v-if="company.data"
          label="Open company record"
          icon-right="lucide-external-link"
          :link="companyLink"
        />
      </div>

      <!-- Gated on isFinished, not on data: an in-flight request has no data either, and saying
           there is no company while still asking for one states the opposite of the truth. -->
      <LoadingText v-if="!company.isFinished" class="mt-4" />

      <p v-else-if="!company.data" class="mt-4 text-base text-ink-gray-5">
        No company is set for this store yet, so there is nothing to show. Set one on Lifestyle
        Settings in Desk and orders will book against it.
      </p>

      <div v-else class="mt-2 divide-y divide-outline-gray-1">
        <SettingsRow title="Registered name">
          <p class="text-base text-ink-gray-7">{{ company.data.name }}</p>
        </SettingsRow>
        <SettingsRow title="Registered address">
          <p class="max-w-xs whitespace-pre-line text-right text-p-base text-ink-gray-7">
            {{ company.data.address ?? 'No address on the company record' }}
          </p>
        </SettingsRow>
        <SettingsRow title="Currency">
          <p class="text-base text-ink-gray-7">
            {{ company.data.currency }}<span v-if="company.data.country"> · {{ company.data.country }}</span>
          </p>
        </SettingsRow>
        <SettingsRow
          title="Tax ID"
          description="Printed on invoices. Tax rates themselves are set by your books, not here."
        >
          <p class="text-base text-ink-gray-7 tabular-nums">
            {{ company.data.tax_id ?? 'Not set' }}
          </p>
        </SettingsRow>
        <SettingsRow title="Financial year">
          <p class="text-base text-ink-gray-7 tabular-nums">
            {{ company.data.fiscal_year ?? 'None covers today' }}
          </p>
        </SettingsRow>
      </div>
    </div>
  </SettingsBody>
</template>
