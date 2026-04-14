<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex gap-1 items-center">
        <Button
          variant="ghost"
          icon-left="chevron-left"
          :label="__('WebSprix Settings')"
          size="md"
          class="cursor-pointer -ml-4 hover:bg-transparent focus:bg-transparent focus:outline-none focus:ring-0 focus:ring-offset-0 focus-visible:none active:bg-transparent active:outline-none active:ring-0 active:ring-offset-0 active:text-ink-gray-5 font-semibold text-xl hover:opacity-70 !pr-0 !max-w-96 !justify-start"
          @click="emit('updateStep', 'telephony-settings')"
        />
        <Badge
          v-if="websprix.doc?.enabled && isDirty"
          :label="__('Not Saved')"
          variant="subtle"
          theme="orange"
        />
      </div>
    </template>
    <template #header-actions>
      <div
        v-if="websprix.doc?.enabled && !websprix.get.loading"
        class="flex gap-2"
      >
        <Button
          v-if="isDirty"
          :label="__('Discard Changes')"
          variant="subtle"
          @click="websprix.reload()"
        />
        <Button :label="__('Disable')" variant="subtle" @click="disable" />
        <Button
          variant="solid"
          :label="__('Update')"
          :loading="websprix.save.loading"
          :disabled="!isDirty"
          @click="update"
        />
      </div>
    </template>
    <template #content>
      <div v-if="websprix.doc" class="h-full">
        <div v-if="websprix.doc.enabled" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <FormControl
              v-model="websprix.doc.customer_id"
              :label="__('Customer ID')"
              type="text"
              placeholder="cust_123"
              required
              autocomplete="off"
            />
            <FormControl
              v-model="websprix.doc.organization_id"
              :label="__('Organization ID')"
              type="text"
              placeholder="org_123"
              required
              autocomplete="off"
            />
            <FormControl
              v-model="websprix.doc.api_key"
              :label="__('API Key')"
              type="text"
              placeholder="api_************"
              required
              autocomplete="off"
            />
            <FormControl
              v-model="websprix.doc.base_url"
              :label="__('Base URL')"
              type="text"
              placeholder="https://etw-pbx-cloud1.websprix.com/api/v2"
              required
              autocomplete="off"
            />
          </div>
          <div class="h-px border-t border-outline-gray-modals" />
          <div class="flex items-center justify-between">
            <div class="flex flex-col">
              <div class="text-p-base font-medium text-ink-gray-7 truncate">
                {{ __('Record Outgoing Calls') }}
              </div>
              <div class="text-p-sm text-ink-gray-5 truncate">
                {{ __('Store a recording of every outgoing call') }}
              </div>
            </div>
            <div>
              <Switch v-model="websprix.doc.record_call" size="sm" />
            </div>
          </div>
        </div>
        <!--  Disabled state -->
        <div v-else class="relative flex h-full w-full justify-center">
          <div
            class="absolute left-1/2 flex w-64 -translate-x-1/2 flex-col items-center gap-3"
            :style="{ top: '35%' }"
          >
            <div class="flex flex-col items-center gap-1.5 text-center">
              <PhoneIcon class="size-7.5 text-ink-gray-7" />
              <span class="text-lg font-medium text-ink-gray-8">
                {{ __('WebSprix Integration Disabled') }}
              </span>
              <span class="text-center text-p-base text-ink-gray-6">
                {{
                  __(
                    'Enable WebSprix integration to make and receive SIP calls directly from your CRM',
                  )
                }}
              </span>
              <Button :label="__('Enable')" variant="solid" @click="enable" />
            </div>
          </div>
        </div>
      </div>
      <div
        v-else-if="websprix.get.loading"
        class="flex items-center justify-center mt-[35%]"
      >
        <LoadingIndicator class="size-6" />
      </div>
    </template>
  </SettingsLayoutBase>
</template>
<script setup>
import { websprixEnabled } from '@/composables/settings'
import { useDocument } from '@/data/document'
import { Switch } from 'frappe-ui'
import { computed } from 'vue'

const emit = defineEmits(['updateStep'])

const { document: websprix } = useDocument(
  'CRM WebSprix Settings',
  'CRM WebSprix Settings',
)

function enable() {
  websprix.doc.enabled = true
}

function disable() {
  websprix.doc.enabled = false
  update()
}

function update() {
  websprix.save.submit(null, {
    onSuccess: () => websprix.reload(),
  })

  websprixEnabled.value = websprix.doc.enabled
}

const isDirty = computed(() => {
  return (
    websprix.doc &&
    websprix.originalDoc &&
    JSON.stringify(websprix.doc) !== JSON.stringify(websprix.originalDoc)
  )
})
</script>
