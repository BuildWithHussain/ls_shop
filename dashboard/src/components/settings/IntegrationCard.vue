<script setup>
/**
 * One provider, one row: the mark, what state it is in, and the two things you came to
 * do — turn it on, or give it keys. Every piece of state is the server's answer, never a
 * local flag, so a card cannot claim a connection the site does not have.
 */
import { computed } from 'vue'
import { Badge, Button, Switch } from 'frappe-ui'
import BrandMark from './BrandMark.vue'
import { brandFor } from '../../data/integrations'

const props = defineProps({
  card: { type: Object, required: true },
  busy: { type: Boolean, default: false },
})

defineEmits(['configure', 'toggle'])

const brand = computed(() => brandFor(props.card.slug))
const needsKeys = computed(() => props.card.enabled && props.card.missing?.length > 0)
</script>

<template>
  <div class="flex items-center gap-3 py-3">
    <BrandMark :mark="brand.mark" :brand="brand.brand" size="size-8" />

    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <p class="truncate text-base text-ink-gray-8">{{ card.label }}</p>
        <Badge v-if="card.enabled" label="Live" theme="green" variant="subtle" />
        <!-- The app behind this provider is not installed on the site, so there is
             nothing to configure and the row says so rather than offering keys. -->
        <Badge v-if="!card.available" label="Not installed" theme="gray" variant="subtle" />
        <span v-if="needsKeys" class="shrink-0 text-sm text-ink-amber-7">Keys missing</span>
      </div>
      <p v-if="card.blurb" class="mt-1 truncate text-sm text-ink-gray-5">{{ card.blurb }}</p>
    </div>

    <div class="ml-auto flex shrink-0 items-center gap-3">
      <Button
        :label="card.configured ? 'Configure' : 'Add keys'"
        :disabled="!card.available"
        @click="$emit('configure', card.slug)"
      />
      <Switch
        :model-value="card.enabled"
        size="sm"
        :disabled="!card.available || busy"
        @update:model-value="$emit('toggle', $event)"
      />
    </div>
  </div>
</template>

