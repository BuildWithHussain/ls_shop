<script setup>
/**
 * Configuring one provider takes over the panel, so the keys of several providers never
 * share a scroll.
 *
 * Every row here is derived from the settings doctype's own meta, in Desk layout order —
 * never a hardcoded field list. Add a docfield to a gateway or carrier Single and it shows
 * up here with its label, its description and its required flag, with no change to this
 * file.
 */
import { reactive, ref } from 'vue'
import {
  Badge,
  Button,
  Select,
  SettingsBody,
  SettingsHeader,
  SettingsRow,
  Switch,
  TextInput,
  toast,
} from 'frappe-ui'

const props = defineProps({
  card: { type: Object, required: true },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['back', 'save'])

const NUMERIC_FIELDTYPES = ['Int', 'Float', 'Currency', 'Percent']

// A Password never arrives with its value — the server sends `is_set` and a null instead —
// so a secret starts blank and staying blank keeps whatever is stored.
const values = reactive(
  Object.fromEntries(
    props.card.groups.flatMap((group) =>
      group.fields.map((field) => [field.fieldname, field.is_secret ? '' : (field.value ?? '')]),
    ),
  ),
)

const enabled = ref(props.card.enabled)

function inputType(field) {
  if (field.is_secret) return 'password'
  if (NUMERIC_FIELDTYPES.includes(field.fieldtype)) return 'number'
  return 'text'
}

function selectOptions(field) {
  return (field.options ?? '').split('\n').filter(Boolean)
}

// Docfield descriptions are authored as Desk HTML — <b>…</b>, and entities like &gt;. This row
// interpolates its description as text, so the markup is unwrapped here rather than shown to the
// owner literally. Parsed in a detached element and read back as text: nothing is ever injected.
function plainText(html) {
  if (!html) return undefined

  const element = document.createElement('div')
  element.innerHTML = html
  return element.textContent.replace(/\s+/g, ' ').trim()
}

// A secret already stored is the one thing this screen cannot show, so it says so instead.
function hint(field) {
  if (field.is_secret && field.is_set) return 'Stored. Leave blank to keep it.'
  if (field.is_secret) return 'Stored encrypted, never shown again.'
  if (field.fieldtype === 'Link') return `Links to ${field.options}.`
  return plainText(field.description)
}

async function copyWebhookUrl() {
  await navigator.clipboard.writeText(props.card.webhook_url)
  toast.success('Webhook URL copied')
}
</script>

<template>
  <SettingsHeader :title="card.label" :description="card.blurb">
    <template #actions>
      <Button label="Back" icon-left="lucide-arrow-left" @click="emit('back')" />
      <Button
        label="Save"
        variant="solid"
        theme="gray"
        :loading="saving"
        @click="emit('save', { enabled, values })"
      />
    </template>
  </SettingsHeader>

  <SettingsBody>
    <div class="divide-y divide-outline-gray-1">
      <SettingsRow title="Enabled" description="Offered to customers at checkout.">
        <div class="flex items-center gap-2">
          <Badge
            v-if="card.missing?.length"
            :label="`${card.missing.length} still needed`"
            theme="orange"
            variant="subtle"
          />
          <Switch v-model="enabled" size="sm" />
        </div>
      </SettingsRow>

      <template v-for="group in card.groups" :key="group.label">
        <p class="pt-5 text-sm text-ink-gray-5">{{ group.label }}</p>
        <SettingsRow
          v-for="field in group.fields"
          :key="field.fieldname"
          :title="field.required ? `${field.label} *` : field.label"
          :description="hint(field)"
        >
          <Switch v-if="field.fieldtype === 'Check'" v-model="values[field.fieldname]" size="sm" />
          <Select
            v-else-if="field.fieldtype === 'Select'"
            v-model="values[field.fieldname]"
            class="w-72"
            :options="selectOptions(field)"
          />
          <TextInput
            v-else
            v-model="values[field.fieldname]"
            class="w-72"
            :type="inputType(field)"
            :placeholder="field.is_secret && field.is_set ? '••••••••' : ''"
          />
        </SettingsRow>
      </template>
    </div>

    <!-- The provider needs this URL in its own panel, and it is the one thing here that
         is read rather than written, so it gets a copy button and no input. -->
    <div v-if="card.webhook_url" class="mt-6 border-t border-outline-gray-1 pt-4">
      <p class="text-sm text-ink-gray-5">Webhook URL</p>
      <div class="mt-2 flex items-center gap-2">
        <code class="min-w-0 flex-1 truncate rounded bg-surface-gray-2 px-2 py-1 text-sm text-ink-gray-7">
          {{ card.webhook_url }}
        </code>
        <Button label="Copy" icon-left="lucide-copy" @click="copyWebhookUrl" />
      </div>
      <p class="mt-2 text-sm text-ink-gray-5">
        Paste this into the provider's dashboard so it can report status back to this store.
      </p>
    </div>

    <div v-if="card.docs_url" class="mt-4">
      <Button
        label="Provider documentation"
        icon-right="lucide-external-link"
        variant="ghost"
        :link="card.docs_url"
      />
    </div>
  </SettingsBody>
</template>

