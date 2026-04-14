<template>
  <TwilioCallUI v-if="twilioEnabled" ref="twilio" />
  <ExotelCallUI v-if="exotelEnabled" ref="exotel" />
  <WebsprixCallUI v-if="websprixEnabled" ref="websprix" />
  <Dialog
    v-model="show"
    :options="{
      title: __('Make Call'),
      actions: [
        {
          label: __('Call using {0}', [callMedium]),
          variant: 'solid',
          onClick: makeCallUsing,
        },
      ],
    }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="mobileNumber"
          type="text"
          :label="__('Mobile Number')"
        />
        <FormControl
          v-model="callMedium"
          type="select"
          :label="__('Calling Medium')"
          :options="enabledMediums"
        />
        <div class="flex flex-col gap-1">
          <FormControl
            v-model="isDefaultMedium"
            type="checkbox"
            :label="__('Make {0} as default calling medium', [callMedium])"
          />

          <div v-if="isDefaultMedium" class="text-sm text-ink-gray-4">
            {{
              __('You can change the default calling medium from the settings')
            }}
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script setup>
import TwilioCallUI from '@/components/Telephony/TwilioCallUI.vue'
import ExotelCallUI from '@/components/Telephony/ExotelCallUI.vue'
import WebsprixCallUI from '@/components/Telephony/WebsprixCallUI.vue'
import {
  twilioEnabled,
  exotelEnabled,
  websprixEnabled,
  defaultCallingMedium,
} from '@/composables/settings'
import { globalStore } from '@/stores/global'
import { FormControl, call, toast } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'

const { setMakeCall } = globalStore()

const twilio = ref(null)
const exotel = ref(null)
const websprix = ref(null)

const callMedium = ref('Twilio')
const isDefaultMedium = ref(false)

const show = ref(false)
const mobileNumber = ref('')

const enabledMediums = computed(() => {
  const mediums = []
  if (twilioEnabled.value) mediums.push('Twilio')
  if (exotelEnabled.value) mediums.push('Exotel')
  if (websprixEnabled.value) mediums.push('WebSprix')
  return mediums
})

function pickFirstEnabled() {
  if (twilioEnabled.value) return 'Twilio'
  if (exotelEnabled.value) return 'Exotel'
  if (websprixEnabled.value) return 'WebSprix'
  return ''
}

function countEnabled() {
  return (
    (twilioEnabled.value ? 1 : 0) +
    (exotelEnabled.value ? 1 : 0) +
    (websprixEnabled.value ? 1 : 0)
  )
}

function makeCall(number) {
  // Show picker if >1 provider is enabled and no default has been chosen
  if (countEnabled() > 1 && !defaultCallingMedium.value) {
    callMedium.value = pickFirstEnabled()
    mobileNumber.value = number
    show.value = true
    return
  }

  callMedium.value = pickFirstEnabled()
  if (defaultCallingMedium.value) {
    callMedium.value = defaultCallingMedium.value
  }

  mobileNumber.value = number
  makeCallUsing()
}

function makeCallUsing() {
  if (isDefaultMedium.value && callMedium.value) {
    setDefaultCallingMedium()
  }

  if (callMedium.value === 'Twilio') {
    twilio.value?.makeOutgoingCall(mobileNumber.value)
  } else if (callMedium.value === 'Exotel') {
    exotel.value?.makeOutgoingCall(mobileNumber.value)
  } else if (callMedium.value === 'WebSprix') {
    websprix.value?.makeOutgoingCall(mobileNumber.value)
  }
  show.value = false
}

async function setDefaultCallingMedium() {
  await call('crm.integrations.api.set_default_calling_medium', {
    medium: callMedium.value,
  })

  defaultCallingMedium.value = callMedium.value
  toast.success(
    __('Default calling medium set successfully to {0}', [callMedium.value]),
  )
}

watch(
  [twilioEnabled, exotelEnabled, websprixEnabled],
  ([twilioValue, exotelValue, websprixValue]) =>
    nextTick(() => {
      if (twilioValue) {
        twilio.value?.setup()
      }

      if (exotelValue) {
        exotel.value?.setup()
      }

      if (websprixValue) {
        websprix.value?.setup()
      }

      if (twilioValue || exotelValue || websprixValue) {
        callMedium.value = pickFirstEnabled()
        setMakeCall(makeCall)
      }
    }),
  { immediate: true },
)
</script>
