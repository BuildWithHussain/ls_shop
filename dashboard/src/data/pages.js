import { ref } from 'vue'
import { createAdminCaller } from './adminCaller'

const pages = ref([])
const total = ref(0)

// A refused read leaves `pages` empty, which reads as "this store has no pages"
// unless the failure is kept.
const loadError = ref(null)

const { attempt, call, loading } = createAdminCaller('pages.')

async function load() {
  const { data, error } = await attempt('get_pages')
  loadError.value = error
  pages.value = data?.pages ?? []
  total.value = data?.total ?? 0
}

// The editor needs the refusal itself, not an empty form that reads as a blank page.
async function getPage(name) {
  return await attempt('get_page', { name })
}

// Resolves to the saved page, or null when the server refused it.
async function savePage(fields) {
  return await call('save_page', fields)
}

// delete_page answers with nothing, so success can only be read off the absence
// of an error — `call` alone cannot tell the two apart.
async function removePage(name) {
  const { error } = await attempt('delete_page', { name })
  if (error) return false
  await load()
  return true
}

export function usePages() {
  return { pages, total, loadError, loading, load, getPage, savePage, removePage }
}
