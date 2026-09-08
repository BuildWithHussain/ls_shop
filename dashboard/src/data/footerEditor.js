import { ref } from 'vue'
import { createAdminCaller } from './adminCaller'

const sections = ref([])
const pages = ref([])

// The preview frames the rendered storefront footer and cannot be told the columns
// moved, so every mutation bumps this.
const previewToken = ref(0)

// A refused read leaves `sections` empty, which reads as "this store has no footer"
// unless the failure is kept.
const loadError = ref(null)

const { attempt, call, loading } = createAdminCaller('footer.')

function apply(data) {
  if (!data) return

  sections.value = data.columns ?? []
  pages.value = data.pages ?? []
}

// Run a mutation and adopt the footer it returns, or null when the server refused it.
async function mutate(method, params = {}) {
  const data = await call(method, params)
  if (!data) return null
  apply(data)
  previewToken.value += 1
  return data
}

async function load() {
  const { data, error } = await attempt('get_editor_data')
  loadError.value = error
  apply(data)
}

// The order a list ends up in after `oldIndex` is lifted out and dropped at `newIndex`.
function reordered(names, oldIndex, newIndex) {
  const next = [...names]
  const [moved] = next.splice(oldIndex, 1)
  next.splice(newIndex, 0, moved)
  return next
}

export function useFooter() {
  return { sections, pages, loadError, previewToken, loading, load, mutate, reordered }
}
