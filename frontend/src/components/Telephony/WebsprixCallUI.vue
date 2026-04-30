<template>
  <audio ref="xaid" id="remoteAudio"></audio>
  <div v-show="showCallPopup">
    <div
      ref="callPopup"
      class="fixed z-20 flex w-60 cursor-move select-none flex-col rounded-lg bg-gray-900 p-4 text-gray-300 shadow-2xl"
      :style="style"
    >
      <div class="flex flex-row-reverse items-center gap-2">
        <MinimizeIcon class="h-4 w-4 cursor-pointer" @click="toggleCallWindow" />
        <button
          v-if="contact.docname && contact.doctype"
          type="button"
          class="inline-flex h-5 w-5 items-center justify-center rounded-full text-gray-300 hover:text-white hover:bg-gray-800 focus:outline-none"
          :title="
            contact.doctype === 'CRM Deal'
              ? __('Open deal')
              : contact.doctype === 'CRM Lead'
                ? __('Open lead')
                : __('Open contact')
          "
          @click="goToContact"
        >
          <LucideInfo class="h-4 w-4" />
        </button>
      </div>
      <div class="flex flex-col items-center justify-center gap-3">
        <Avatar
          :image="contact.image"
          :label="contact.full_name"
          class="relative flex !h-24 !w-24 items-center justify-center [&>div]:text-[30px]"
          :class="onCall || calling ? '' : 'pulse'"
        />
        <div class="flex flex-col items-center justify-center gap-1">
          <div class="text-xl font-medium">{{ contact.full_name }}</div>
          <div class="text-sm text-gray-600">{{ contact.mobile_no }}</div>
          <div class="text-xs text-gray-600">{{ referer }}</div>
        </div>
        <CountUpTimer ref="counterUp">
          <div v-if="onCall" class="my-1 text-base">
            {{ counterUp?.updatedTime }}
          </div>
        </CountUpTimer>
        <div v-if="!onCall" class="my-1 text-base">
          {{
            callStatus == 'initiating'
              ? 'Initiating call...'
              : callStatus == 'ringing'
                ? 'Ringing...'
                : calling
                  ? 'Calling...'
                  : 'Incoming call...'
          }}
        </div>
        <div v-if="onCall" class="flex gap-2">
          <Button
            :icon="muted ? 'mic-off' : 'mic'"
            class="rounded-full"
            :tooltip="__('Mute / Unmute')"
            @click="toggleMute"
          />
          <Button class="rounded-full" :tooltip="__('Transfer call')" @click="togglePopover">
            <template #icon>
              <ReplyIcon class="cursor-pointer rounded-full" />
            </template>
          </Button>
          <Button
            class="rounded-full bg-surface-gray-6 text-ink-white hover:bg-surface-gray-5"
            :tooltip="__('Add a note')"
            :icon="NoteIcon"
            @click="openNoteModal"
          />
          <Button
            class="rounded-full bg-surface-gray-6 text-ink-white hover:bg-surface-gray-5"
            :tooltip="__('Add a task')"
            :icon="TaskIcon"
            @click="openTaskModal"
          />
          <Button
            variant="solid"
            theme="red"
            class="rounded-full"
            :tooltip="__('Hang up')"
            @click="hangUpCall"
          >
            <template #icon>
              <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white text-white" />
            </template>
          </Button>
        </div>
        <div v-else-if="calling || callStatus == 'initiating'">
          <Button size="md" variant="solid" theme="red" label="Cancel" class="rounded-lg" @click="cancelCall">
            <template #prefix>
              <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white" />
            </template>
          </Button>
        </div>
        <div v-else class="flex gap-2">
          <Button size="md" variant="solid" theme="green" label="Accept" class="rounded-lg" @click="acceptIncomingCall">
            <template #prefix>
              <PhoneIcon class="h-4 w-4 fill-white" />
            </template>
          </Button>
          <Button size="md" variant="solid" theme="red" label="Reject" class="rounded-lg" @click="rejectIncomingCall">
            <template #prefix>
              <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white" />
            </template>
          </Button>
        </div>
      </div>
    </div>
  </div>
  <div
    v-show="showSmallCallWindow"
    class="ml-2 flex cursor-pointer select-none items-center justify-between gap-3 rounded-lg bg-gray-900 px-2 py-[7px] text-base text-gray-300 fixed bottom-0 right-0 w-1/4"
    @click="toggleCallWindow"
  >
    <div class="flex items-center gap-2">
      <Avatar
        :image="contact.image"
        :label="contact.full_name"
        class="relative flex !h-5 !w-5 items-center justify-center"
      />
      <div class="max-w-[120px] truncate">{{ contact.full_name }}</div>
    </div>
    <div v-if="onCall" class="flex items-center gap-2">
      <div class="my-1 min-w-[40px] text-center">{{ counterUp?.updatedTime }}</div>
      <Button variant="solid" theme="red" class="!h-6 !w-6 rounded-full">
        <template #icon>
          <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white" @click.stop="hangUpCall" />
        </template>
      </Button>
    </div>
    <div v-else-if="calling" class="flex items-center gap-3">
      <div class="my-1">{{ callStatus == 'ringing' ? 'Ringing...' : 'Calling...' }}</div>
      <Button variant="solid" theme="red" class="!h-6 !w-6 rounded-full" @click.stop="cancelCall">
        <template #icon>
          <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white" />
        </template>
      </Button>
    </div>
    <div v-else class="flex items-center gap-2">
      <Button
        variant="solid"
        theme="green"
        class="pulse relative !h-6 !w-6 rounded-full"
        @click.stop="acceptIncomingCall"
      >
        <template #icon>
          <PhoneIcon class="h-4 w-4 animate-pulse fill-white" />
        </template>
      </Button>
      <Button variant="solid" theme="red" class="!h-6 !w-6 rounded-full" @click.stop="rejectIncomingCall">
        <template #icon>
          <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white" />
        </template>
      </Button>
    </div>
  </div>
  <div
    v-if="showPopover"
    class="absolute top-0 right-0 w-72 max-h-56 overflow-y-auto z-[1030] cursor-move p-4 bg-white shadow-lg rounded z-50"
  >
    <h3 class="font-semibold text-gray-700">Transfer Call To:</h3>
    <ul>
      <li v-for="user in organizationUsers.result" :key="user.extension" class="mb-2">
        <div class="flex justify-between items-center">
          <span>{{ user.cid_name }}-{{ user.extension }}</span>
          <Button class="text-blue-500 hover:text-blue-700" @click="transferCall(user.extension)">
            Transfer
          </Button>
        </div>
      </li>
    </ul>
  </div>
  <NoteModal
    v-model="showNoteModal"
    :note="note"
    :doctype="referenceDoctype"
    :doc="referenceDocname"
    @after="updateNote"
  />
  <TaskModal
    v-model="showTaskModal"
    :task="task"
    :doctype="referenceDoctype"
    :doc="referenceDocname"
    @after="updateTask"
  />
</template>

<script setup>
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import MinimizeIcon from '@/components/Icons/MinimizeIcon.vue'
import ReplyIcon from '@/components/Icons/ReplyIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import LucideInfo from '~icons/lucide/info'
import CountUpTimer from '@/components/CountUpTimer.vue'
import NoteModal from '@/components/Modals/NoteModal.vue'
import TaskModal from '@/components/Modals/TaskModal.vue'
import {
  Inviter,
  Registerer,
  RegistererState,
  SessionState,
  TransportState,
  UserAgent,
} from 'sip.js'
import router from '@/router'
import { useDraggable, useWindowSize } from '@vueuse/core'
import { globalStore } from '@/stores/global'
import { Avatar, call, createResource, toast } from 'frappe-ui'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const { setMakeCall, $socket } = globalStore()

const contact = ref({
  full_name: '',
  image: '',
  mobile_no: '',
  doctype: '',
  docname: '',
})
const phoneNumber = ref('')

let showCallPopup = ref(false)
let showSmallCallWindow = ref(false)
let onCall = ref(false)
let calling = ref(false)
let muted = ref(false)
let showPopover = ref(false)
let callPopup = ref(null)
let counterUp = ref(null)
let callStatus = ref('')

const showNoteModal = ref(false)
const showTaskModal = ref(false)
const currentCallLogId = ref('')
const task = ref({
  title: '',
  description: '',
  assigned_to: '',
  due_date: '',
  status: 'Backlog',
  priority: 'Low',
})
const note = ref({
  name: '',
  title: '',
  content: '',
})

let ringTone = null
let referer = ref('')
let organizationUsers = ref([])
let activeSession = null
let outgoingUserCancelled = false
let userAgent = null
let registerer = null
let sipServer = ''
let wsDetails = null
const registered = ref(false)
let joinDTMF = null
let leaveDTMF = null

const getContact = createResource({
  url: 'crm.integrations.websprix.api.get_deal_lead_or_contact_from_number',
  makeParams() {
    return { phone_number: phoneNumber.value }
  },
  cache() {
    return ['contact', phoneNumber.value]
  },
  onSuccess(data) {
    const isSavedContact = Boolean(data?.full_name)
    contact.value = {
      ...contact.value,
      ...(data || {}),
      mobile_no: data?.mobile_no || phoneNumber.value,
      full_name: isSavedContact ? data.full_name : __('Unsaved'),
    }
  },
})

watch(phoneNumber, (value) => {
  if (!value) return
  // Show the number with an "Unsaved" placeholder immediately; the
  // backend lookup will overwrite both fields once a match is found.
  contact.value = {
    full_name: __('Unsaved'),
    image: '',
    mobile_no: value,
    doctype: '',
    docname: '',
  }
  getContact.fetch()
})

// Prefer the resolved Lead/Deal as the note/task reference so the saved
// item also appears on the lead/deal page. Fall back to the Call Log only
// when we actually have one (a missing reference_docname would make the
// insert fail, which is what stopped the dialog from closing before).
const referenceDoctype = computed(() => {
  const dt = contact.value?.doctype
  if ((dt === 'CRM Lead' || dt === 'CRM Deal') && contact.value?.docname) {
    return dt
  }
  return currentCallLogId.value ? 'CRM Call Log' : ''
})
const referenceDocname = computed(() => {
  const dt = contact.value?.doctype
  if ((dt === 'CRM Lead' || dt === 'CRM Deal') && contact.value?.docname) {
    return contact.value.docname
  }
  return currentCallLogId.value || ''
})

const { width, height } = useWindowSize()
const { x, y, style } = useDraggable(callPopup, {
  initialValue: { x: width.value - 280, y: height.value - 310 },
  containerElement: document.body,
  preventDefault: true,
  onMove: ({ x, y }) => {
    const el = callPopup.value
    if (!el) return
    const { offsetWidth, offsetHeight } = el
    x.value = Math.min(width.value - offsetWidth, Math.max(0, x))
    y.value = Math.min(height.value - offsetHeight, Math.max(0, y))
  },
})

function toggleCallWindow() {
  showCallPopup.value = !showCallPopup.value
  showSmallCallWindow.value = !showSmallCallWindow.value
}

function togglePopover() {
  showPopover.value = !showPopover.value
}

function toggleMute() {
  if (!activeSession) return
  if (!muted.value) {
    handleMute(false)
    muted.value = true
  } else {
    handleMute(true)
    muted.value = false
  }
}

function handleMute(toggle) {
  const sessionDescriptionHandler = activeSession.sessionDescriptionHandler
  const peerConnection = sessionDescriptionHandler?.peerConnection
  if (!peerConnection) return
  peerConnection.getSenders().forEach((sender) => {
    if (sender.track) sender.track.enabled = toggle
  })
}

async function acceptIncomingCall() {
  onCall.value = true
  activeSession.accept()
  counterUp.value?.start?.()
}

function rejectIncomingCall() {
  if (activeSession) {
    activeSession.reject().catch(() => {})
  }
  showCallPopup.value = false
  showSmallCallWindow.value = false
  callStatus.value = ''
  muted.value = false
  if (ringTone) ringTone.pause()
}

function hangUpCall() {
  onCall.value = false
  callStatus.value = ''
  muted.value = false
  note.value = { name: '', title: '', content: '' }
  counterUp.value?.stop?.()
  if (!activeSession) return
  if (activeSession.state === 'Established') {
    activeSession.bye().catch(() => {})
  } else {
    activeSession.cancel().catch(() => {})
  }
}

function cancelCall() {
  if (!activeSession) return
  outgoingUserCancelled = true
  if (activeSession.state === 'Initial' || activeSession.state === 'Established') {
    activeSession.bye()
  } else if (activeSession.state === 'Establishing') {
    activeSession.cancel()
  }
  showCallPopup.value = false
  showSmallCallWindow.value = false
  callStatus.value = ''
  calling.value = false
}

function transferCall(extension) {
  if (!activeSession) return
  const target = UserAgent.makeURI(`sip:${extension}@${sipServer}`)
  if (!target) return
  activeSession.refer(target).then(() => {
    showPopover.value = false
  })
}

function audioConfig(session) {
  const remoteAudio = document.getElementById('remoteAudio')
  if (!remoteAudio) return
  const remoteStream = new MediaStream()
  session.sessionDescriptionHandler.peerConnection.getReceivers().forEach((receiver) => {
    if (receiver.track) remoteStream.addTrack(receiver.track)
  })
  remoteAudio.srcObject = remoteStream
  remoteAudio.play().catch(() => {})
}

function earlyMediaConfig(session) {
  audioConfig(session)
}

function cleanupMedia() {
  const remoteAudio = document.getElementById('remoteAudio')
  if (remoteAudio) {
    remoteAudio.srcObject = null
  }
}

async function startupClient() {
  try {
    wsDetails = await call('crm.integrations.websprix.api.get_user_settings')
  } catch (e) {
    console.warn('[WebSprix] Could not fetch user settings:', e)
    return
  }
  if (!wsDetails || !wsDetails.result) return

  const { username, ep_pass, cid_name, pri_sip_address, sec_sip_address } = wsDetails.result
  sipServer = pri_sip_address || sec_sip_address
  const wsServer = `wss://${sipServer}:8089/ws`

  const uri = UserAgent.makeURI(`sip:${username}@${sipServer}`)
  if (!uri) return

  const uaConfig = {
    uri,
    media: { remote: { audio: document.getElementById('remoteAudio') } },
    delegate: {
      onInvite,
      onMessage: () => {},
      onConnect: () => {
        window.dispatchEvent(new CustomEvent('statusEvent', { detail: 'connected' }))
      },
      onDisconnect: () => {
        window.dispatchEvent(new CustomEvent('statusEvent', { detail: 'disconnected' }))
      },
    },
    transportOptions: {
      server: wsServer,
      // Log every SIP message in/out of the browser. Costs a bit of console
      // noise but is the only way to see the PBX's WWW-Authenticate header
      // and 401/403 reasons during onboarding/debugging.
      traceSip: true,
      keepAliveInterval: 5,
    },
    register: false,
    hackIpInContact: true,
    authorizationUsername: username,
    authorizationPassword: ep_pass,
    displayName: cid_name,
  }

  userAgent = new UserAgent(uaConfig)
  registerer = new Registerer(userAgent)

  registerer.stateChange.addListener((state) => {
    registered.value = state === RegistererState.Registered
    if (state === RegistererState.Unregistered) {
      console.warn('[WebSprix] SIP registration is no longer active')
    }
  })

  userAgent.start().then(() => {
    registerer
      .register()
      .catch((err) => {
        console.warn('[WebSprix] register failed:', err)
        toast.error(
          __(
            'WebSprix SIP registration failed. Calls will not work until you reload the page.',
          ),
        )
      })
  })
}

async function onInvite(session) {
  showCallPopup.value = true
  activeSession = session
  referer.value = ''

  if (session.remoteIdentity?.displayName) {
    phoneNumber.value = session.remoteIdentity.displayName
  } else if (session.remoteIdentity?.uri?.user) {
    phoneNumber.value = session.remoteIdentity.uri.user
  }

  const referredByHeader = session.request.getHeader('Referred-By')
  if (referredByHeader) {
    try {
      const refererUri = referredByHeader.replace(/<|>/g, '')
      const sipUri = UserAgent.makeURI(refererUri)
      if (sipUri?.user?.includes('S')) {
        const extension = sipUri.user.split('S')[1]
        for (const user of organizationUsers?.result || []) {
          if (user.extension === extension) {
            referer.value = `Referer: ${user.cid_name}`
          }
        }
      }
    } catch (e) {
      referer.value = ''
    }
  }

  if (ringTone) {
    ringTone.play().catch(() => {
      if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
        new Notification('Incoming Call')
      }
    })
  }

  session.stateChange.addListener((newState) => {
    switch (newState) {
      case SessionState.Established:
        audioConfig(session)
        if (ringTone) ringTone.pause()
        showCallPopup.value = true
        muted.value = false
        onCall.value = true
        referer.value = ''
        counterUp.value?.start?.()
        break
      case SessionState.Terminated:
        activeSession = null
        showCallPopup.value = false
        showSmallCallWindow.value = false
        muted.value = false
        onCall.value = false
        referer.value = ''
        showPopover.value = false
        currentCallLogId.value = ''
        if (ringTone) ringTone.pause()
        cleanupMedia()
        counterUp.value?.stop?.()
        refreshCallLogs('incoming')
        break
      default:
        break
    }
  })
}

async function makeOutgoingCall(number) {
  if (!userAgent || !sipServer) {
    toast.error(__('WebSprix is not registered. Please reload.'))
    return
  }

  referer.value = ''
  let dtmfType = number

  if (number === 'join_queue' && joinDTMF != null) number = joinDTMF
  else if (number === 'leave_queue' && leaveDTMF != null) number = leaveDTMF

  const target = UserAgent.makeURI(`sip:${number}@${sipServer}`)
  if (!target) return

  const inviter = new Inviter(userAgent, target, {
    earlyMedia: true,
    sessionDescriptionHandlerOptions: {
      constraints: { audio: true, video: false },
    },
  })

  activeSession = inviter
  outgoingUserCancelled = false
  // Track whether the call ever connected so a Terminated transition that
  // happens before Established (e.g. PBX 401, 403, 404) can be surfaced as
  // a failure instead of silently closing the popup. We also need to
  // distinguish PBX-initiated termination from user-clicked Cancel.
  let callEverEstablished = false

  phoneNumber.value = number

  if (number[0] !== '*') {
    showCallPopup.value = true
    calling.value = true
    callStatus.value = 'initiating'
  }

  inviter.stateChange.addListener((state) => {
    switch (state) {
      case SessionState.Establishing:
        callStatus.value = 'ringing'
        activeSession = inviter
        earlyMediaConfig(inviter)
        break
      case SessionState.Established:
        callEverEstablished = true
        callStatus.value = ''
        activeSession = inviter
        showCallPopup.value = true
        muted.value = false
        onCall.value = true
        referer.value = ''
        calling.value = false
        counterUp.value?.start?.()
        audioConfig(inviter)
        window.dispatchEvent(new CustomEvent('queueEvent', { detail: dtmfType }))
        break
      case SessionState.Terminated:
        if (
          !callEverEstablished &&
          !outgoingUserCancelled &&
          number[0] !== '*'
        ) {
          toast.error(
            __(
              'Call could not be placed. The PBX rejected the call (check the browser console for a 401/403 from sip.js).',
            ),
          )
        }
        outgoingUserCancelled = false
        activeSession = null
        calling.value = false
        contact.value = { full_name: '', mobile_no: '', user_link: '', docname: '', doctype: '' }
        currentCallLogId.value = ''
        onCall.value = false
        showCallPopup.value = false
        showSmallCallWindow.value = false
        showPopover.value = false
        callStatus.value = ''
        muted.value = false
        counterUp.value?.stop?.()
        refreshCallLogs('outgoing')
        break
      default:
        break
    }
  })

  inviter.invite().catch((err) => {
    console.error('[WebSprix] outgoing call error:', err)
    toast.error(__('Outgoing call failed: {0}', [err?.message || err]))
  })
}

function goToContact() {
  if (!contact.value?.doctype || !contact.value?.docname) {
    console.warn('[WebSprix] No linked document to open for this contact')
    return
  }

  // Backend returns the raw Frappe doctype name ("CRM Lead" / "CRM Deal" /
  // "Contact"); the router uses "Lead" / "Deal" / "Contact". Translate.
  const routeByDoctype = {
    'CRM Lead': { name: 'Lead', paramKey: 'leadId' },
    'CRM Deal': { name: 'Deal', paramKey: 'dealId' },
    Lead: { name: 'Lead', paramKey: 'leadId' },
    Deal: { name: 'Deal', paramKey: 'dealId' },
    Contact: { name: 'Contact', paramKey: 'contactId' },
  }

  const target = routeByDoctype[contact.value.doctype]
  if (!target) {
    console.warn('[WebSprix] Unknown doctype for navigation:', contact.value.doctype)
    return
  }

  router.push({
    name: target.name,
    params: { [target.paramKey]: contact.value.docname },
  })
}

async function resolveCurrentCallLogId() {
  if (currentCallLogId.value) return currentCallLogId.value
  if (!phoneNumber.value) return ''
  try {
    const logs = await call('frappe.client.get_list', {
      doctype: 'CRM Call Log',
      filters: {
        telephony_medium: 'WebSprix',
        from: ['in', [phoneNumber.value, `+${phoneNumber.value}`]],
      },
      or_filters: { to: phoneNumber.value },
      fields: ['name'],
      order_by: 'creation desc',
      page_length: 1,
    })
    if (logs?.length) {
      currentCallLogId.value = logs[0].name
      return currentCallLogId.value
    }
  } catch (e) {
    console.warn('[WebSprix] Could not resolve current call log:', e)
  }
  return ''
}

async function openNoteModal() {
  await resolveCurrentCallLogId()
  note.value = { name: '', title: '', content: '' }
  showNoteModal.value = true
}

async function openTaskModal() {
  await resolveCurrentCallLogId()
  task.value = {
    title: '',
    description: '',
    assigned_to: '',
    due_date: '',
    status: 'Backlog',
    priority: 'Low',
  }
  showTaskModal.value = true
}

async function updateNote(_note, insert_mode = false) {
  note.value = _note
  showNoteModal.value = false
  if (insert_mode && _note?.name && currentCallLogId.value) {
    try {
      await call('crm.integrations.api.add_note_to_call_log', {
        call_sid: currentCallLogId.value,
        note: _note,
      })
    } catch (e) {
      console.warn('[WebSprix] Failed to link note to call log:', e)
    }
  }
}

async function updateTask(_task, insert_mode = false) {
  task.value = _task
  showTaskModal.value = false
  if (insert_mode && _task?.name && currentCallLogId.value) {
    try {
      await call('crm.integrations.api.add_task_to_call_log', {
        call_sid: currentCallLogId.value,
        task: _task,
      })
    } catch (e) {
      console.warn('[WebSprix] Failed to link task to call log:', e)
    }
  }
}

async function refreshCallLogs(type) {
  await new Promise((resolve) => setTimeout(resolve, 4000))
  try {
    if (type === 'incoming') {
      await call('crm.integrations.websprix.api.fetch_and_process_incoming_call_logs')
      await call('crm.integrations.websprix.api.fetch_and_process_missed_call_logs')
    } else if (type === 'outgoing') {
      await call('crm.integrations.websprix.api.fetch_and_process_outgoing_call_logs')
    }
  } catch (e) {
    console.warn('[WebSprix] Post-call log sync failed:', e)
  }
}

async function getOrganizationUsers() {
  try {
    const result = await call('crm.integrations.websprix.api.fetch_users_to_transfer')
    if (result?.status === 'OK' && Array.isArray(result.result)) {
      organizationUsers.value = result
    } else {
      organizationUsers.value = result || { result: [] }
    }
  } catch (e) {
    organizationUsers.value = { result: [] }
  }
}

/**
 * Build a ring-tone player. Synthesises a phone-ring with Web Audio API so
 * we don't depend on a static asset. If a custom ringtone has been uploaded
 * via CRM WebSprix Settings, we use that instead.
 */
async function createRingTone() {
  let htmlAudio = null
  try {
    const settings = await call('frappe.client.get_value', {
      doctype: 'CRM WebSprix Settings',
      fieldname: 'ringtone',
    })
    const ringtoneUrl = settings?.ringtone
    if (ringtoneUrl) {
      htmlAudio = new Audio(ringtoneUrl)
      htmlAudio.loop = true
    }
  } catch (e) {
    htmlAudio = null
  }

  let audioCtx = null
  let ringInterval = null

  function playSyntheticBurst() {
    try {
      if (!audioCtx) {
        const Ctx = window.AudioContext || window.webkitAudioContext
        if (!Ctx) return
        audioCtx = new Ctx()
      }
      const osc1 = audioCtx.createOscillator()
      const osc2 = audioCtx.createOscillator()
      const gain = audioCtx.createGain()
      osc1.frequency.value = 440
      osc2.frequency.value = 480
      const t = audioCtx.currentTime
      gain.gain.setValueAtTime(0, t)
      gain.gain.linearRampToValueAtTime(0.18, t + 0.05)
      gain.gain.setValueAtTime(0.18, t + 1.6)
      gain.gain.linearRampToValueAtTime(0, t + 1.7)
      osc1.connect(gain)
      osc2.connect(gain)
      gain.connect(audioCtx.destination)
      osc1.start(t)
      osc2.start(t)
      osc1.stop(t + 1.7)
      osc2.stop(t + 1.7)
    } catch (e) {
      // silent fallback
    }
  }

  return {
    play() {
      if (htmlAudio) {
        const promise = htmlAudio.play()
        if (promise && typeof promise.catch === 'function') {
          promise.catch(() => {
            htmlAudio = null
            this.play()
          })
        }
        return Promise.resolve()
      }
      playSyntheticBurst()
      if (!ringInterval) {
        ringInterval = setInterval(playSyntheticBurst, 3500)
      }
      return Promise.resolve()
    },
    pause() {
      if (htmlAudio) {
        try {
          htmlAudio.pause()
          htmlAudio.currentTime = 0
        } catch (e) {
          // ignore
        }
      }
      if (ringInterval) {
        clearInterval(ringInterval)
        ringInterval = null
      }
    },
  }
}

async function setup() {
  // navigator.mediaDevices is only available in secure contexts (HTTPS or
  // localhost). On plain HTTP the entire API is undefined, so accessing it
  // without guarding throws "Cannot read properties of undefined" and aborts
  // the whole component.
  if (
    typeof navigator !== 'undefined' &&
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === 'function'
  ) {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      console.warn('[WebSprix] Microphone permission was not granted:', err?.message || err)
    }
  } else {
    console.warn(
      '[WebSprix] navigator.mediaDevices is unavailable — browser calling requires HTTPS (or http://localhost). The SIP client will not register.',
    )
    return
  }

  await startupClient()

  try {
    const queueSettings = await call('crm.integrations.websprix.api.get_queue_settings')
    if (queueSettings) {
      joinDTMF = queueSettings.join_dtmf
      leaveDTMF = queueSettings.leave_dtmf
    }
  } catch (e) {
    // queue settings are optional
  }

  window.addEventListener('callEvent', function (e) {
    makeOutgoingCall(e.detail.number)
  })

  // Capture the CRM Call Log id as soon as the backend webhook fires so
  // the "Add a note" / "Add a task" buttons have a reference to link to.
  if ($socket && typeof $socket.on === 'function') {
    $socket.on('websprix_call', (data) => {
      if (data?.CallUUID) {
        currentCallLogId.value = data.CallUUID
      }
    })
  }

  await getOrganizationUsers()
  ringTone = await createRingTone()
  setMakeCall(makeOutgoingCall)
}

onBeforeUnmount(() => {
  if ($socket && typeof $socket.off === 'function') {
    $socket.off('websprix_call')
  }
})

defineExpose({ setup, makeOutgoingCall })
</script>
