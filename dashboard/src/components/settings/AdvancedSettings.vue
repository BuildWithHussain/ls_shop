<script setup>
/**
 * The long tail of store setup: every remaining Lifestyle Settings field, grouped by the section it
 * sits under in Desk and rendered from that doctype's own meta. Add a field to the doctype and it
 * appears here; nothing about this screen names a field.
 */
import { watch } from 'vue'
import { Alert, Button, LoadingText, SettingsBody, SettingsHeader, toast } from 'frappe-ui'
import SettingsFieldRows from './SettingsFieldRows.vue'
import { useAdminAction, useAdminRead } from '../../data/api'
import { useSettingsDraft } from '../../data/useSettingsDraft'

const props = defineProps({
  active: { type: Boolean, default: false },
})

const advanced = useAdminRead('settings.get_advanced_settings', { immediate: false })
const save = useAdminAction('settings.save_advanced_settings')

const { values, changes, changed, adopt, set } = useSettingsDraft()

function adoptSettings(data) {
  for (const group of data.groups) {
    adopt(Object.fromEntries(group.fields.map((field) => [field.fieldname, field.value])))
  }
}

watch(
  () => advanced.data,
  (data) => data && adoptSettings(data),
  { immediate: true },
)

watch(
  () => props.active,
  (isActive) => isActive && !advanced.isFinished && advanced.reload(),
  { immediate: true },
)

async function submit() {
  await save.submit({ ...changes.value })
  if (save.error) return

  // The server answers with the fields it wrote, not with the screen, and a controller can
  // rewrite a value on save — so the whole tab is re-read rather than assumed.
  await advanced.reload()
  toast.success('Advanced settings saved')
}
</script>

<template>
  <SettingsHeader
    title="Advanced"
    description="Every remaining store setting, grouped as it appears in your books."
  >
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
    <LoadingText v-if="advanced.loading && !advanced.data" class="py-10" />

    <template v-else-if="advanced.data">
      <Alert
        theme="amber"
        title="These are setup values, not everyday settings"
        description="Changing one can break your storefront — edit only what you recognise."
      />

      <div class="mt-2 divide-y divide-outline-gray-1">
        <SettingsFieldRows
          :groups="advanced.data.groups"
          :values="values"
          link-options-path="settings.get_link_options"
          @update="set"
        />
      </div>

      <!-- Lists of rows rather than single values, so this says where they live instead of
           pretending it can edit them. -->
      <div v-if="advanced.data.child_tables.length" class="mt-8 border-t border-outline-gray-1 pt-6">
        <h3 class="text-base font-medium text-ink-gray-8">Managed in Desk</h3>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          These are lists rather than single values, so they are still edited on the Lifestyle
          Settings form.
        </p>
        <ul class="mt-3 divide-y divide-outline-gray-1 border-y border-outline-gray-1">
          <li
            v-for="table in advanced.data.child_tables"
            :key="table.label"
            class="flex items-center justify-between gap-4 py-2.5"
          >
            <span class="text-base text-ink-gray-8">{{ table.label }}</span>
            <span class="text-sm text-ink-gray-5">{{ table.options }}</span>
          </li>
        </ul>
      </div>
    </template>
  </SettingsBody>
</template>
