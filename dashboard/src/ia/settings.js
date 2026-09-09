import { reactive } from 'vue'

// Settings is a dialog, not a route: it is opened from the workspace menu and
// the sidebar, and it should never lose the page behind it.
export const settings = reactive({ open: false, tab: 'general' })

export function openSettings(tab = 'general') {
  settings.tab = tab
  settings.open = true
}
