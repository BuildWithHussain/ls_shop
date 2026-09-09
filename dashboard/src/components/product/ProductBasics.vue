<script setup>
import { FormControl } from 'frappe-ui'
import RichTextField from '../RichTextField.vue'
import Thumb from '../Thumb.vue'

defineProps({ product: { type: Object, required: true } })
</script>

<template>
  <section class="space-y-4">
    <FormControl v-model="product.title" label="Title" />
    <RichTextField
      v-model="product.description"
      label="Description"
      description="Shown on the product page."
      min-height="min-h-32"
    />
    <div>
      <p class="mb-1.5 text-base text-ink-gray-6">Media</p>
      <div class="flex flex-wrap gap-2">
        <Thumb :image="product.image" size="size-20" />
      </div>
    </div>
  </section>
</template>
