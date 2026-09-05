<script setup>
import { computed, ref } from 'vue'
import { Badge, Button, Progress, Select, Spinner, TabButtons, toast } from 'frappe-ui'
import { imp } from '../../../data/importFlow'
import ProductThumb from '../ProductThumb.vue'
import CoachTip from '../CoachTip.vue'

const delay = (ms) => ms

// Bulk photo matching (a zip of files matched to a SKU, or a URL column fetched server-side) has
// no backend behind it yet — documented as deliberately inert in docs/commera-open-questions.md,
// the same way the rest of this step already was. What changed is only where its placeholder rows
// come from: the real title/colour/size read off the uploaded file, instead of a fixed fixture.
const IMPORT_ROWS = computed(() =>
  imp.rows
    .filter((row) => !row.issue || row.issue.level === 'warning')
    .map((row) => ({
      sku: `${row.title}-${row.color}-${row.size}`,
      name: row.title,
      variant: [row.color, row.size].filter(Boolean).join(' / '),
      icon: 'lucide-shirt',
      images: 0,
    })),
)

const uploading = ref(false)
const pct = ref(0)

const UNMATCHED = ['IMG_4471.jpg', 'IMG_4472.jpg', 'shoot-final-v2.png', 'socks grey.jpeg']

const assign = ref({})
const productOptions = computed(() => [
  { label: 'Leave unmatched', value: '' },
  ...IMPORT_ROWS.value.map((p) => ({ label: `${p.name} — ${p.variant}`, value: p.sku })),
])

function upload() {
  uploading.value = true
  pct.value = 0
  const tick = () => {
    pct.value = Math.min(100, pct.value + 12)
    if (pct.value < 100) setTimeout(tick, delay(140))
    else
      setTimeout(() => {
        uploading.value = false
        imp.imagesDone = true
        toast.success('356 of 372 images matched by file name')
      }, delay(200))
  }
  setTimeout(tick, delay(140))
}

const urlRows = computed(() =>
  IMPORT_ROWS.value.map((p, i) => ({
    ...p,
    url: `https://cdn.kirana.co/catalog/${p.sku.toLowerCase()}-1.jpg`,
    ok: !(i === 3 || i === 8 || i === 12),
  })),
)
const broken = computed(() => urlRows.value.filter((r) => !r.ok).length)

const perProduct = ref(IMPORT_ROWS.value.slice(0, 6).map((p) => ({ ...p, uploaded: p.images > 0 })))
const perDone = computed(() => perProduct.value.filter((p) => p.uploaded).length)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start gap-4">
      <div class="min-w-0 flex-1">
        <h2 class="text-xl text-ink-gray-9">Add product photos</h2>
        <p class="mt-1 text-p-base text-ink-gray-6">
          Products sell far better with a photo. You can also skip this and add them later.
        </p>
      </div>
      <TabButtons
        v-model="imp.imagesMode"
        class="shrink-0"
        :options="[
          { label: 'Drop a folder', value: 'bulk' },
          { label: 'From a URL column', value: 'url' },
          { label: 'One by one', value: 'each' },
        ]"
      />
    </div>

    <!-- A: a folder of files, matched on the SKU in each name -->
    <template v-if="imp.imagesMode === 'bulk'">
      <div
        v-if="!imp.imagesDone && !uploading"
        class="flex flex-col items-center justify-center rounded-5 border-2 border-dashed border-outline-gray-2 bg-surface-gray-1 px-6 py-12 text-center"
        @dragover.prevent
        @drop.prevent="upload"
      >
        <div class="flex size-11 items-center justify-center rounded-full bg-surface-base text-ink-gray-6 shadow-sm">
          <span class="lucide-images size-5" aria-hidden="true" />
        </div>
        <p class="mt-3 text-base text-ink-gray-7">Drop a folder or a .zip of photos</p>
        <p class="mt-1 max-w-[420px] text-p-sm text-ink-gray-5">
          We match each file to a product by the SKU in its name, so
          <span class="text-ink-gray-7">TEE-OVS-BLK-M-1.jpg</span> lands on the right product.
        </p>
        <Button class="mt-3" variant="solid" theme="gray" label="Browse photos" @click="upload" />
      </div>

      <div v-else-if="uploading" class="rounded-5 border border-outline-gray-1 p-4">
        <div class="flex items-center gap-3">
          <Spinner class="size-4" />
          <span class="text-base text-ink-gray-8">Uploading 372 photos…</span>
          <span class="ml-auto text-sm text-ink-gray-5 tabular-nums">{{ pct }}%</span>
        </div>
        <Progress :value="pct" size="sm" class="mt-3" />
      </div>

      <template v-else>
        <div class="grid gap-4 sm:grid-cols-3">
          <div
            v-for="s in [
              { n: '356', l: 'photos matched', tone: 'text-ink-green-6' },
              { n: '16', l: 'could not be matched', tone: 'text-ink-amber-7' },
              { n: '7', l: 'products with no photo', tone: 'text-ink-gray-7' },
            ]"
            :key="s.l"
            class="rounded-5 border border-outline-gray-1 p-4"
          >
            <div class="text-2xl tabular-nums" :class="s.tone">{{ s.n }}</div>
            <div class="mt-0.5 text-sm text-ink-gray-5">{{ s.l }}</div>
          </div>
        </div>

        <div class="rounded-5 border border-outline-gray-1 p-4">
          <div class="text-base-semibold text-ink-gray-8">Matched products</div>
          <div class="mt-3 flex flex-wrap gap-2">
            <div v-for="p in IMPORT_ROWS.slice(0, 11)" :key="p.sku" class="relative">
              <ProductThumb :seed="p.sku" :icon="p.icon" size="size-14" icon-size="size-5" :empty="p.images === 0" />
              <span
                v-if="p.images"
                class="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-surface-gray-7 px-1 text-2xs tabular-nums text-white"
              >
                {{ p.images }}
              </span>
            </div>
            <div
              class="flex size-14 items-center justify-center rounded-4 border border-dashed border-outline-gray-2 text-sm text-ink-gray-5"
            >
              +110
            </div>
          </div>
        </div>

        <div class="rounded-5 border border-outline-gray-1">
          <div class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-3">
            <span class="text-base-semibold text-ink-gray-8">Files we could not place</span>
            <Badge label="16" theme="orange" variant="subtle" />
            <span class="ml-auto text-sm text-ink-gray-5">Showing 4</span>
          </div>
          <div class="divide-y divide-outline-gray-1">
            <div v-for="f in UNMATCHED" :key="f" class="flex items-center gap-3 px-4 py-3">
              <ProductThumb :seed="f" icon="lucide-image" />
              <div class="min-w-0 flex-1 truncate text-base text-ink-gray-7">{{ f }}</div>
              <Select v-model="assign[f]" :options="productOptions" placeholder="Assign to product" class="w-64 shrink-0" />
            </div>
          </div>
        </div>
      </template>

      <CoachTip
        title="File names do the matching"
        text="Name each photo after its SKU with a -1, -2, -3 suffix. The first one becomes the main image."
      />
    </template>

    <!-- B: a column of image links -->
    <template v-else-if="imp.imagesMode === 'url'">
      <div class="flex items-center gap-2 rounded-4 border border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5">
        <span class="lucide-link size-4 text-ink-gray-6" aria-hidden="true" />
        <span class="text-base text-ink-gray-7">
          Pulling photos from the <span class="text-ink-gray-9">Image files</span> column.
        </span>
        <Badge class="ml-auto" :label="broken + ' links failed'" theme="red" variant="subtle" />
      </div>

      <div class="overflow-hidden rounded-5 border border-outline-gray-1">
        <div class="divide-y divide-outline-gray-1">
          <div v-for="r in urlRows" :key="r.sku + r.url" class="flex items-center gap-3 px-4 py-2.5">
            <ProductThumb :seed="r.sku" :icon="r.icon" :empty="!r.ok" />
            <div class="min-w-0 flex-1">
              <div class="truncate text-base text-ink-gray-8">{{ r.name }} · {{ r.variant }}</div>
              <div class="truncate text-sm text-ink-gray-5">{{ r.url }}</div>
            </div>
            <Badge
              class="shrink-0"
              :label="r.ok ? 'Fetched' : '404 not found'"
              :theme="r.ok ? 'green' : 'red'"
              variant="subtle"
            />
            <Button v-if="!r.ok" class="shrink-0" variant="subtle" label="Upload instead" />
          </div>
        </div>
      </div>

      <CoachTip
        theme="orange"
        icon="lucide-triangle-alert"
        title="Broken links do not block the import"
        text="Those products come in without a photo, and you can fix them from the product page any time."
      />
    </template>

    <!-- C: one product at a time -->
    <template v-else>
      <div class="flex items-center gap-3 rounded-4 border border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5">
        <span class="text-base text-ink-gray-7">{{ perDone }} of {{ perProduct.length }} done</span>
        <Progress :value="Math.round((perDone / perProduct.length) * 100)" size="sm" class="max-w-56 flex-1" />
        <Button class="ml-auto" variant="ghost" label="Skip the rest for now" />
      </div>

      <div class="overflow-hidden rounded-5 border border-outline-gray-1">
        <div class="divide-y divide-outline-gray-1">
          <div v-for="p in perProduct" :key="p.sku" class="flex items-center gap-3 px-4 py-3">
            <ProductThumb :seed="p.sku" :icon="p.icon" size="size-12" :empty="!p.uploaded" />
            <div class="min-w-0 flex-1">
              <div class="truncate text-base text-ink-gray-8">{{ p.name }}</div>
              <div class="truncate text-sm text-ink-gray-5">{{ p.variant }} · {{ p.sku }}</div>
            </div>
            <Badge v-if="p.uploaded" class="shrink-0" :label="p.images + ' photos'" theme="green" variant="subtle" />
            <Button
              class="shrink-0"
              :variant="p.uploaded ? 'subtle' : 'solid'"
              theme="gray"
              :icon-left="p.uploaded ? 'lucide-pencil' : 'lucide-upload'"
              :label="p.uploaded ? 'Replace' : 'Upload'"
              @click="((p.uploaded = true), (p.images = p.images || 1))"
            />
          </div>
        </div>
        <div class="border-t border-outline-gray-1 bg-surface-gray-1 px-4 py-2.5 text-sm text-ink-gray-5">
          Showing 6 of 128 products
        </div>
      </div>

      <CoachTip
        icon="lucide-clock"
        title="Slow going for a big catalogue"
        text="For 128 products, dropping a folder of photos takes about a minute instead."
      />
    </template>
  </div>
</template>

