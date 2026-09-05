<script setup>
/**
 * One docfield of a settings Single, as the control its fieldtype asks for.
 *
 * Editing is committed on change, never per keystroke: every commit saves and reloads the
 * storefront preview underneath, which no store owner wants to watch happen mid-word.
 */
import { ref, watch } from 'vue'
import { Select, Switch, Textarea, TextInput } from 'frappe-ui'

const props = defineProps({
  field: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['commit'])

const NUMERIC_FIELDTYPES = ['Int', 'Float', 'Currency', 'Percent']
const MULTILINE_FIELDTYPES = ['Small Text', 'Text', 'Long Text', 'Text Editor']

const draft = ref(props.field.value ?? '')

// The server answers every save with the whole screen, so a value the backend rewrote —
// or a save that was refused — must win over what is in the box.
watch(
  () => props.field.value,
  (value) => (draft.value = value ?? ''),
)

function commit(value) {
  if (value === (props.field.value ?? '')) return
  emit('commit', value)
}

function selectOptions(field) {
  return (field.options ?? '').split('\n').filter(Boolean)
}

// Docfield descriptions are authored as Desk HTML — <b>…</b>, and entities like &gt;. This is
// rendered as text, so the markup is unwrapped rather than shown literally. Parsed in a
// detached element and read back as text: nothing is ever injected.
function plainText(html) {
  if (!html) return undefined

  const element = document.createElement('div')
  element.innerHTML = html
  return element.textContent.replace(/\s+/g, ' ').trim()
}
</script>

<template>
  <div>
    <label class="mb-1.5 block text-base text-ink-gray-6" :for="field.fieldname">
      {{ field.label }}
    </label>

    <Switch
      v-if="field.fieldtype === 'Check'"
      :id="field.fieldname"
      v-model="draft"
      size="sm"
      :disabled="disabled"
      @update:model-value="commit($event)"
    />

    <!-- The swatch is the browser's own colour input; the hex beside it is what a brand
         guideline is actually given in, so it stays typeable. -->
    <div v-else-if="field.fieldtype === 'Color'" class="flex items-center gap-2">
      <input
        :id="field.fieldname"
        v-model="draft"
        type="color"
        class="size-7 shrink-0 cursor-pointer rounded-4 border border-outline-gray-2 bg-surface-base"
        :disabled="disabled"
        :aria-label="field.label"
        @change="commit(draft)"
      />
      <TextInput
        v-model="draft"
        class="min-w-0 flex-1"
        :disabled="disabled"
        :aria-label="`${field.label} hex`"
        placeholder="#000000"
        @change="commit(draft)"
      />
    </div>

    <Select
      v-else-if="field.fieldtype === 'Select'"
      :id="field.fieldname"
      v-model="draft"
      :options="selectOptions(field)"
      :disabled="disabled"
      @update:model-value="commit($event)"
    />

    <Textarea
      v-else-if="MULTILINE_FIELDTYPES.includes(field.fieldtype)"
      :id="field.fieldname"
      v-model="draft"
      :rows="3"
      :disabled="disabled"
      @change="commit(draft)"
    />

    <TextInput
      v-else
      :id="field.fieldname"
      v-model="draft"
      :type="NUMERIC_FIELDTYPES.includes(field.fieldtype) ? 'number' : 'text'"
      :disabled="disabled"
      @change="commit(draft)"
    />

    <p v-if="plainText(field.description)" class="mt-1 text-sm text-ink-gray-5">
      {{ plainText(field.description) }}
    </p>
  </div>
</template>
