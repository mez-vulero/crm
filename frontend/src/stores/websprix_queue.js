import { createResource, call, toast } from 'frappe-ui'
import { ref } from 'vue'

export const queueJoined = ref(false)
export const queueId = ref(null)
export const queueLoading = ref(false)

createResource({
  url: 'crm.integrations.websprix.api.queue_status',
  cache: 'Websprix Queue Status',
  auto: true,
  onSuccess(data) {
    queueJoined.value = Boolean(data?.joined)
    queueId.value = data?.queue_id || null
  },
})

/**
 * Toggle queue membership. The UI only reflects the new state after the
 * backend confirms success; if the API call fails, the local state is left
 * unchanged and the error is shown to the user.
 */
export async function toggleQueue() {
  if (queueLoading.value) return

  if (!queueId.value) {
    toast.error(
      __(
        'WebSprix Queue is not configured. Set your Queue ID in Settings → Telephony.',
      ),
    )
    return
  }

  const wasJoined = queueJoined.value
  const endpoint = wasJoined
    ? 'crm.integrations.websprix.api.leave_queue'
    : 'crm.integrations.websprix.api.join_queue'

  queueLoading.value = true
  try {
    const result = await call(endpoint)
    if (typeof result?.joined === 'boolean') {
      queueJoined.value = result.joined
    } else {
      queueJoined.value = !wasJoined
    }
    if (result?.queue_id) {
      queueId.value = result.queue_id
    }
    toast.success(
      queueJoined.value
        ? __('Joined queue {0}', [queueId.value])
        : __('Left queue {0}', [queueId.value]),
    )
  } catch (err) {
    const message =
      err?.messages?.[0] ||
      err?.message ||
      (wasJoined
        ? __('Could not leave the queue. Please try again.')
        : __('Could not join the queue. Please try again.'))
    toast.error(message)
  } finally {
    queueLoading.value = false
  }
}
