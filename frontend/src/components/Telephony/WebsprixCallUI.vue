<template>
  <audio ref="xaid" id="remoteAudio"> </audio>
  <div v-show="showCallPopup">
    <div ref="callPopup"
      class="fixed z-20 flex w-60 cursor-move select-none flex-col rounded-lg bg-gray-900 p-4 text-gray-300 shadow-2xl"
      :style="style">
      <div class="flex flex-row-reverse items-center gap-1">
        <MinimizeIcon class="h-4 w-4 cursor-pointer" @click="toggleCallWindow" />
      </div>
      <div class="flex flex-col items-center justify-center gap-3">
        <Avatar :image="contact.image" :label="contact.full_name"
          class="relative flex !h-24 !w-24 items-center justify-center [&>div]:text-[30px]"
          :class="onCall || calling ? '' : 'pulse'" />
        <div class="flex flex-col items-center justify-center gap-1">
          <div class="text-xl font-medium">
            {{ contact.full_name }}
          </div>
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
          <Button :icon="muted ? 'mic-off' : 'mic'" class="rounded-full" @click="toggleMute" />
          <Button @click="togglePopover" class="rounded-full">
            <template #icon>
              <ReplyIcon class="cursor-pointer rounded-full" />
            </template>
          </Button>
          <Button class="rounded-full">
            <template #icon>
              <div v-if="contact.first_name && contact.first_name !== 'Unknown'">
                <FileIcon class="h-4 w-4 cursor-pointer rounded-full text-gray-900" @click="goToContact()" />
              </div>
              <div v-else>
                <ContactIcon class="h-4 w-4 cursor-pointer rounded-full text-gray-900" @click="goToContact()" />
              </div>
            </template>
          </Button>
                   <Button
            class="bg-surface-gray-6 text-ink-white hover:bg-surface-gray-5"
            :tooltip="__('Add a note')"
            size="md"
            :icon="NoteIcon"
            @click="showNoteWindow"
          />
          <Button
            class="bg-surface-gray-6 text-ink-white hover:bg-surface-gray-5"
            size="md"
            :tooltip="__('Add a task')"
            :icon="TaskIcon"
            @click="showTaskWindow"
          />
          <Button class="rounded-full bg-red-600 hover:bg-red-700">
            <template #icon>
              <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white text-white" @click="hangUpCall" />
            </template>
          </Button>
        </div>
        <div v-else-if="calling || callStatus == 'initiating'">
          <Button size="md" variant="solid" theme="red" label="Cancel" @click="cancelCall" class="rounded-lg">
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
  <div v-show="showSmallCallWindow"
    class="ml-2 flex cursor-pointer select-none items-center justify-between gap-3 rounded-lg bg-gray-900 px-2 py-[7px] text-base text-gray-300 fixed bottom-0 right-0 w-1/4"
    @click="toggleCallWindow">
    <div class="flex items-center gap-2">
      <Avatar :image="contact.image" :label="contact.full_name"
        class="relative flex !h-5 !w-5 items-center justify-center" />
      <div class="max-w-[120px] truncate">
        {{ contact.full_name }}
      </div>
    </div>
    <div v-if="onCall" class="flex items-center gap-2">
      <div class="my-1 min-w-[40px] text-center">
        {{ counterUp?.updatedTime }}
      </div>
      <Button variant="solid" theme="red" class="!h-6 !w-6 rounded-full">
        <template #icon>
          <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white" @click.stop="hangUpCall" />
        </template>
      </Button>
    </div>
    <div v-else-if="calling" class="flex items-center gap-3">
      <div class="my-1">
        {{ callStatus == 'ringing' ? 'Ringing...' : 'Calling...' }}
      </div>
      <Button variant="solid" theme="red" class="!h-6 !w-6 rounded-full" @click.stop="cancelCall">
        <template #icon>
          <PhoneIcon class="h-4 w-4 rotate-[135deg] fill-white" />
        </template>
      </Button>
    </div>
    <div v-else class="flex items-center gap-2">
      <Button variant="solid" theme="green" class="pulse relative !h-6 !w-6 rounded-full"
        @click.stop="acceptIncomingCall">
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
  <div v-if="showPopover"
    class="absolute top-0 right-0 w-72 max-h-56 overflow-y-auto z-[1030] cursor-move p-4 bg-white shadow-lg rounded z-50">
    <h3 class="font-semibold text-gray-700">Transfer Call To:</h3>
    <ul>
      <li v-for="user in organizationUsers.result" :key="user.id" class="mb-2">
        <div class="flex justify-between items-center">
          <span>{{ user.cid_name }}-{{ user.extension }}</span>
          <Button class="text-blue-500 hover:text-blue-700" @click="transferCall(user.extension)">
            Transfer
          </Button>
        </div>
      </li>
    </ul>
  </div>
  <NoteModal v-model="showNoteModal" :note="note" doctype="CRM Call Log" @after="updateNote" />
</template>

<script setup>
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import FileIcon from '@/components/Icons/FileIcon.vue'
import ContactIcon from '@/components/Icons/ContactIcon.vue'
import MinimizeIcon from '@/components/Icons/MinimizeIcon.vue'
import DialpadIcon from '@/components/Icons/DialpadIcon.vue'
import ReplyIcon from '@/components/Icons/ReplyIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import CountUpTimer from '@/components/CountUpTimer.vue'
import NoteModal from '@/components/Modals/NoteModal.vue'
import {
  Inviter,
  Registerer,
  RegistererState,
  SessionState,
  TransportState,
  UserAgent,
} from "sip.js";
import router from '@/router'
import { useDraggable, useWindowSize } from '@vueuse/core'
import { globalStore } from '@/stores/global'
import { Avatar, call, createResource } from 'frappe-ui'
import { onMounted, ref, watch } from 'vue'

const { setMakeCall, $dialog } = globalStore()

let log = ref('Connecting...')

/*const contact = ref({
  full_name: '',
  mobile_no: '',
  //user_link: '',
})*/

const contact = ref({
  full_name: '',
  image: '',
  mobile_no: '',
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
const note = ref({
  title: '',
  content: '',
})
let ringTone = null;
let referer = ref('');
let organizationUsers = ref([]);
let activeSession = null;
let wsDetails = null;
let sipServer = null;
let userAgent = null;
let uaConfig = null;
let connectAttempt = 0;
let uri = null;
let joinDTMF = null;
let leaveDTMF = null;
let onlineStatus = 0;

watch(phoneNumber, (value) => {
  console.log(value)
  if (!value) return
  getContact.fetch()
})

const getContact = createResource({
  url: 'crm.integrations.websprix.api.get_deal_lead_or_contact_from_number',
  makeParams() {
    return {
      phone_number: phoneNumber.value,
    }
  },
  cache() {
    return ['contact', phoneNumber.value]
  },
  onSuccess(data) {
    contact.value = data
    console.log("data", data)
    console.log(contact.value)
  },
})


async function getOrganizationUsers() {
  organizationUsers.value = [];
  try {
    organizationUsers = await call('crm.integrations.websprix.api.fetch_users_to_transfer');
    if (organizationUsers.status == "OK") {
      const currentUser = organizationUsers.result.findIndex(obj => obj['extension'] == wsDetails.result.extension);
      if (currentUser !== -1) {
        organizationUsers.result.splice(currentUser, 1);
      }

      organizationUsers.value = organizationUsers.result;
    }
  } catch (e) {
    organizationUsers.value = [];
  }
}

async function getContactDetail(number) {
  try {
    const formattedNumber = number.replace(/^\+?251/, '0');
    const contactInfo = await call('crm.integrations.websprix.api.get_contact_info', { formattedNumber });
    if (contactInfo && contactInfo.data.length !== 0) {
      contact.value = {
        full_name: contactInfo.data.full_name,
        mobile_no: number,
      }
    } else {
      contact.value = {
        full_name: 'Unknown',
        mobile_no: number,
      }
    }

    if (contactInfo && contactInfo.open_file_name != '') {
      contact.value.user_link = `/crm/${contactInfo.file_doc_type}/${contactInfo.open_file_name}`
    } else {
      contact.value.user_link = `/crm/${contactInfo.file_doc_type}/new}`
    }

  } catch (e) {
    console.log('contact error', e);
    contact.value = {
      full_name: 'Unknown',
      mobile_no: number,
    }
  }
}

async function onInvite(session) {
  showCallPopup.value = true;
  activeSession = session;
  referer.value = '';

  if (session.remoteIdentity && session.remoteIdentity.displayName) {
    let uri = session.remoteIdentity
    let phoneNo = session.remoteIdentity.displayName
    phoneNumber.value = phoneNo
  } else if (session.remoteIdentity && session.remoteIdentity.uri.normal.user) {
    let uri = session.remoteIdentity;
    let phoneNo = session.remoteIdentity.uri.normal.user;
    phoneNumber.value = phoneNo
  } else if (session.remoteIdentity && session.remoteIdentity.uri.raw.user) {
    let uri = session.remoteIdentity;
    let phoneNo = session.remoteIdentity.uri.raw.user;
    phoneNumber.value = phoneNo
  }

  const referredByHeader = session.request.getHeader('Referred-By');
  if (referredByHeader) {
    try {
      const refererUri = referredByHeader.replace(/<|>/g, '');
      const sipUri = UserAgent.makeURI(refererUri);
      if (sipUri && sipUri.user) {
        if (sipUri.user.includes('S')) {
          let extension = sipUri.user.split('S')[1];
          for (let user of organizationUsers.result) {
            if (user.extension === extension) {
              referer.value = `Referer: ${user.cid_name}`;
            }
          }
        }
      }
    } catch (error) {
      referer.value = '';
    }
  } else {
    referer.value = '';
  }

  ringTone
    .play()
    .then(() => { })
    .catch((error) => {
      console.log(error)
      if (Notification.permission === "granted") {
        new Notification("Incoming Call");
      }
    });

  session.stateChange.addListener((newState) => {
    switch (newState) {
      case SessionState.Establishing:
        break;
      case SessionState.Established:
        audioConfig(session);
        ringTone.pause();
        showCallPopup.value = true
        muted.value = false
        onCall.value = true
        referer.value = '';
        break;
      case SessionState.Terminated:
        activeSession = null;
        showCallPopup.value = false
        if (showSmallCallWindow.value == undefined) {
          showSmallCallWindow = false
        } else {
          showSmallCallWindow.value = false
        }
        muted.value = false
        onCall.value = false
        referer.value = '';
        showPopover.value = false
        ringTone.pause();
        cleanupMedia()
        counterUp.value.stop()
        refreshCallLogs('incoming');
        break;
      default:
        break;
    }
  });
}

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
  }
})

watch([width, height], () => {
  const el = callPopup.value
  if (!el) return

  const { offsetWidth, offsetHeight } = el

  // Adjust position to stay within the viewport
  x.value = Math.min(width.value - offsetWidth, Math.max(0, x.value))
  y.value = Math.min(height.value - offsetHeight, Math.max(0, y.value))
})

async function startupClient() {
  log.value = 'Requesting Access Token...'
  ++connectAttempt;

  try {
    wsDetails = await call('crm.integrations.websprix.api.get_user_settings');
  } catch (e) {
    console.log("An error occured fetching connection details");
    wsDetails = null;
    return;
  }

  let {
    username,
    cid_name,
    ep_pass: password,
    pri_sip_address: sipServer
  } = wsDetails.result;

  if (!wsDetails || !wsDetails.result) {
    console.log("Invalid connection details");
    return;
  }

  if (connectAttempt > 3) {
    sipServer = wsDetails.result.sec_sip_address;
  }
  console.log(sipServer)

  // sipServer = 'etw-pbx-sip1.websprix.com'
  //console.log(sipServer);
  //const wsServer = `wss://etw-pbx-sip2.websprix.com:8089/ws`;
  // uri = UserAgent.makeURI(`sip:${username}@etw-pbx-sip2.websprix.com`);
  // const wsServer = `wss://${sipServer}:8089/ws`;
  // uri = UserAgent.makeURI(`sip:${username}@${sipServer}`);

  const wsServer = `wss://${sipServer}:8089/ws`;
  uri = UserAgent.makeURI(`sip:${username}@${sipServer}`);

  uaConfig =
  {
    uri: uri,
    media: {
      remote: {
        audio: document.getElementById('remoteAudio'),
      },
    },
    delegate: {
      onRefer: async (referral) => {
          console.log(referral)
      },
      onInvite: onInvite,
      onMessage: function (message) {
        console.log("Received SIP message:", message);
      },
      onRegistered: function () {
        console.log("Successfully registered!");
      },
      onRegistrationFailed: function (cause) {
        console.log("Registration failed:", cause);
      }
    },
    transportOptions: {
      server: wsServer,
      traceSip: true,
      keepAliveInterval: 5,
    },
    register: true,
    hackIpInContact: true,
    authorizationUsername: username,
    authorizationPassword: password,
    displayName: cid_name,
  }

  userAgent = new UserAgent(uaConfig);

  userAgent.transport.stateChange.addListener((newState) => {
    switch (newState) {
      case TransportState.Connecting:
        console.log('Attempting to connect to the server...');
        break;
      case TransportState.Connected:
        console.log('Successfully connected to the server.');
        onlineStatus = 1;
        window.dispatchEvent(new CustomEvent('statusEvent', {
          detail: 'connected'
        }));
        break;
      case TransportState.Disconnecting:
        onlineStatus = 0;
        console.log('Disconnecting from the server...');
        window.dispatchEvent(new CustomEvent('statusEvent', {
          detail: 'disconnecting'
        }));
        break;
      case TransportState.Disconnected:
        onlineStatus = 0;
        console.log('Disconnected from the server.');
        if (connectAttempt < 10) {
          setTimeout(async () => {
            await startupClient();
            console.log("Attempting Re-connection");
          }, 5000);
          window.dispatchEvent(new CustomEvent('statusEvent', {
            detail: 'reconnecting'
          }));
        }
        window.dispatchEvent(new CustomEvent('statusEvent', {
          detail: 'disconnected'
        }));
        break;
      case TransportState.Reconnecting:
        console.log('Reconnecting to the server...');
        break;
      default: console.log('Unknown transport state:', newState);
        break;
    }
  });

  try {
    await registerSipUser();
  } catch (err) {
    log.value = 'An error occurred. ' + err.message
  }
}

async function registerSipUser() {
  const registerer = new Registerer(userAgent, uri);

  userAgent.start().then(() => {
    registerer.register().catch((err) => console.log(err));
  });
}

function togglePopover() {
  showPopover.value = !showPopover.value;
}

function toggleMute() {
  if (!muted.value) {
    handleMute(false)
    muted.value = true
  } else {
    handleMute(true);
    muted.value = false
  }
}

function handleMute(toggle) {
  const sessionDescriptionHandler = activeSession.sessionDescriptionHandler;
  const peerConnection = sessionDescriptionHandler.peerConnection;
  if (!peerConnection) {
    throw new Error("Peer connection closed.");
  }
  peerConnection.getSenders().forEach((sender) => {
    if (sender.track) {
      sender.track.enabled = toggle;
    }
  });
}

async function acceptIncomingCall() {
  log.value = 'Accepted incoming call.'
  onCall.value = true
  activeSession.accept()
  counterUp.value.start()
}

function rejectIncomingCall() {
  activeSession.reject().catch((error) => console.log(error));
  console.log("Call Rejected")
  log.value = 'Rejected incoming call'
  showCallPopup.value = false
  if (showSmallCallWindow.value == undefined) {
    showSmallCallWindow = false
  } else {
    showSmallCallWindow.value = false
  }
  callStatus.value = ''
  muted.value = false
}


function hangUpCall() {
  log.value = 'Hanging up incoming call'
  onCall.value = false
  callStatus.value = ''
  muted.value = false
  note.value = {
    title: '',
    content: '',
  }
  counterUp.value.stop()
  if (activeSession.state == "Established") {
    activeSession.bye().catch((error) => { });
  } else {
    activeSession.cancel().catch((error) => { });
  }
}

function handleDisconnectedIncomingCall() {
  log.value = `Call ended from handle disconnected Incoming call.`
  showCallPopup.value = false
  if (showSmallCallWindow.value == undefined) {
    showSmallCallWindow = false
  } else {
    showSmallCallWindow.value = false
  }
  _call = null
  muted.value = false
  onCall.value = false
  counterUp.value.stop()
}

async function makeOutgoingCall(number, sipServer) {

  /*if(!onlineStatus) {
    window.frappe.msgprint("The user is offline and can't make calls right now");
    return;
  }
  */
  referer.value = '';
  let dtmfType = number;

  if (number == "join_queue" && joinDTMF != null) {
    number = joinDTMF;
  } else if (number == "leave_queue" && leaveDTMF != null) {
    number = leaveDTMF;
  }

  const target = UserAgent.makeURI(`sip:${number}@${sipServer}`);

  const inviter = new Inviter(userAgent, target, {
    earlyMedia: true,
    sessionDescriptionHandlerOptions: {
      constraints: {
        audio: true,
        video: false,
      },
    },
  })

  activeSession = inviter;

  await userAgent
    .start()
    .then(() => {
      inviter.invite();
    }).catch((error) => {
      console.error("Error <callWithTarget-sip>: ", error);
    });

  //await getContactDetail(number); 
  phoneNumber.value = number;

  if (number[0] != "*") {
    showCallPopup.value = true
    calling.value = true
    callStatus.value = 'initiating'
  }

  inviter.stateChange.addListener((state) => {
    switch (state) {
      case SessionState.Initial:
        break;
      case SessionState.Establishing:
        callStatus.value = 'ringing';
        activeSession = inviter;
        earlyMediaConfig(inviter);
        break;
      case SessionState.Established:
        callStatus.value = ''
        activeSession = inviter;
        showCallPopup.value = true
        muted.value = false
        onCall.value = true
        referer.value = '';
        calling.value = false
        counterUp.value.start()
        audioConfig(inviter);
        window.dispatchEvent(new CustomEvent('queueEvent', {
          detail: dtmfType
        }));
        break;
      case SessionState.Terminating:
        break;
      case SessionState.Terminated:
        console.log('Call ended.');
        activeSession = null;
        calling.value = false
        contact.value = {
          full_name: '',
          mobile_no: '',
          user_link: '',
          docname:   '',
          doctype:   ''
        }
        onCall.value = false
        showCallPopup.value = false
        showSmallCallWindow = false
        showPopover.value = false
        callStatus.value = ''
        muted.value = false
        counterUp.value.stop()
        //refreshCallLogs('outgoing');
        break
      default:
        console.log('Unknown session state')
    }
  });
}

function cancelCall() {
  if (activeSession) {
    if (activeSession.state == "Initial" || activeSession.state == "Established") {
      activeSession.bye();
    } else if (activeSession.state == "Establishing") {
      activeSession.cancel();
    }
  }
  activeSession = null;
  showCallPopup.value = false
  if (showSmallCallWindow.value == undefined) {
    showSmallCallWindow = false
  } else {
    showSmallCallWindow.value = false
  }
  calling.value = false
  onCall.value = false
  callStatus.value = ''
  muted.value = false
  contact.value = {
    full_name: '',
    mobile_no: '',
    user_link: '',
    docname:   '',
    doctype:   ''
  }
}

function transferCall(number) {

  if (activeSession) {

    const target = UserAgent.makeURI(`sip:${number}@${sipServer}`);

    activeSession.refer(target).then(() => {
      activeSession = null;
      showCallPopup.value = false
      if (showSmallCallWindow.value == undefined) {
        showSmallCallWindow = false
      } else {
        showSmallCallWindow.value = false
      }
      showPopover.value = false;
      muted.value = false
      onCall.value = false
      cleanupMedia()
      counterUp.value.stop()
    }).catch((error) => {
      console.log("Can't Transfer call", error);
    });

  }
}

function toggleCallWindow() {
  showCallPopup.value = !showCallPopup.value
  if (showSmallCallWindow.value == undefined) {
    showSmallCallWindow = !showSmallCallWindow
  } else {
    showSmallCallWindow.value = !showSmallCallWindow.value
  }
}

function cleanupMedia() {
  let mediaElement = document.getElementById("remoteAudio");
  mediaElement.srcObject = null;
  mediaElement.pause();
}

function earlyMediaConfig(inviter) {
  const mediaElement = document.getElementById('remoteAudio')
  const remoteStream =
    new MediaStream()
  inviter.sessionDescriptionHandler.peerConnection
    .getReceivers()
    .forEach((receiver) => {
      if (receiver.track) {
        remoteStream.addTrack(receiver.track)
      }
    })
  mediaElement.srcObject = remoteStream
  mediaElement.play()
}

function audioConfig(inviter) {
  const mediaElement = document.getElementById('remoteAudio')
  const remoteStream = new MediaStream()
  inviter.sessionDescriptionHandler.peerConnection
    .getReceivers().forEach((receiver) => {
      if (receiver.track) {
        remoteStream.addTrack(receiver.track)
      }
    })
  mediaElement.srcObject = remoteStream
  mediaElement.play()
  inviter.sessionDescriptionHandler.peerConnection
    .getReceivers()
    .forEach((receiver) => {
      if (receiver.track) {
        remoteStream.addTrack(receiver.track)
      }
    });
}

function goToContact() {
  if (!contact.value?.doctype || !contact.value?.docname) {
    console.warn("No doc available to navigate")
    return
  }

  let params = {}
  // Set param key based on doctype
  switch (contact.value.doctype) {
    case "Contact":
      params = { contactId: contact.value.docname }
      break
    case "Lead":
      params = { leadId: contact.value.docname }
      break
    case "Deal":
      params = { dealId: contact.value.docname }
      break
  }
console.log(params)
  router.push({
    name: contact.value.doctype,
    params,
    //hash
  })
}

async function refreshCallLogs(type) {
  if (type == 'incoming') {
    await call('crm.integrations.websprix.api.fetch_and_process_call_logs');
  } else if (type == 'outgoing') {
    await call('crm.integrations.websprix.api.fetch_and_process_outgoing_call_logs');
  }
}

watch(
  () => log.value,
  (value) => {
    console.log(value)
  },
  { immediate: true }
)


async function setup() {
  navigator.mediaDevices.getUserMedia({ audio: true })

  await startupClient()

  try {
    let queueSettings = await call('crm.integrations.websprix.api.get_queue_settings');
    if (queueSettings) {
      joinDTMF = queueSettings.join_dtmf;
      leaveDTMF = queueSettings.leave_dtmf;
    }
  } catch (e) {
    console.log("An error occured fetching queue details", e);
  }

  window.addEventListener('callEvent', function (e) {
    makeOutgoingCall(e.detail.number, sipServer);
  })
  await getOrganizationUsers();
  ringTone = new Audio("/assets/vulero_dialer/frontend/ring.mp3")
}

defineExpose({ setup, makeOutgoingCall })
</script>
<style scoped>
.pulse::before {
  content: '';
  position: absolute;
  border: 1px solid green;
  width: calc(100% + 20px);
  height: calc(100% + 20px);
  border-radius: 50%;
  animation: pulse 1s linear infinite;
}

.pulse::after {
  content: '';
  position: absolute;
  border: 1px solid green;
  width: calc(100% + 20px);
  height: calc(100% + 20px);
  border-radius: 50%;
  animation: pulse 1s linear infinite;
  animation-delay: 0.3s;
}

@keyframes pulse {
  0% {
    transform: scale(0.5);
    opacity: 0;
  }

  50% {
    transform: scale(1);
    opacity: 1;
  }

  100% {
    transform: scale(1.3);
    opacity: 0;
  }
}
</style>
