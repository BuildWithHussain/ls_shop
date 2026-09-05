<script setup>
import { ref } from 'vue'
import { Badge, Button, Select, Slider, Switch, TabButtons, toast } from 'frappe-ui'
import AppPageHeader from '../../components/AppPageHeader.vue'
import PageBody from '../../components/PageBody.vue'
import StorefrontPreview from '../../components/StorefrontPreview.vue'

const themes = ref([
  { id: 'pixio', name: 'Pixio', note: 'Current theme · v2.4', live: true },
  { id: 'ledger', name: 'Ledger', note: 'Editorial, good for books', live: false },
  { id: 'market', name: 'Market', note: 'Dense grid, good for many SKUs', live: false },
])

const ACCENTS = {
  slate: '#334155',
  forest: '#166534',
  clay: '#9a3412',
  plum: '#6b21a8',
}

const accent = ref('slate')
const font = ref('Inter')
const radius = ref([8]) // Slider is always an array — [value] for single, [lo, hi] for a range
const density = ref('regular')
const width = ref('wide')
const device = ref('desktop')
const flags = ref({ quickAdd: true, stickyAtc: false, reviews: true })

const accentOptions = Object.keys(ACCENTS).map((k) => ({ label: k[0].toUpperCase() + k.slice(1), value: k }))
const fontOptions = ['Inter', 'Instrument Serif', 'Geist Mono'].map((f) => ({ label: f, value: f }))
const densityOptions = [
  { label: 'Compact', value: 'compact' },
  { label: 'Regular', value: 'regular' },
  { label: 'Airy', value: 'airy' },
]
const widthOptions = ['Narrow', 'Wide', 'Full'].map((w) => ({ label: w, value: w.toLowerCase() }))

function activate(theme) {
  themes.value.forEach((t) => (t.live = t.id === theme.id))
  toast.success(`${theme.name} is now the live theme`)
}
</script>

<template>
  <AppPageHeader title="Theme">
    <template #actions>
      <Button class="hidden sm:inline-flex" label="Preview store" icon-left="lucide-external-link" />
      <Button label="Publish" variant="solid" theme="gray" @click="toast.success('Theme published')" />
    </template>
  </AppPageHeader>

  <PageBody>
    <div class="gap-6 lg:flex">
      <div class="w-full shrink-0 space-y-11 lg:w-[22rem]">
        <section>
          <h2 class="text-lg-semibold text-ink-gray-8">Installed themes</h2>
          <div class="mt-3 space-y-2">
            <div
              v-for="theme in themes"
              :key="theme.id"
              class="flex items-center gap-3 rounded-5 border border-outline-gray-1 p-3"
            >
              <span class="grid size-9 shrink-0 place-items-center rounded-4 bg-surface-gray-2 text-ink-gray-6">
                <span class="lucide-palette size-4" aria-hidden="true" />
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-base text-ink-gray-8">{{ theme.name }}</p>
                <p class="mt-1 truncate text-sm text-ink-gray-5">{{ theme.note }}</p>
              </div>
              <Badge v-if="theme.live" label="Live" theme="green" variant="subtle" />
              <Button v-else label="Activate" @click="activate(theme)" />
            </div>
          </div>
        </section>

        <section>
          <h2 class="text-lg-semibold text-ink-gray-8">Brand</h2>
          <div class="mt-4 space-y-4">
            <Select v-model="accent" class="w-full" label="Accent colour" :options="accentOptions" />
            <Select v-model="font" class="w-full" label="Heading font" :options="fontOptions" />
          </div>
        </section>

        <section>
          <h2 class="text-lg-semibold text-ink-gray-8">Shape</h2>
          <div class="mt-4 space-y-4">
            <div>
              <p class="mb-1.5 text-base text-ink-gray-6">Corner radius — {{ radius[0] }}px</p>
              <Slider v-model="radius" :min="0" :max="24" :step="2" />
            </div>
            <Select v-model="density" class="w-full" label="Spacing" :options="densityOptions" />
            <Select v-model="width" class="w-full" label="Page width" :options="widthOptions" />
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-lg-semibold text-ink-gray-8">Product page</h2>
          <Switch v-model="flags.quickAdd" label="Quick add from the grid" size="sm" />
          <Switch v-model="flags.stickyAtc" label="Sticky add to cart" size="sm" />
          <Switch v-model="flags.reviews" label="Show reviews" size="sm" />
        </section>

        <section>
          <h2 class="text-lg-semibold text-ink-gray-8">Layout</h2>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            Header, footer and section order live in Pages and Navigation — this screen only owns tokens.
          </p>
          <div class="mt-3 flex gap-2">
            <Button label="Edit navigation" route="/storefront/navigation" />
            <Button label="Edit pages" route="/storefront/pages" />
          </div>
        </section>
      </div>

      <!-- Live token preview: a miniature of the storefront, not a real iframe. -->
      <div class="mt-8 min-w-0 flex-1 lg:mt-0">
        <div class="mb-3 flex items-center justify-between">
          <p class="text-sm text-ink-gray-5">Preview</p>
          <TabButtons
            v-model="device"
            size="sm"
            :options="[
              { label: 'Desktop', value: 'desktop' },
              { label: 'Mobile', value: 'mobile' },
            ]"
          />
        </div>
        <StorefrontPreview :device="device" />
      </div>
    </div>
  </PageBody>
</template>
