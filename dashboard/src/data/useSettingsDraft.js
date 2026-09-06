import { computed, reactive } from 'vue'

// Frappe stores checks as 1/0 and numbers as numbers, while an input hands back a string or a
// boolean, so two values are the same when they would be stored the same.
function normalize(value) {
  if (value === true) return '1'
  if (value === false) return '0'
  if (value === null || value === undefined) return ''
  return String(value)
}

/**
 * What is in the boxes, next to what the server last said was stored.
 *
 * Save then sends only the fields that actually changed — which is what makes a blank secret mean
 * "keep the stored one" rather than "wipe it", and what stops one tab's save from rewriting a
 * field the owner never touched.
 */
export function useSettingsDraft() {
  const values = reactive({})
  const saved = reactive({})

  function adopt(record) {
    for (const [fieldname, value] of Object.entries(record)) {
      values[fieldname] = value ?? null
      saved[fieldname] = value ?? null
    }
  }

  function set(fieldname, value) {
    values[fieldname] = value
  }

  const changes = computed(() =>
    Object.fromEntries(
      Object.keys(values)
        .filter((fieldname) => normalize(values[fieldname]) !== normalize(saved[fieldname]))
        .map((fieldname) => [fieldname, values[fieldname]]),
    ),
  )

  const changed = computed(() => Object.keys(changes.value).length > 0)

  return { values, changes, changed, adopt, set }
}
