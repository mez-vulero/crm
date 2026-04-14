<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Viewings') }]" />
    </template>
    <template #right-header>
      <div class="flex gap-2">
        <FormControl
          v-model="statusFilter"
          type="select"
          :options="statusOptions"
          class="w-40"
          @change="loadData"
        />
        <Button
          variant="solid"
          :label="__('Schedule Viewing')"
          iconLeft="plus"
          @click="showDialog = true"
        />
      </div>
    </template>
  </LayoutHeader>
  <div class="flex flex-col overflow-y-auto p-5">
    <!-- Summary Cards -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-6">
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">{{ __('Scheduled') }}</div>
        <div class="mt-1 text-2xl font-semibold text-orange-600">
          {{ counts.scheduled }}
        </div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">{{ __('Completed') }}</div>
        <div class="mt-1 text-2xl font-semibold text-green-600">
          {{ counts.completed }}
        </div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">{{ __('No-Show') }}</div>
        <div class="mt-1 text-2xl font-semibold text-red-600">
          {{ counts.noshow }}
        </div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">{{ __('Cancelled') }}</div>
        <div class="mt-1 text-2xl font-semibold text-gray-500">
          {{ counts.cancelled }}
        </div>
      </div>
    </div>

    <!-- Appointments Table -->
    <div class="overflow-x-auto">
      <table v-if="appointments.length" class="w-full text-left">
        <thead>
          <tr class="text-sm text-ink-gray-5 border-b">
            <th class="py-2 pr-4 font-medium">{{ __('Date') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Time') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Status') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Agent') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Lead') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Deal') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Project') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Unit') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Feedback') }}</th>
            <th class="py-2 font-medium">{{ __('Actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="apt in appointments"
            :key="apt.name"
            class="border-b text-base text-ink-gray-7"
          >
            <td class="py-2.5 pr-4">{{ apt.appointment_date }}</td>
            <td class="py-2.5 pr-4">{{ apt.appointment_time || '-' }}</td>
            <td class="py-2.5 pr-4">
              <Badge
                :variant="'subtle'"
                :theme="apt.status === 'Completed' ? 'green' : apt.status === 'No-Show' ? 'red' : apt.status === 'Cancelled' ? 'gray' : 'orange'"
                :label="apt.status"
                size="sm"
              />
            </td>
            <td class="py-2.5 pr-4">{{ apt.assigned_agent || '-' }}</td>
            <td class="py-2.5 pr-4">{{ apt.lead || '-' }}</td>
            <td class="py-2.5 pr-4">{{ apt.deal || '-' }}</td>
            <td class="py-2.5 pr-4">{{ apt.project || '-' }}</td>
            <td class="py-2.5 pr-4">{{ apt.unit || '-' }}</td>
            <td class="py-2.5 pr-4 max-w-[12rem] truncate">{{ apt.feedback || '-' }}</td>
            <td class="py-2.5">
              <div v-if="apt.status === 'Scheduled'" class="flex gap-1">
                <Button variant="subtle" size="sm" :label="__('Complete')" @click="updateStatus(apt.name, 'Completed')" />
                <Button variant="ghost" size="sm" :label="__('No-Show')" @click="updateStatus(apt.name, 'No-Show')" />
                <Button variant="ghost" size="sm" :label="__('Cancel')" @click="updateStatus(apt.name, 'Cancelled')" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="flex flex-col items-center justify-center py-16 text-ink-gray-5">
        <CalendarIcon class="h-12 w-12 mb-3" />
        <p class="text-base">{{ __('No viewing appointments found') }}</p>
      </div>
    </div>
  </div>

  <!-- Schedule Viewing Dialog -->
  <Dialog v-model="showDialog" :options="{ title: __('Schedule Viewing'), size: 'lg' }">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-4">
          <FormControl v-model="form.appointment_date" :label="__('Date')" type="date" required />
          <FormControl v-model="form.appointment_time" :label="__('Time')" type="time" />
        </div>
        <FormControl v-model="form.lead" :label="__('Lead')" type="text" :placeholder="__('Lead ID')" />
        <FormControl v-model="form.deal" :label="__('Deal')" type="text" :placeholder="__('Deal ID')" />
        <FormControl v-model="form.project" :label="__('Project')" type="text" :placeholder="__('Real Estate Project ID')" />
        <FormControl v-model="form.unit" :label="__('Unit')" type="text" :placeholder="__('Property Unit ID')" />
        <FormControl v-model="form.assigned_agent" :label="__('Assigned Agent')" type="text" :placeholder="__('user@example.com')" />
        <FormControl v-model="form.notes" :label="__('Notes')" type="textarea" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Schedule')" @click="scheduleViewing" />
    </template>
  </Dialog>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import { Badge, Breadcrumbs, Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { ref, reactive, computed, onMounted } from 'vue'

const statusFilter = ref('')
const statusOptions = [
  { label: __('All Statuses'), value: '' },
  { label: __('Scheduled'), value: 'Scheduled' },
  { label: __('Completed'), value: 'Completed' },
  { label: __('No-Show'), value: 'No-Show' },
  { label: __('Cancelled'), value: 'Cancelled' },
]

const appointments = ref([])

const counts = computed(() => {
  const all = appointments.value
  return {
    scheduled: all.filter((a) => a.status === 'Scheduled').length,
    completed: all.filter((a) => a.status === 'Completed').length,
    noshow: all.filter((a) => a.status === 'No-Show').length,
    cancelled: all.filter((a) => a.status === 'Cancelled').length,
  }
})

const showDialog = ref(false)
const form = ref({
  appointment_date: '',
  appointment_time: '',
  lead: '',
  deal: '',
  project: '',
  unit: '',
  assigned_agent: '',
  notes: '',
})

async function loadData() {
  try {
    const filters = {}
    if (statusFilter.value) filters.status = statusFilter.value

    const data = await call('frappe.client.get_list', {
      doctype: 'Viewing Appointment',
      filters,
      fields: [
        'name', 'appointment_date', 'appointment_time', 'status',
        'assigned_agent', 'lead', 'deal', 'project', 'unit',
        'feedback', 'notes',
      ],
      order_by: 'appointment_date desc, appointment_time desc',
      page_length: 200,
    })
    appointments.value = data || []
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error loading appointments'))
  }
}

async function scheduleViewing() {
  if (!form.value.appointment_date) {
    toast.error(__('Date is required'))
    return
  }
  try {
    await call(
      'crm.fcrm.doctype.viewing_appointment.viewing_appointment.schedule_viewing',
      {
        appointment_date: form.value.appointment_date,
        appointment_time: form.value.appointment_time || undefined,
        lead: form.value.lead || undefined,
        deal: form.value.deal || undefined,
        project: form.value.project || undefined,
        unit: form.value.unit || undefined,
        assigned_agent: form.value.assigned_agent || undefined,
        notes: form.value.notes || undefined,
      },
    )
    showDialog.value = false
    form.value = { appointment_date: '', appointment_time: '', lead: '', deal: '', project: '', unit: '', assigned_agent: '', notes: '' }
    await loadData()
    toast.success(__('Viewing scheduled'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error scheduling viewing'))
  }
}

async function updateStatus(name, status) {
  try {
    await call(
      'crm.fcrm.doctype.viewing_appointment.viewing_appointment.update_status',
      { appointment_name: name, status },
    )
    await loadData()
    toast.success(__('Status updated'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error'))
  }
}

onMounted(() => loadData())
</script>
