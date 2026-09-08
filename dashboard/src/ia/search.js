import { reactive } from 'vue'

// Search is a palette, not a page: the sidebar row and Mod+K both open it.
export const search = reactive({ open: false })
