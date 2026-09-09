// Tailwind v3 does not merge `content` from a preset, and frappe-ui's own list
// covers surfaces this app's globs missed — the experimental CommandPalette
// among them, which is why its padding classes were never generated.
import frappeUIPreset, { content as frappeUIContent } from 'frappe-ui/tailwind'

/** @type {import('tailwindcss').Config} */
export default {
  presets: [frappeUIPreset],
  content: [...frappeUIContent, './index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
}
