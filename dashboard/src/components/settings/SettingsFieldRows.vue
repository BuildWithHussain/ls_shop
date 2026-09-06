<script setup>
/**
 * A group of docfields as settings rows, in the order the doctype itself lays them out.
 *
 * There is one of these in the app, not one per screen: the provider config, the analytics tab
 * and the advanced tab all render server-described fields, so a docfield's label, description,
 * required flag and "this secret is already stored" wording reach all three the same way.
 */
import { SettingsRow } from 'frappe-ui'
import SettingsFieldControl from './SettingsFieldControl.vue'

defineProps({
  groups: { type: Array, required: true },
  values: { type: Object, required: true },
  linkOptionsPath: { type: String, default: '' },
})

const emit = defineEmits(['update'])

// Docfield descriptions are authored as Desk HTML — <b>…</b>, and entities like &gt;. A row
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
</script>

<template>
  <template v-for="group in groups" :key="group.label">
    <p v-if="group.label" class="pt-5 text-sm text-ink-gray-5">{{ group.label }}</p>
    <SettingsRow
      v-for="field in group.fields"
      :key="field.fieldname"
      :title="field.required ? `${field.label} *` : field.label"
      :description="hint(field)"
    >
      <SettingsFieldControl
        :field="field"
        :model-value="values[field.fieldname]"
        :link-options-path="linkOptionsPath"
        @update:model-value="emit('update', field.fieldname, $event)"
      />
    </SettingsRow>
  </template>
</template>
