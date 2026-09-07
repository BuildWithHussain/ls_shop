import { ref } from 'vue'
import { toast } from 'frappe-ui'

// Frappe stores checks as 1/0 and numbers as numbers, while an input hands back a string or a
// boolean, so two values are the same when they would be stored the same.
function normalize(value) {
  if (value === true) return '1'
  if (value === false) return '0'
  return String(value ?? '')
}

/**
 * A settings panel that saves itself: there is no Save button, so every control writes its own
 * field the moment it settles.
 *
 * What is in the boxes is kept next to what the server last said was stored, because a write is
 * the only truth here — a refused one must not leave a box showing what the server refused, and a
 * value the controller rewrote on save wins over what was typed. Only the one field that changed
 * is ever submitted, so a blank secret means "keep the stored one" rather than "wipe it", and one
 * control's save never rewrites a field the owner never touched.
 */
export function useSettingsAutosave(save) {
  const values = ref({})
  const stored = ref({})

  // Merged, not replaced: a panel adopts the fields it owns — a group, a section — one answer at
  // a time, and adopting one must not forget the rest.
  function adopt(record) {
    stored.value = { ...stored.value, ...record }
    values.value = { ...values.value, ...record }
  }

  // What is being typed, before it is worth writing.
  function set(fieldname, value) {
    values.value[fieldname] = value
  }

  // `afterSave` is for panels whose stored truth is wider than the save's answer — an analytics
  // secret that only stops reading as missing once the settings are re-read.
  async function commit(fieldname, value, label, afterSave) {
    if (normalize(value) === normalize(stored.value[fieldname])) return

    values.value[fieldname] = value
    const saved = await save.submit({ [fieldname]: value })
    if (save.error) {
      values.value = { ...stored.value }
      return
    }

    if (afterSave) await afterSave(saved)
    else adopt(saved)

    toast.success(`${label} saved`)
  }

  return { values, stored, adopt, set, commit }
}
