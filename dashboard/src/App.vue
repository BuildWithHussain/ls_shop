<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { FrappeUIProvider } from 'frappe-ui'
import { useIsMobile } from './utils/useIsMobile'
import AppShell from './components/AppShell.vue'
import AppSettingsDialog from './components/settings/AppSettingsDialog.vue'
import SearchPalette from './components/SearchPalette.vue'
import ImportDialog from './components/import/ImportDialog.vue'
import AddProductDialog from './components/AddProductDialog.vue'

// Mobile and desktop are separate navigation families — frappe-ui ships
// MobileShell alongside DesktopShell rather than as a responsive variant of it —
// so the app picks a layout for the viewport instead of adding breakpoints to
// the sidebar. The phone bundle is lazy so a desktop load never pays for it.
const isMobileViewport = useIsMobile()
const MobileLayout = defineAsyncComponent(() => import('./components/MobileLayout.vue'))
const Layout = computed(() => (isMobileViewport.value ? MobileLayout : AppShell))
</script>

<template>
  <FrappeUIProvider>
    <component :is="Layout">
      <router-view />
    </component>

    <!-- One instance for the whole app, outside the layout so both shells reach
         them; opened from the workspace menu and the sidebar footer. -->
    <AppSettingsDialog />
    <SearchPalette />
    <ImportDialog />
    <AddProductDialog />
  </FrappeUIProvider>
</template>

