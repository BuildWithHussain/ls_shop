<script setup>
import { computed, ref, watch } from 'vue'
import { Avatar, TextInput } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import AppPageHeader from '../components/AppPageHeader.vue'
import PageBody from '../components/PageBody.vue'
import ListPagination from '../components/ListPagination.vue'
import { useAdminRead } from '../data/api'
import { longDate, money } from '../data/format'
import { ia } from '../ia/store'

const query = ref('')
const page = ref(1)
const pageSize = ref(20)

const customersRequest = useAdminRead('customers.get_customers', {
  params: () => ({
    search: query.value || undefined,
    start: (page.value - 1) * pageSize.value,
    page_length: pageSize.value,
  }),
  refetch: true,
})

// A search changes what page one is, so it sends you back to it.
watch(query, () => (page.value = 1))

const total = computed(() => customersRequest.data?.total ?? 0)
const rows = computed(() => customersRequest.data?.customers ?? [])
</script>

<template>
  <!-- No header actions: a customer record is created the moment a shopper checks out
       (commera/core.py's _create_party_for_user), and there is no export endpoint. -->
  <AppPageHeader title="Customers" />

  <PageBody>
    <TextInput v-model="query" class="w-56" placeholder="Search customers" icon-left="lucide-search" />

    <p v-if="customersRequest.loading" class="mt-3 text-sm text-ink-gray-5">Loading customers…</p>

    <div v-else class="mt-3 overflow-x-auto">
      <List
        class="min-w-[46rem]"
        :row-height="Math.max(ia.density, 44)"
        :columns="['1fr', '9rem', '6rem', '8rem', '9rem']"
      >
        <ListHeader>
          <ListHeaderCell>Customer</ListHeaderCell>
          <ListHeaderCell>City</ListHeaderCell>
          <ListHeaderCell>Orders</ListHeaderCell>
          <ListHeaderCell>Spend</ListHeaderCell>
          <ListHeaderCell>Customer since</ListHeaderCell>
        </ListHeader>
        <ListRows :items="rows" row-key="id" v-slot="{ item }">
          <ListRow :to="`/customers/${item.id}`" :value="item.id">
            <ListCell>
              <div class="flex min-w-0 items-center gap-2.5">
                <Avatar :label="item.name" size="sm" />
                <div class="min-w-0">
                  <p class="truncate text-base text-ink-gray-8">{{ item.name }}</p>
                  <p class="truncate text-sm text-ink-gray-5">{{ item.email ?? '—' }}</p>
                </div>
              </div>
            </ListCell>
            <ListCell><span class="text-base text-ink-gray-7">{{ item.city ?? '—' }}</span></ListCell>
            <ListCell><span class="text-base text-ink-gray-7 tabular-nums">{{ item.orders }}</span></ListCell>
            <ListCell><span class="text-base text-ink-gray-8 tabular-nums">{{ money(item.spend) }}</span></ListCell>
            <ListCell><span class="text-base text-ink-gray-5">{{ longDate(item.since) }}</span></ListCell>
          </ListRow>
        </ListRows>
      </List>
    </div>

    <ListPagination v-if="total" v-model:page="page" v-model:page-size="pageSize" :total="total" />
  </PageBody>
</template>

