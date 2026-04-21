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
              <span v-if="doc.project_type" class="font-medium text-ink-gray-7">
                {{ doc.project_type }}
              </span>
              <span v-if="doc.project_type && (doc.city || doc.location)">·</span>
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
          <Button
            v-if="doc.image"
            variant="subtle"
            iconLeft="image"
            :label="__('View Property Image')"
            @click="openImagePreview(doc.image, doc.project_name)"
          />
        </div>
        <!-- Unit Summary Cards -->
        <div class="mt-4 grid grid-cols-4 gap-3">
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

        <!-- Specifications -->
        <div v-if="hasSpecs" class="mt-4">
          <div class="mb-2 text-sm font-medium text-ink-gray-5">
            {{ __('Specifications') }}
          </div>
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <div
              v-for="spec in specsList"
              :key="spec.label"
              class="rounded-lg border p-3"
            >
              <div class="text-xs text-ink-gray-5">{{ spec.label }}</div>
              <div class="mt-1 text-base font-semibold text-ink-gray-9">
                {{ spec.value }}
              </div>
            </div>
          </div>
        </div>

        <!-- Amenities -->
        <div v-if="amenityChips.length" class="mt-4">
          <div class="mb-2 text-sm font-medium text-ink-gray-5">
            {{ __('Amenities') }}
          </div>
          <div class="flex flex-wrap gap-2">
            <Badge
              v-for="amenity in amenityChips"
              :key="amenity"
              variant="subtle"
              theme="blue"
              :label="amenity"
              size="md"
            />
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
        <div class="w-48">
          <label class="block text-xs text-ink-gray-5 mb-1">{{ __('Unit Type') }}</label>
          <Link
            class="form-control"
            size="sm"
            :value="filters.unit_type"
            doctype="CRM Unit Type"
            :placeholder="__('All Types')"
            @change="(v) => (filters.unit_type = v || '')"
          />
        </div>
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

      <!-- Unit Grid -->
      <div class="flex-1 overflow-y-auto">
        <table class="w-full">
          <thead class="sticky top-0 bg-surface-white">
            <tr class="text-left text-sm text-ink-gray-5">
              <th class="px-5 py-2 font-medium">{{ __('Unit') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Floor') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Type') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Bed/Bath') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Size (sqm)') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Price') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('View') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Floor Plan') }}</th>
              <th class="px-3 py-2 font-medium">{{ __('Status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="unit in filteredUnits"
              :key="unit.name"
              class="cursor-pointer border-t hover:bg-surface-gray-2 transition-colors"
              @click="selectUnit(unit)"
            >
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
                {{ formatBedBath(unit) }}
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
              <td class="px-3 py-2.5" @click.stop>
                <Button
                  v-if="unit.floor_plan"
                  variant="subtle"
                  size="sm"
                  :label="__('View')"
                  @click="openImagePreview(unit.floor_plan, `${unit.unit_number} \u2014 ${__('Floor Plan')}`)"
                />
                <span v-else class="text-ink-gray-4">-</span>
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
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
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
            <div class="text-sm text-ink-gray-5">{{ __('Bedrooms') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.bedrooms ?? '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Bathrooms') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.bathrooms ?? '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Kitchens') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.kitchen_count ?? '-' }}
              <span v-if="selectedUnit.kitchen_layout" class="text-ink-gray-5 text-sm">
                ({{ selectedUnit.kitchen_layout }})
              </span>
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Balconies') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.balcony_count ?? '-' }}
              <span v-if="selectedUnit.balcony_size_sqm" class="text-ink-gray-5 text-sm">
                ({{ selectedUnit.balcony_size_sqm }} {{ __('sqm') }})
              </span>
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Parking') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.unit_parking_spaces ?? '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Furnishing') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.furnishing || '-' }}
            </div>
          </div>
          <div>
            <div class="text-sm text-ink-gray-5">{{ __('Ceiling Height (m)') }}</div>
            <div class="text-base text-ink-gray-9">
              {{ selectedUnit.ceiling_height_m ?? '-' }}
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
        <div class="flex flex-wrap gap-2">
          <Badge v-if="selectedUnit.has_laundry_room" variant="subtle" theme="green" :label="__('Laundry Room')" />
          <Badge v-if="selectedUnit.maid_room" variant="subtle" theme="green" :label="__('Maid Room')" />
          <Badge v-if="selectedUnit.storage_room" variant="subtle" theme="green" :label="__('Storage Room')" />
        </div>
        <div v-if="selectedUnit.floor_plan" class="pt-2">
          <Button
            variant="subtle"
            iconLeft="image"
            :label="__('View Floor Plan')"
            @click="openImagePreview(selectedUnit.floor_plan, `${selectedUnit.unit_number} \u2014 ${__('Floor Plan')}`)"
          />
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
      <Button
        v-if="selectedUnit?.status === 'Available'"
        variant="solid"
        :label="__('Reserve Unit')"
        @click="showReserveDialog = true"
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
        <div class="space-y-1.5">
          <label class="block text-xs text-ink-gray-5">{{ __('Link to Deal') }}</label>
          <Link
            class="form-control"
            size="md"
            :value="reservation.deal"
            doctype="CRM Deal"
            :placeholder="__('Search Deal')"
            @change="(v) => (reservation.deal = v || '')"
          />
        </div>
        <div class="space-y-1.5">
          <label class="block text-xs text-ink-gray-5">{{ __('Link to Lead') }}</label>
          <Link
            class="form-control"
            size="md"
            :value="reservation.lead"
            doctype="CRM Lead"
            :placeholder="__('Search Lead')"
            @change="(v) => (reservation.lead = v || '')"
          />
        </div>
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
          <div class="space-y-1.5">
            <label class="block text-xs text-ink-gray-5">{{ __('Unit Type') }}</label>
            <Link
              class="form-control"
              size="md"
              :value="newUnit.unit_type"
              doctype="CRM Unit Type"
              :placeholder="__('Search Unit Type')"
              @change="(v) => (newUnit.unit_type = v || '')"
            />
          </div>
          <FormControl
            v-model="newUnit.floor"
            :label="__('Floor')"
            type="number"
          />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="newUnit.bedrooms"
            :label="__('Bedrooms')"
            type="number"
          />
          <FormControl
            v-model="newUnit.bathrooms"
            :label="__('Bathrooms')"
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

  <!-- Image Preview Dialog -->
  <Dialog
    v-model="showImagePreview"
    :options="{ title: imagePreview.title, size: '4xl' }"
  >
    <template #body-content>
      <img
        v-if="imagePreview.url"
        :src="imagePreview.url"
        class="m-auto max-h-[70vh] rounded border"
        :alt="imagePreview.title"
      />
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import Link from '@/components/Controls/Link.vue'
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

const specsList = computed(() => {
  const d = doc.value
  const items = []
  if (d.project_type) items.push({ label: __('Type'), value: d.project_type })
  if (d.number_of_stories) items.push({ label: __('Stories'), value: d.number_of_stories })
  if (d.gross_building_area)
    items.push({ label: __('Built (sqm)'), value: d.gross_building_area })
  if (d.total_land_area)
    items.push({ label: __('Land (sqm)'), value: d.total_land_area })
  if (d.parking_spaces) items.push({ label: __('Parking'), value: d.parking_spaces })
  if (d.elevators) items.push({ label: __('Elevators'), value: d.elevators })
  return items
})

const hasSpecs = computed(() => specsList.value.length > 0)

const amenityChips = computed(() =>
  (doc.value.amenities || []).map((row) => row.amenity).filter(Boolean),
)

// Image preview
const showImagePreview = ref(false)
const imagePreview = reactive({ url: '', title: '' })

function openImagePreview(url, title) {
  if (!url) return
  imagePreview.url = url
  imagePreview.title = title || __('Preview')
  showImagePreview.value = true
}

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
    'bedrooms',
    'bathrooms',
    'kitchen_count',
    'kitchen_layout',
    'has_laundry_room',
    'balcony_count',
    'balcony_size_sqm',
    'maid_room',
    'storage_room',
    'unit_parking_spaces',
    'furnishing',
    'ceiling_height_m',
    'floor_plan',
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

function formatBedBath(unit) {
  const bd = unit.bedrooms
  const ba = unit.bathrooms
  if (!bd && !ba) return '-'
  return `${bd ?? 0} / ${ba ?? 0}`
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

// Add Unit
const showAddUnitDialog = ref(false)
const addingUnit = ref(false)
const newUnit = reactive({
  unit_number: '',
  unit_type: '',
  floor: '',
  size_sqm: '',
  base_price: '',
  view_direction: '',
  bedrooms: '',
  bathrooms: '',
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
        unit_type: newUnit.unit_type || null,
        floor: newUnit.floor || 0,
        size_sqm: newUnit.size_sqm || 0,
        base_price: newUnit.base_price || 0,
        view_direction: newUnit.view_direction || '',
        bedrooms: newUnit.bedrooms || 0,
        bathrooms: newUnit.bathrooms || 0,
        status: 'Available',
      },
    })
    toast.success(__('Unit added'))
    showAddUnitDialog.value = false
    newUnit.unit_number = ''
    newUnit.unit_type = ''
    newUnit.floor = ''
    newUnit.size_sqm = ''
    newUnit.base_price = ''
    newUnit.view_direction = ''
    newUnit.bedrooms = ''
    newUnit.bathrooms = ''
    units.reload()
    project.reload()
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error adding unit'))
  } finally {
    addingUnit.value = false
  }
}
</script>
