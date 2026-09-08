import { useMediaQuery } from '@vueuse/core'

// Below Tailwind's `sm` breakpoint, which is where the app swaps between the
// mobile and desktop layouts. A media query beats a resize listener: the browser
// only notifies on a breakpoint crossing, not on every frame of a drag-resize.
const MOBILE_QUERY = '(max-width: 639.98px)'

export function useIsMobile() {
  return useMediaQuery(MOBILE_QUERY)
}
