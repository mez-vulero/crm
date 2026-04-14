<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Real Estate" />
    </template>
    <template #right-header>
      <Button
        variant="solid"
        :label="__('Create')"
        iconLeft="plus"
        @click="showCreateDialog = true"
      />
    </template>
  </LayoutHeader>
  <!-- Dashboard Summary -->
  <div v-if="dashboard.data" class="mx-3 sm:mx-5 mt-4 mb-2 grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
    <!-- Sales Funnel -->
    <div class="rounded-lg border p-4">
      <div class="text-sm font-medium text-ink-gray-5 mb-2">{{ __('Unit Inventory') }}</div>
      <div class="text-2xl font-semibold text-ink-gray-9">{{ dashboard.data.unit_funnel?.total || 0 }}</div>
      <div class="mt-2 flex gap-3 text-xs">
        <span class="text-green-600">{{ dashboard.data.unit_funnel?.available || 0 }} {{ __('Available') }}</span>
        <span class="text-orange-600">{{ dashboard.data.unit_funnel?.reserved || 0 }} {{ __('Reserved') }}</span>
        <span class="text-red-600">{{ dashboard.data.unit_funnel?.sold || 0 }} {{ __('Sold') }}</span>
      </div>
    </div>
    <!-- Revenue -->
    <div class="rounded-lg border p-4">
      <div class="text-sm font-medium text-ink-gray-5 mb-2">{{ __('Revenue Collection') }}</div>
      <div class="text-2xl font-semibold text-green-600">{{ fmtAmount(dashboard.data.revenue?.collected) }}</div>
      <div class="mt-2 text-xs text-ink-gray-5">
        {{ __('of') }} {{ fmtAmount(dashboard.data.revenue?.scheduled) }} {{ __('scheduled') }}
      </div>
    </div>
    <!-- Overdue -->
    <div class="rounded-lg border p-4">
      <div class="text-sm font-medium text-ink-gray-5 mb-2">{{ __('Overdue Payments') }}</div>
      <div class="text-2xl font-semibold" :class="(dashboard.data.overdue?.count || 0) > 0 ? 'text-red-600' : 'text-green-600'">
        {{ dashboard.data.overdue?.count || 0 }}
      </div>
      <div class="mt-2 text-xs text-ink-gray-5">
        {{ fmtAmount(dashboard.data.overdue?.amount) }} {{ __('overdue') }}
      </div>
    </div>
    <!-- Commissions -->
    <div class="rounded-lg border p-4">
      <div class="text-sm font-medium text-ink-gray-5 mb-2">{{ __('Commissions Payable') }}</div>
      <div class="text-2xl font-semibold text-orange-600">{{ fmtAmount(dashboard.data.commissions?.pending) }}</div>
      <div class="mt-2 flex gap-3 text-xs">
        <span class="text-green-600">{{ fmtAmount(dashboard.data.commissions?.approved) }} {{ __('approved') }}</span>
        <span class="text-blue-600">{{ fmtAmount(dashboard.data.commissions?.paid) }} {{ __('paid') }}</span>
      </div>
    </div>
  </div>
  <ViewControls
    ref="viewControls"
    v-model="projects"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="Real Estate Project"
  />
  <RealEstateListView
    v-if="projects.data && rows.length"
    v-model="projects.data.page_length_count"
    v-model:list="projects"
    :rows="rows"
    :columns="columns"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      rowCount: projects.data.row_count,
      totalCount: projects.data.total_count,
    }"
    @loadMore="() => loadMore++"
    @columnWidthUpdated="() => triggerResize++"
    @updatePageCount="(count) => (updatedPageCount = count)"
    @applyFilter="(data) => viewControls.applyFilter(data)"
  />
  <EmptyState
    v-else-if="projects.data && !rows.length"
    name="Real Estate Projects"
    :icon="BuildingIcon"
  />
  <Dialog
    v-model="showCreateDialog"
    :options="{ title: __('Create Project'), size: 'lg' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="newProject.project_name"
          :label="__('Project Name')"
          type="text"
          :placeholder="__('Enter project name')"
        />
        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="newProject.status"
            :label="__('Status')"
            type="select"
            :options="[
              { label: __('Pre-Launch'), value: 'Pre-Launch' },
              { label: __('Active'), value: 'Active' },
              { label: __('Sold Out'), value: 'Sold Out' },
              { label: __('Delivered'), value: 'Delivered' },
            ]"
          />
          <FormControl
            v-model="newProject.city"
            :label="__('City')"
            type="text"
            :placeholder="__('Enter city')"
          />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="newProject.location"
            :label="__('Location')"
            type="text"
            :placeholder="__('Enter location')"
          />
          <FormControl
            v-model="newProject.launch_date"
            :label="__('Launch Date')"
            type="date"
          />
        </div>
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        :label="__('Create')"
        :loading="creating"
        @click="createProject"
      />
    </template>
  </Dialog>
</template>
<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import BuildingIcon from '@/components/Icons/BuildingIcon.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import RealEstateListView from '@/components/ListViews/RealEstateListView.vue'
import ViewControls from '@/components/ViewControls.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import { getMeta } from '@/stores/meta'
import { formatDate, timeAgo } from '@/utils'
import { Dialog, FormControl, call, toast, createResource } from 'frappe-ui'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const { getFormattedCurrency } = getMeta('Real Estate Project')

const dashboard = createResource({
  url: 'crm.fcrm.doctype.real_estate_project.real_estate_project.get_real_estate_dashboard',
  auto: true,
})

function fmtAmount(val) {
  if (!val) return '0.00'
  return Number(val).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const projects = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const showCreateDialog = ref(false)
const creating = ref(false)
const newProject = ref({
  project_name: '',
  status: 'Active',
  city: '',
  location: '',
  launch_date: '',
})

const rows = computed(() => {
  if (
    !projects.value?.data?.data ||
    !['list', 'group_by'].includes(projects.value.data.view_type)
  )
    return []
  return projects.value?.data.data.map((project) => {
    let _rows = {}
    projects.value?.data.rows.forEach((row) => {
      _rows[row] = project[row]

      let fieldType = projects.value?.data.columns?.find(
        (col) => (col.key || col.value) == row,
      )?.type

      if (
        fieldType &&
        ['Date', 'Datetime'].includes(fieldType) &&
        !['modified', 'creation'].includes(row)
      ) {
        _rows[row] = formatDate(
          project[row],
          '',
          true,
          fieldType == 'Datetime',
        )
      }

      if (fieldType && fieldType == 'Currency') {
        _rows[row] = getFormattedCurrency(row, project)
      }

      if (['modified', 'creation'].includes(row)) {
        _rows[row] = {
          label: formatDate(project[row]),
          timeAgo: __(timeAgo(project[row])),
        }
      }
    })
    return _rows
  })
})

const columns = computed(() => {
  let _columns = projects.value?.data?.columns || []

  if (_columns.length) {
    _columns = _columns.map((col, index) => {
      if (index === _columns.length - 1) {
        return { ...col, align: 'right' }
      }
      return col
    })
  }

  return _columns
})

async function createProject() {
  if (!newProject.value.project_name) {
    toast.error(__('Project Name is required'))
    return
  }
  creating.value = true
  try {
    const doc = await call('frappe.client.insert', {
      doc: {
        doctype: 'Real Estate Project',
        ...newProject.value,
      },
    })
    showCreateDialog.value = false
    toast.success(__('Project created'))
    router.push({
      name: 'RealEstateProject',
      params: { projectId: doc.name },
    })
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error creating project'))
  } finally {
    creating.value = false
  }
}
</script>
