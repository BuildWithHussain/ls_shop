<script setup>
/**
 * One docfield, as the control its fieldtype asks for. Every settings screen that renders fields
 * it did not hardcode reaches this through SettingsFieldRows, so a provider's API key, an
 * analytics pixel id and an advanced setting all behave the same way.
 */
import { computed, ref } from 'vue'
import { Button, Select, Switch, Textarea, TextInput, toast, useFileUpload } from 'frappe-ui'
import SettingsLinkControl from './SettingsLinkControl.vue'

const NUMERIC_FIELDTYPES = ['Int', 'Float', 'Currency', 'Percent']
const MULTILINE_FIELDTYPES = ['Small Text', 'Text', 'Long Text', 'Code']
const ATTACH_FIELDTYPES = ['Attach', 'Attach Image']

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean], default: null },
  // Only set where the server offers a picker for this doctype's Link fields. Without one a
  // Link stays a plain box rather than a combobox that can never fill itself.
  linkOptionsPath: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const { upload, isUploading } = useFileUpload()
const fileInput = ref(null)

// Frappe answers with 1/0 and numbers where an input wants a string, and a field never touched
// arrives as null.
const text = computed({
  get: () => (props.modelValue === null || props.modelValue === undefined ? '' : String(props.modelValue)),
  set: (value) => emit('update:modelValue', value),
})

const checked = computed({
  get: () => Boolean(props.modelValue) && props.modelValue !== '0',
  set: (value) => emit('update:modelValue', value),
})

function inputType(field) {
  if (field.is_secret) return 'password'
  if (NUMERIC_FIELDTYPES.includes(field.fieldtype)) return 'number'
  return 'text'
}

function selectOptions(field) {
  return (field.options ?? '').split('\n').filter(Boolean)
}

async function uploadFile(event) {
  const [file] = [...(event.target.files ?? [])]
  event.target.value = ''
  if (!file) return

  try {
    // Public: these end up in storefront markup — share images, logos — not behind a login.
    const uploaded = await upload(file, { private: false })
    emit('update:modelValue', uploaded.file_url)
  } catch {
    toast.error(`Could not upload ${file.name}`)
  }
}
</script>

<template>
  <Switch v-if="field.fieldtype === 'Check'" v-model="checked" size="sm" />

  <Select
    v-else-if="field.fieldtype === 'Select'"
    v-model="text"
    class="w-72"
    :options="selectOptions(field)"
  />

  <SettingsLinkControl
    v-else-if="field.fieldtype === 'Link' && linkOptionsPath"
    :field="field"
    :model-value="text"
    :options-path="linkOptionsPath"
    @update:model-value="emit('update:modelValue', $event)"
  />

  <div v-else-if="ATTACH_FIELDTYPES.includes(field.fieldtype)" class="flex w-72 items-center gap-2">
    <input
      ref="fileInput"
      type="file"
      class="hidden"
      :accept="field.fieldtype === 'Attach Image' ? 'image/*' : undefined"
      @change="uploadFile"
    />
    <p v-if="text" class="min-w-0 flex-1 truncate text-base text-ink-gray-7">{{ text }}</p>
    <p v-else class="min-w-0 flex-1 text-base text-ink-gray-5">Nothing uploaded</p>
    <Button :loading="isUploading" label="Upload" @click="fileInput.click()" />
    <Button
      v-if="text"
      icon="lucide-x"
      variant="ghost"
      :aria-label="`Remove ${field.label}`"
      @click="emit('update:modelValue', '')"
    />
  </div>

  <Textarea
    v-else-if="MULTILINE_FIELDTYPES.includes(field.fieldtype)"
    v-model="text"
    class="w-72"
    :rows="field.fieldtype === 'Code' ? 8 : 3"
  />

  <TextInput
    v-else
    v-model="text"
    class="w-72"
    :type="inputType(field)"
    :placeholder="field.is_secret && field.is_set ? '••••••••' : ''"
  />
</template>
