<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DesktopShell, ScrollArea, Sidebar, SidebarHeader, call } from 'frappe-ui'
import { activeNavTarget, productName, sections } from '../ia/nav'
import logoUrl from '../assets/commera.svg'
import { openSettings } from '../ia/settings'
import { useAdminRead } from '../data/api'
import NavSection from './NavSection.vue'

const route = useRoute()

const activeTarget = computed(() => activeNavTarget(route.path))

// The store's own name, read once for the shell. A site that has not been
// configured yet gets no subtitle rather than a stand-in name.
const storeRequest = useAdminRead('settings.get_store_settings')
const storeName = computed(() => storeRequest.data?.store_name || null)

// The storefront is served by this same site, so it is the origin's root — a
// bare '/' redirects to the shopper's language.
function openStorefront() {
  window.open('/', '_blank', 'noopener')
}

// `location.replace` rather than a router push: the session cookie is gone
// server-side, so the shell in memory is authenticated against nothing and
// every subsequent read would 403 behind a screen that still looks logged in.
async function logout() {
  await call('/api/method/logout')
  window.location.replace('/login')
}

// The workspace header is the dropdown: it names the store and gets you to the
// things that are about the account, not about the page you are on.
const headerMenu = [
  { label: 'Settings', icon: 'lucide-settings', onClick: () => openSettings('general') },
  { label: 'Appearance', icon: 'lucide-sun-moon', onClick: () => openSettings('appearance') },
  { label: 'View storefront', icon: 'lucide-external-link', onClick: openStorefront },
  { label: 'Log out', icon: 'lucide-log-out', onClick: logout },
]
</script>

<template>
  <div class="h-screen w-full bg-surface-base text-ink-gray-9">
    <DesktopShell :scroll="!route.meta.split">
      <template #sidebar>
        <Sidebar width="14rem" class="border-r border-outline-gray-1">
          <div class="flex h-full flex-col p-2">
            <SidebarHeader :title="productName" :subtitle="storeName" :menu-items="headerMenu">
              <template #prefix>
                <img :src="logoUrl" alt="" class="h-full w-full object-cover" />
              </template>
            </SidebarHeader>
            <ScrollArea class="min-h-0 flex-1" viewport-class="pt-1 pb-10">
              <NavSection v-for="section in sections" :key="section.id" :section="section" :active-target="activeTarget" />
            </ScrollArea>
          </div>
        </Sidebar>
      </template>

      <slot />
    </DesktopShell>
  </div>
</template>

