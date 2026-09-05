<script setup>
import { computed } from 'vue'
import { longDate } from '../data/format'

// Fed straight from the order's own `progress` array (ls_shop.api.admin.orders.describe_progress) —
// each entry already carries the state ('done' | 'current' | 'upcoming') and label the ladder needs;
// this component only adds the icon and the caption text, which are presentational.
const props = defineProps({ progress: { type: Array, required: true } })

const ICONS = {
  confirmation_pending: 'lucide-clock',
  to_fulfil: 'lucide-shopping-bag',
  delivery_note_drafted: 'lucide-file-text',
  packed: 'lucide-package',
  shipped: 'lucide-truck',
  delivered: 'lucide-house',
  cancelled: 'lucide-circle-x',
  returned: 'lucide-rotate-ccw',
}

// A terminal step (cancelled/returned) reads as its own state, layered on top
// of the plain done/current/upcoming three the rest of the ladder uses.
const TERMINAL_KEYS = ['cancelled', 'returned']

const steps = computed(() =>
  props.progress.map((step) => ({
    ...step,
    icon: ICONS[step.key] ?? 'lucide-circle',
    caption: step.note || (step.at ? longDate(step.at) : step.state === 'current' ? 'In progress' : 'Not yet'),
    tone: TERMINAL_KEYS.includes(step.key) && step.state === 'current' ? step.key : step.state,
  })),
)

// The same surface/ink pairings Avatar uses for a letter with no image: a tint
// behind, the matching ink on top, so a step reads as a state and not as a
// button.
const DOT = {
  done: 'bg-surface-green-2 text-ink-green-7',
  current: 'bg-surface-blue-2 text-ink-blue-7',
  upcoming: 'bg-surface-gray-2 text-ink-gray-5',
  cancelled: 'bg-surface-red-2 text-ink-red-7',
  returned: 'bg-surface-gray-2 text-ink-gray-6',
}

const LABEL = {
  done: 'text-ink-gray-8',
  current: 'text-ink-gray-9',
  upcoming: 'text-ink-gray-5',
  cancelled: 'text-ink-red-6',
  returned: 'text-ink-gray-6',
}

// A connector is filled up to the last step the order actually reached.
const REACHED = ['done', 'current', 'cancelled', 'returned']
const reached = (step) => Boolean(step) && REACHED.includes(step.tone)
</script>

<template>
  <div class="rounded-5 border border-outline-gray-1 px-5 py-4">
    <ol class="mx-auto flex max-w-2xl items-start">
      <li
        v-for="(step, index) in steps"
        :key="step.key"
        class="flex min-w-0 flex-1 flex-col items-center text-center"
      >
        <!-- The connectors carry the reading: filled up to where the order got. -->
        <div class="flex w-full items-center">
          <span
            class="h-px flex-1"
            :class="index === 0 ? 'bg-transparent' : reached(step) ? 'bg-surface-gray-5' : 'bg-surface-gray-3'"
            aria-hidden="true"
          />
          <span class="mx-2 grid size-8 shrink-0 place-content-center rounded-full" :class="DOT[step.tone]">
            <span :class="[step.tone === 'done' ? 'lucide-check' : step.icon, 'size-4']" aria-hidden="true" />
          </span>
          <span
            class="h-px flex-1"
            :class="
              index === steps.length - 1
                ? 'bg-transparent'
                : reached(steps[index + 1])
                  ? 'bg-surface-gray-5'
                  : 'bg-surface-gray-3'
            "
            aria-hidden="true"
          />
        </div>

        <p class="mt-2 max-w-full truncate text-base" :class="LABEL[step.tone]">{{ step.label }}</p>
        <p class="mt-0.5 max-w-full truncate text-sm text-ink-gray-5">{{ step.caption }}</p>
      </li>
    </ol>
  </div>
</template>

