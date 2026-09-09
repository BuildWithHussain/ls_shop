import { ref } from 'vue'
import { createAdminCaller } from './adminCaller'

const themes = ref([])
const activeTheme = ref(null)
const settings = ref({
  doctype: null,
  groups: [],
  child_tables: [],
  desk_url: null,
})

// The preview frames the rendered storefront and cannot be told a setting changed,
// so every mutation bumps this.
const previewToken = ref(0)

// A refused read leaves `themes` empty, which reads as "this store has no themes"
// unless the failure is kept.
const loadError = ref(null)

const { attempt, call, loading } = createAdminCaller('theme.')

function apply(data) {
  if (!data) return

  themes.value = data.themes ?? []
  activeTheme.value = data.active_theme ?? null
  settings.value = data.settings ?? {
    doctype: null,
    groups: [],
    child_tables: [],
    desk_url: null,
  }
}

async function load() {
  const { data, error } = await attempt('get_editor_data')
  loadError.value = error
  apply(data)
}

// Run a mutation and adopt the screen it returns, or null when the server refused it.
async function mutate(method, params = {}) {
  const data = await call(method, params)
  if (!data) return null
  apply(data)
  previewToken.value += 1
  return data
}

export function useTheme() {
  return {
    themes,
    activeTheme,
    settings,
    previewToken,
    loadError,
    loading,
    load,
    mutate,
  }
}
