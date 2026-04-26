<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Commissions') }]" />
    </template>
    <template #right-header>
      <div class="flex items-center gap-2">
        <FormControl
          v-model="filters.status"
          type="select"
          :options="[
            { label: __('All Statuses'), value: '' },
            { label: __('Pending'), value: 'Pending' },
            { label: __('Approved'), value: 'Approved' },
            { label: __('Paid'), value: 'Paid' },
            { label: __('Cancelled'), value: 'Cancelled' },
          ]"
          class="w-40"
          @change="loadData"
        />
        <FormControl
          v-model="filters.from_date"
          type="date"
          :placeholder="__('From')"
          class="w-40"
          @change="loadData"
        />
        <FormControl
          v-model="filters.to_date"
          type="date"
          :placeholder="__('To')"
          class="w-40"
          @change="loadData"
        />
        <FormControl
          v-if="isManager"
          v-model="selectedAgent"
          type="select"
          :options="agentOptions"
          class="w-56"
          @change="loadData"
        />
        <Button
          v-if="filters.status || filters.from_date || filters.to_date"
          variant="ghost"
          size="sm"
          :label="__('Clear')"
          @click="clearFilters"
        />
      </div>
    </template>
  </LayoutHeader>
  <div class="flex flex-col overflow-y-auto p-5">
    <!-- Summary Cards -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">{{ __('Pending') }}</div>
        <div class="mt-1 text-2xl font-semibold text-orange-600">
          {{ fmtAmount(summary.pending) }}
        </div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">{{ __('Approved') }}</div>
        <div class="mt-1 text-2xl font-semibold text-green-600">
          {{ fmtAmount(summary.approved) }}
        </div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">{{ __('Paid') }}</div>
        <div class="mt-1 text-2xl font-semibold text-blue-600">
          {{ fmtAmount(summary.paid) }}
        </div>
      </div>
    </div>

    <!-- Commission Records Table -->
    <div class="overflow-x-auto">
      <table v-if="summary.records?.length" class="w-full text-left">
        <thead>
          <tr class="text-sm text-ink-gray-5 border-b">
            <th v-if="isManager && selectedAgent === '__all__'" class="py-2 pr-4 font-medium">{{ __('Agent') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Deal') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Project') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Unit') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Role') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Rate %') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Amount') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Trigger') }}</th>
            <th class="py-2 font-medium">{{ __('Status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="rec in summary.records"
            :key="rec.name"
            class="border-b text-base text-ink-gray-7"
          >
            <td v-if="isManager && selectedAgent === '__all__'" class="py-2.5 pr-4">{{ rec.agent_name }}</td>
            <td class="py-2.5 pr-4 font-medium">{{ rec.deal }}</td>
            <td class="py-2.5 pr-4">{{ rec.project || '-' }}</td>
            <td class="py-2.5 pr-4">{{ rec.unit || '-' }}</td>
            <td class="py-2.5 pr-4">{{ rec.role }}</td>
            <td class="py-2.5 pr-4">{{ rec.commission_rate }}%</td>
            <td class="py-2.5 pr-4 font-medium">{{ fmtAmount(rec.final_commission) }}</td>
            <td class="py-2.5 pr-4">{{ rec.trigger_event }}</td>
            <td class="py-2.5">
              <Badge
                :variant="'subtle'"
                :theme="rec.status === 'Approved' ? 'green' : rec.status === 'Paid' ? 'blue' : rec.status === 'Cancelled' ? 'red' : 'orange'"
                :label="rec.status"
                size="sm"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="flex flex-col items-center justify-center py-16 text-ink-gray-5">
        <CommissionIcon class="h-12 w-12 mb-3" />
        <p class="text-base">{{ __('No commission records found') }}</p>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import CommissionIcon from '@/components/Icons/CommissionIcon.vue'
import { sessionStore } from '@/stores/session'
import { Badge, Breadcrumbs, Button, FormControl, call, toast } from 'frappe-ui'
import { ref, reactive, computed, onMounted } from 'vue'

const { user } = sessionStore()
const isManager = ref(false)
const selectedAgent = ref('')

const summary = reactive({
  pending: 0,
  approved: 0,
  paid: 0,
  records: [],
})

const filters = reactive({
  status: '',
  from_date: '',
  to_date: '',
})

function clearFilters() {
  filters.status = ''
  filters.from_date = ''
  filters.to_date = ''
  loadData()
}

const agentOptions = ref([])

function fmtAmount(val) {
  if (!val) return '0.00'
  return Number(val).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

async function checkManagerRole() {
  try {
    const roles = await call('frappe.client.get_list', {
      doctype: 'Has Role',
      filters: { parent: user, role: 'Sales Manager' },
      fields: ['name'],
      page_length: 1,
    })
    isManager.value = roles.length > 0
    if (isManager.value) {
      const users = await call('frappe.client.get_list', {
        doctype: 'User',
        filters: { enabled: 1 },
        fields: ['name', 'full_name'],
        page_length: 200,
      })
      agentOptions.value = [
        { label: __('My Commissions'), value: '' },
        { label: __('All Agents'), value: '__all__' },
        ...users.map((u) => ({ label: u.full_name || u.name, value: u.name })),
      ]
    }
  } catch {
    isManager.value = false
  }
}

async function loadData() {
  try {
    const data = await call(
      'crm.fcrm.doctype.sales_commission.sales_commission.get_agent_commission_summary',
      {
        agent: selectedAgent.value || undefined,
        from_date: filters.from_date || undefined,
        to_date: filters.to_date || undefined,
      },
    )
    summary.pending = data.pending || 0
    summary.approved = data.approved || 0
    summary.paid = data.paid || 0
    let records = data.records || []
    if (filters.status) {
      records = records.filter((r) => r.status === filters.status)
    }
    summary.records = records
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error loading commissions'))
  }
}

onMounted(async () => {
  await checkManagerRole()
  await loadData()
})
</script>
