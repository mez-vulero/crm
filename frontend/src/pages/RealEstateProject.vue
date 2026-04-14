<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="breadcrumbs" />
    </template>
    <template v-if="doc.name" #right-header>
      <Dropdown :options="statusOptions" placement="right">
        <template #default="{ open }">
          <Button
            v-if="doc.status"
            :label="doc.status"
            :iconRight="open ? 'chevron-up' : 'chevron-down'"
          >
            <template #prefix>
              <div
                class="size-2 rounded-full"
                :class="statusDotClass(doc.status)"
              />
            </template>
          </Button>
        </template>
      </Dropdown>
    </template>
  </LayoutHeader>
  <div v-if="doc.name" class="flex h-full overflow-hidden">
    <div class="flex flex-1 flex-col overflow-y-auto">
      <!-- Project Header -->
      <div class="border-b px-5 py-4">
        <div class="flex items-start gap-4">
          <Avatar
            v-if="doc.image"
            size="3xl"
            class="size-16"
            :label="doc.project_name"
            :image="doc.image"
          />
          <div class="flex-1">
            <h2 class="text-2xl font-semibold text-ink-gray-9">
              {{ doc.project_name }}
            </h2>
            <div class="mt-1 flex items-center gap-3 text-base text-ink-gray-5">
              <span v-if="doc.city">{{ doc.city }}</span>
              <span v-if="doc.location && doc.city">-</span>
              <span v-if="doc.location">{{ doc.location }}</span>
            </div>
            <div
              v-if="doc.launch_date || doc.delivery_date"
              class="mt-1 flex items-center gap-3 text-sm text-ink-gray-4"
            >
              <span v-if="doc.launch_date">
                {{ __('Launch') }}: {{ formatDate(doc.launch_date) }}
              </span>
              <span v-if="doc.delivery_date">
                {{ __('Delivery') }}: {{ formatDate(doc.delivery_date) }}
              </span>
            </div>
          </div>
        </div>
        <!-- Unit Summary Cards -->
        <div class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            v-for="stat in unitStats"
            :key="stat.label"
            class="rounded-lg border p-3"
          >
            <div class="text-sm text-ink-gray-5">{{ stat.label }}</div>
            <div class="mt-1 text-xl font-semibold text-ink-gray-9">
              {{ stat.value }}
            </div>
          </div>
        </div>
      </div>

      <!-- Filter Bar -->
      <div class="flex items-center gap-3 border-b px-5 py-3">
        <FormControl
          v-model="filters.status"
          type="select"
          :label="__('Status')"
          :options="[
            { label: __('All Statuses'), value: '' },
            { label: __('Available'), value: 'Available' },
            { label: __('Reserved'), value: 'Reserved' },
            { label: __('Sold'), value: 'Sold' },
            { label: __('Blocked'), value: 'Blocked' },
          ]"
          class="w-40"
        />
        <FormControl
          v-model="filters.unit_type"
          type="select"
          :label="__('Unit Type')"
          :options="[
            { label: __('All Types'), value: '' },
            { label: 'Studio', value: 'Studio' },
            { label: '1BR', value: '1BR' },
            { label: '2BR', value: '2BR' },
            { label: '3BR', value: '3BR' },
            { label: '4BR', value: '4BR' },
            { label: 'Penthouse', value: 'Penthouse' },
          ]"
          class="w-40"
        />
        <div class="ml-auto flex items-center gap-3">
          <span class="text-sm text-ink-gray-5">
            {{ filteredUnits.length }} {{ __('units') }}
          </span>
          <Button
            variant="solid"
            :label="__('Add Unit')"
            iconLeft="plus"
            @click="showAddUnitDialog = true"
          />
        </div>
      </div>

      <!-- Bulk Actions Bar -->
      <div
        v-if="selectedUnits.length"
        class="flex items-center gap-3 px-5 py-2 bg-surface-gray-2 border-b"
      >
        <span class="text-sm text-ink-gray-7 font-medium">
          {{ selectedUnits.length }} {{ __('selected') }}
        </span>
        <Button
          variant="subtle"
          size="sm"
          :label="__('Block')"
          @click="bulkStatus('Blocked')"
        />
        <Button
          variant="subtle"
          size="sm"
          :label="__('Make Available')"
          @click="bulkStatus('Available')"
        />
        <Button
          variant="subtle"
          size="sm"
          :label="__('Adjust Price')"
          @click="showBulkPriceDialog = true"
        />
        <Button
          variant="ghost"
          size="sm"
          :label="__('Clear')"
          @click="selectedUnits = []"
        />
      </div>

      <!-- Unit Grid -->
      <div class="flex-1 overflow-y-auto">
        <table class="w-full">
          <thead class="sticky top-0 bg-surface-white">
            <tr class="text-left text-sm text-ink-gray-5">
              <th class="w-8 px-3 py-2">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  :indeterminate="someSelected"
                  class="rounded"
                  @change="toggleSelectAll"
                />
              </th>
              <th class="px-5 py-2 font-medium">{{ __('Unit') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Floor') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Type') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Size (sqm)') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Price') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('View') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="unit in filteredUnits"
              :key="unit.name"
              class="cursor-pointer border-t hover:bg-surface-gray-2 transition-colors"
              :class="{ 'bg-surface-gray-2': selectedUnits.includes(unit.name) }"
              @click="selectUnit(unit)"
            >
              <td class="w-8 px-3 py-2.5" @click.stop>
                <input
                  type="checkbox"
                  :checked="selectedUnits.includes(unit.name)"
                  class="rounded"
                  @change="toggleUnit(unit.name)"
                />
              </td>
              <td class="px-5 py-2.5 text-base font-medium text-ink-gray-9">
                {{ unit.unit_number }}
              </td>
              <td class="px-3 py-2.5 text-base text-ink-gray-7">
                {{ unit.floor || '-' }}
              </td>
              <td class="px-3 py-2.5 text-base text-ink-gray-7">
                {{ unit.unit_type || '-' }}
              </td>
              <td class="px-3 py-2.5 text-base text-ink-gray-7">
                {{ unit.size_sqm || '-' }}
              </td>
              <td class="px-3 py-2.5 text-base text-ink-gray-7">
                {{ formatPrice(unit) }}
              </td>
              <td class="px-3 py-2.5 text-base text-ink-gray-7">
                {{ unit.view_direction || '-' }}
              </td>
              <td class="px-3 py-2.5">
                <Badge
                  :variant="'subtle'"
                  :theme="unitStatusColor(unit.status)"
                  :label="unit.status"
                  size="md"
                />
              </td>
            </tr>
          </tbody>
        </table>
        <div
          v-if="!filteredUnits.length && !unitsLoading"
          class="flex items-center justify-center py-10 text-ink-gray-5"
        >
          {{ __('No units found') }}
        </div>
      </div>
    </div>
  </div>

  <!-- Unit Detail Dialog -->
  <Dialog
    v-model="showUnitDetail"
    :options="{ title: selectedUnit?.unit_number, size: 'xl' }"
  >
    <template #body-content>
      <div v-if="selectedUnit" class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Unit Type') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.unit_type || '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Floor') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.floor || '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Size (sqm)') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.size_sqm || '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Price') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ formatPrice(selectedUnit) }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">
              {{ __('View Direction') }}
            </div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.view_direction || '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Status') }}</div>
            <Badge
              :variant="'subtle'"
              :theme="unitStatusColor(selectedUnit.status)"
              :label="selectedUnit.status"
              size="md"
            />
          </div>
        </div>
        <div v-if="selectedUnit.notes">
          <div class="text-sm text-ink-gray-5">{{ __('Notes') }}</div>
          <div class="text-base text-ink-gray-7">{{ selectedUnit.notes }}</div>
        </div>
        <div v-if="selectedUnit.linked_deal">
          <div class="text-sm text-ink-gray-5">{{ __('Linked Deal') }}</div>
          <div class="text-base text-ink-gray-9">
            {{ selectedUnit.linked_deal }}
          </div>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex gap-2">
        <Button
          variant="outline"
          :label="__('Schedule Viewing')"
          @click="showViewingDialog = true"
        />
        <Button
          v-if="selectedUnit?.status === 'Available'"
          variant="solid"
          :label="__('Reserve Unit')"
          @click="showReserveDialog = true"
        />
      </div>
    </template>
  </Dialog>

  <!-- Schedule Viewing Dialog -->
  <Dialog
    v-model="showViewingDialog"
    :options="{ title: __('Schedule Viewing'), size: 'lg' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="text-base text-ink-gray-7">
          {{ __('Viewing for unit') }}: <strong>{{ selectedUnit?.unit_number }}</strong>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="viewingData.appointment_date"
            :label="__('Date')"
            type="date"
            required
          />
          <FormControl
            v-model="viewingData.appointment_time"
            :label="__('Time')"
            type="time"
          />
        </div>
        <FormControl
          v-model="viewingData.lead"
          :label="__('Link to Lead (optional)')"
          type="text"
          :placeholder="__('Lead ID')"
        />
        <FormControl
          v-model="viewingData.deal"
          :label="__('Link to Deal (optional)')"
          type="text"
          :placeholder="__('Deal ID')"
        />
        <FormControl
          v-model="viewingData.assigned_agent"
          :label="__('Assigned Agent (optional)')"
          type="text"
          :placeholder="__('user@example.com')"
        />
        <FormControl
          v-model="viewingData.notes"
          :label="__('Notes')"
          type="textarea"
        />
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        :label="__('Schedule')"
        :loading="schedulingViewing"
        @click="scheduleViewing"
      />
    </template>
  </Dialog>

  <!-- Reserve Unit Dialog -->
  <Dialog
    v-model="showReserveDialog"
    :options="{ title: __('Reserve Unit'), size: 'lg' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="text-base text-ink-gray-7">
          {{ __('Reserving unit') }}: <strong>{{ selectedUnit?.unit_number }}</strong>
        </div>
        <FormControl
          v-model="reservation.deal"
          :label="__('Link to Deal (optional)')"
          type="text"
          :placeholder="__('Deal ID')"
        />
        <FormControl
          v-model="reservation.lead"
          :label="__('Link to Lead (optional)')"
          type="text"
          :placeholder="__('Lead ID')"
        />
        <FormControl
          v-model="reservation.reservation_type"
          :label="__('Reservation Type')"
          type="select"
          :options="[
            { label: __('Soft'), value: 'Soft' },
            { label: __('Hard'), value: 'Hard' },
          ]"
        />
        <FormControl
          v-model="reservation.deposit_amount"
          :label="__('Deposit Amount')"
          type="number"
        />
        <FormControl
          v-model="reservation.expiry_date"
          :label="__('Expiry Date')"
          type="date"
        />
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        :label="__('Confirm Reservation')"
        :loading="reserving"
        @click="reserveUnit"
      />
    </template>
  </Dialog>

  <!-- Bulk Price Adjustment Dialog -->
  <Dialog
    v-model="showBulkPriceDialog"
    :options="{ title: __('Adjust Price'), size: 'md' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="text-base text-ink-gray-7">
          {{ __('Adjusting price for') }} <strong>{{ selectedUnits.length }}</strong> {{ __('units') }}
        </div>
        <FormControl
          v-model="bulkPriceForm.type"
          :label="__('Adjustment Type')"
          type="select"
          :options="[
            { label: __('Percentage (%)'), value: 'percentage' },
            { label: __('Fixed Amount'), value: 'fixed' },
          ]"
        />
        <FormControl
          v-model="bulkPriceForm.value"
          :label="bulkPriceForm.type === 'percentage' ? __('Percentage (e.g. 5 for +5%)') : __('Amount to add')"
          type="number"
        />
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        :label="__('Apply')"
        :loading="bulkUpdating"
        @click="bulkPrice"
      />
    </template>
  </Dialog>

  <!-- Add Unit Dialog -->
  <Dialog
    v-model="showAddUnitDialog"
    :options="{ title: __('Add Unit'), size: 'lg' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="newUnit.unit_number"
          :label="__('Unit Number')"
          type="text"
          :placeholder="__('e.g. A-101')"
        />
        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="newUnit.unit_type"
            :label="__('Unit Type')"
            type="select"
            :options="[
              { label: 'Studio', value: 'Studio' },
              { label: '1BR', value: '1BR' },
              { label: '2BR', value: '2BR' },
              { label: '3BR', value: '3BR' },
              { label: '4BR', value: '4BR' },
              { label: 'Penthouse', value: 'Penthouse' },
            ]"
          />
          <FormControl
            v-model="newUnit.floor"
            :label="__('Floor')"
            type="number"
          />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="newUnit.size_sqm"
            :label="__('Size (sqm)')"
            type="number"
          />
          <FormControl
            v-model="newUnit.base_price"
            :label="__('Base Price')"
            type="number"
          />
        </div>
        <FormControl
          v-model="newUnit.view_direction"
          :label="__('View Direction')"
          type="select"
          :options="[
            { label: __('None'), value: '' },
            { label: 'Garden', value: 'Garden' },
            { label: 'City', value: 'City' },
            { label: 'Sea', value: 'Sea' },
            { label: 'Courtyard', value: 'Courtyard' },
            { label: 'Street', value: 'Street' },
          ]"
        />
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        :label="__('Add')"
        :loading="addingUnit"
        @click="addUnit"
      />
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { formatDate } from '@/utils'
import { formatCurrency } from '@/utils/numberFormat'
import {
  Avatar,
  Badge,
  Breadcrumbs,
  Button,
  Dialog,
  Dropdown,
  FormControl,
  call,
  createListResource,
  createDocumentResource,
  toast,
} from 'frappe-ui'
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  projectId: { type: String, required: true },
})

const router = useRouter()

const breadcrumbs = computed(() => [
  { label: __('Properties'), route: { name: 'Real Estate' } },
  { label: doc.value.project_name || props.projectId },
])

const project = createDocumentResource({
  doctype: 'Real Estate Project',
  name: props.projectId,
  auto: true,
})

const doc = computed(() => project.doc || {})

const unitStats = computed(() => [
  { label: __('Total Units'), value: doc.value.total_units || 0 },
  { label: __('Available'), value: doc.value.available_units || 0 },
  { label: __('Reserved'), value: doc.value.reserved_units || 0 },
  { label: __('Sold'), value: doc.value.sold_units || 0 },
])

// Status management
const statusOptions = computed(() =>
  ['Pre-Launch', 'Active', 'Sold Out', 'Delivered'].map((s) => ({
    label: s,
    onClick: () => updateStatus(s),
  })),
)

async function updateStatus(status) {
  project.setValue.submit({ status })
}

function statusDotClass(status) {
  const classes = {
    'Pre-Launch': 'bg-blue-500',
    Active: 'bg-green-500',
    'Sold Out': 'bg-red-500',
    Delivered: 'bg-gray-500',
  }
  return classes[status] || 'bg-gray-500'
}

// Units
const filters = reactive({ status: '', unit_type: '' })

const unitFilters = computed(() => {
  const f = { project: props.projectId }
  if (filters.status) f.status = filters.status
  if (filters.unit_type) f.unit_type = filters.unit_type
  return f
})

const units = createListResource({
  doctype: 'Property Unit',
  fields: [
    'name',
    'unit_number',
    'floor',
    'unit_type',
    'size_sqm',
    'base_price',
    'price_override',
    'view_direction',
    'status',
    'notes',
    'linked_deal',
  ],
  filters: unitFilters.value,
  orderBy: 'floor asc, unit_number asc',
  pageLength: 999,
  auto: true,
})

watch(unitFilters, () => {
  units.update({ filters: unitFilters.value })
  units.reload()
})

const unitsLoading = computed(() => units.loading)

const filteredUnits = computed(() => units.data || [])

function formatPrice(unit) {
  const price = unit.price_override || unit.base_price
  if (!price) return '-'
  return formatCurrency(price)
}

function unitStatusColor(status) {
  const colors = {
    Available: 'green',
    Reserved: 'orange',
    Sold: 'red',
    Blocked: 'gray',
  }
  return colors[status] || 'gray'
}

// Unit detail
const showUnitDetail = ref(false)
const selectedUnit = ref(null)

function selectUnit(unit) {
  selectedUnit.value = unit
  showUnitDetail.value = true
}

// Reservation
const showReserveDialog = ref(false)
const reserving = ref(false)
const reservation = reactive({
  deal: '',
  lead: '',
  reservation_type: 'Soft',
  deposit_amount: 0,
  expiry_date: '',
})

async function reserveUnit() {
  reserving.value = true
  try {
    await call(
      'crm.fcrm.doctype.unit_reservation.unit_reservation.reserve_unit',
      {
        unit: selectedUnit.value.name,
        deal: reservation.deal || undefined,
        lead: reservation.lead || undefined,
        reservation_type: reservation.reservation_type,
        deposit_amount: reservation.deposit_amount,
        expiry_date: reservation.expiry_date || undefined,
      },
    )
    toast.success(__('Unit reserved successfully'))
    showReserveDialog.value = false
    showUnitDetail.value = false
    units.reload()
    project.reload()
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error reserving unit'))
  } finally {
    reserving.value = false
  }
}

// Bulk Operations
const selectedUnits = ref([])
const showBulkPriceDialog = ref(false)
const bulkUpdating = ref(false)
const bulkPriceForm = reactive({
  type: 'percentage',
  value: 0,
})

const allSelected = computed(
  () => filteredUnits.value.length > 0 && selectedUnits.value.length === filteredUnits.value.length,
)
const someSelected = computed(
  () => selectedUnits.value.length > 0 && selectedUnits.value.length < filteredUnits.value.length,
)

function toggleUnit(name) {
  const idx = selectedUnits.value.indexOf(name)
  if (idx >= 0) selectedUnits.value.splice(idx, 1)
  else selectedUnits.value.push(name)
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedUnits.value = []
  } else {
    selectedUnits.value = filteredUnits.value.map((u) => u.name)
  }
}

async function bulkStatus(status) {
  bulkUpdating.value = true
  try {
    const count = await call(
      'crm.fcrm.doctype.property_unit.property_unit.bulk_update_status',
      { units: selectedUnits.value, status },
    )
    toast.success(__(`${count} units updated to ${status}`))
    selectedUnits.value = []
    units.reload()
    project.reload()
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error'))
  } finally {
    bulkUpdating.value = false
  }
}

async function bulkPrice() {
  if (!bulkPriceForm.value) {
    toast.error(__('Enter a value'))
    return
  }
  bulkUpdating.value = true
  try {
    const count = await call(
      'crm.fcrm.doctype.property_unit.property_unit.bulk_update_price',
      {
        units: selectedUnits.value,
        adjustment_type: bulkPriceForm.type,
        adjustment_value: bulkPriceForm.value,
      },
    )
    toast.success(__(`${count} units updated`))
    selectedUnits.value = []
    showBulkPriceDialog.value = false
    Object.assign(bulkPriceForm, { type: 'percentage', value: 0 })
    units.reload()
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error'))
  } finally {
    bulkUpdating.value = false
  }
}

// Viewing Appointment
const showViewingDialog = ref(false)
const schedulingViewing = ref(false)
const viewingData = reactive({
  appointment_date: '',
  appointment_time: '',
  lead: '',
  deal: '',
  assigned_agent: '',
  notes: '',
})

async function scheduleViewing() {
  if (!viewingData.appointment_date) {
    toast.error(__('Date is required'))
    return
  }
  schedulingViewing.value = true
  try {
    await call(
      'crm.fcrm.doctype.viewing_appointment.viewing_appointment.schedule_viewing',
      {
        appointment_date: viewingData.appointment_date,
        appointment_time: viewingData.appointment_time || undefined,
        project: props.projectId,
        unit: selectedUnit.value?.name,
        lead: viewingData.lead || undefined,
        deal: viewingData.deal || undefined,
        assigned_agent: viewingData.assigned_agent || undefined,
        notes: viewingData.notes || undefined,
      },
    )
    toast.success(__('Viewing scheduled'))
    showViewingDialog.value = false
    Object.assign(viewingData, { appointment_date: '', appointment_time: '', lead: '', deal: '', assigned_agent: '', notes: '' })
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error scheduling viewing'))
  } finally {
    schedulingViewing.value = false
  }
}

// Add Unit
const showAddUnitDialog = ref(false)
const addingUnit = ref(false)
const newUnit = reactive({
  unit_number: '',
  unit_type: 'Studio',
  floor: '',
  size_sqm: '',
  base_price: '',
  view_direction: '',
})

async function addUnit() {
  if (!newUnit.unit_number) {
    toast.error(__('Unit Number is required'))
    return
  }
  addingUnit.value = true
  try {
    await call('frappe.client.insert', {
      doc: {
        doctype: 'Property Unit',
        project: props.projectId,
        unit_number: newUnit.unit_number,
        unit_type: newUnit.unit_type,
        floor: newUnit.floor || 0,
        size_sqm: newUnit.size_sqm || 0,
        base_price: newUnit.base_price || 0,
        view_direction: newUnit.view_direction || '',
        status: 'Available',
      },
    })
    toast.success(__('Unit added'))
    showAddUnitDialog.value = false
    newUnit.unit_number = ''
    newUnit.floor = ''
    newUnit.size_sqm = ''
    newUnit.base_price = ''
    newUnit.view_direction = ''
    units.reload()
    project.reload()
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error adding unit'))
  } finally {
    addingUnit.value = false
  }
}
</script>
