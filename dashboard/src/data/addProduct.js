// The Add Product dialog is a single global instance (same pattern as data/importFlow.js's
// ImportDialog) — opened from wherever "Add product" lives, without threading a v-model prop
// through every caller.
import { reactive } from 'vue'

export const addProduct = reactive({ open: false })

export function openAddProduct() {
  addProduct.open = true
}

export function closeAddProduct() {
  addProduct.open = false
}
