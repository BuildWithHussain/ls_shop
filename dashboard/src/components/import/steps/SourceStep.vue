<script setup>
import { Badge } from 'frappe-ui'
import { imp } from '../../../data/importFlow'
import CoachTip from '../CoachTip.vue'
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl text-ink-gray-9">Where are your products right now?</h2>
      <p class="mt-1.5 text-p-base text-ink-gray-6">
        Every platform can export a spreadsheet, so that is the way in. You can import again later.
      </p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <button
        type="button"
        class="rounded-5 border p-5 text-left transition"
        :class="imp.source === 'csv' ? 'border-outline-gray-4 bg-surface-gray-1' : 'border-outline-gray-1 hover:bg-surface-gray-1'"
        @click="imp.source = 'csv'"
      >
        <div class="flex items-start gap-3">
          <span class="lucide-file-spreadsheet size-5 shrink-0 text-ink-gray-7" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span class="text-base-semibold text-ink-gray-8">Spreadsheet</span>
              <Badge class="shrink-0" label="Most common" theme="blue" variant="subtle" />
            </div>
            <p class="mt-1 text-p-sm text-ink-gray-5">CSV or Excel exported from anywhere.</p>
          </div>
          <!-- Always in the layout, so selecting the card never reflows its text. -->
          <span
            class="lucide-circle-check size-4 shrink-0 text-ink-green-5"
            :class="imp.source === 'csv' ? '' : 'invisible'"
            aria-hidden="true"
          />
        </div>
      </button>
    </div>

    <CoachTip
      title="Coming from another store?"
      text="Export a CSV of your products from it and continue. The export carries your titles, prices and stock counts along, and you match its column headings to ours on the next step but one."
    />
  </div>
</template>
