<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DesktopShell, ScrollArea, Sidebar, SidebarHeader } from 'frappe-ui'
import { activeNavTarget, productName, sections } from '../ia/nav'
import logoUrl from '../assets/commera.svg'
import { openSettings } from '../ia/settings'
import NavSection from './NavSection.vue'

const route = useRoute()

const activeTarget = computed(() => activeNavTarget(route.path))

// The workspace header is the dropdown: it names the store and gets you to the
// things that are about the account, not about the page you are on.
const headerMenu = [
  { label: 'Settings', icon: 'lucide-settings', onClick: () => openSettings('general') },
  { label: 'Appearance', icon: 'lucide-sun-moon', onClick: () => openSettings('appearance') },
  { label: 'View storefront', icon: 'lucide-external-link', onClick: () => {} },
  { label: 'Log out', icon: 'lucide-log-out', onClick: () => {} },
]
</script>

<template>
  <div class="h-screen w-full bg-surface-base text-ink-gray-9">
    <DesktopShell :scroll="!route.meta.split">
      <template #sidebar>
        <Sidebar width="14rem" class="border-r border-outline-gray-1">
          <div class="flex h-full flex-col p-2">
            <SidebarHeader :title="productName" subtitle="Kirana & Co" :menu-items="headerMenu">
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

