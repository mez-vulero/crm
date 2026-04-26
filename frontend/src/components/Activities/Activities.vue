<template>
  <ActivityHeader
    v-model="tabIndex"
    v-model:showWhatsappTemplates="showWhatsappTemplates"
    v-model:showFilesUploader="showFilesUploader"
    v-model:emailBox="emailBox"
    :tabs="tabs"
    :title="title"
    :doc="doc"
    :whatsappBox="whatsappBox"
    :modalRef="modalRef"
    @generateContract="showContractDialog = true"
    @recordPayment="showPaymentDialog = true"
    @addCommission="showCommissionDialog = true"
    @scheduleViewing="showViewingDialog = true"
  />
  <FadedScrollableDiv class="flex flex-col h-full overflow-y-auto">
    <div
      v-if="all_activities?.loading"
      class="flex flex-1 flex-col items-center justify-center gap-3 text-xl font-medium text-ink-gray-4"
    >
      <LoadingIndicator class="h-6 w-6" />
      <span>{{ __('Loading...') }}</span>
    </div>
    <div v-else-if="title == 'Events'" class="h-full activity">
      <EventArea :doctype="doctype" :docname="docname" />
    </div>
    <!-- Contracts Tab -->
    <div v-else-if="title == 'Contracts'" class="px-3 pb-3 sm:px-10 sm:pb-5">
      <!-- Contract list -->
      <div v-if="contractsList.data?.length" class="overflow-x-auto">
        <table class="w-full text-left">
          <thead><tr class="text-sm text-ink-gray-5 border-b">
            <th class="py-2 pr-4 font-medium">{{ __('Contract #') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Status') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Date') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Signed') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('PDF') }}</th>
            <th class="py-2 font-medium">{{ __('Actions') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="c in contractsList.data" :key="c.name" class="border-b text-base text-ink-gray-7">
              <td class="py-2.5 pr-4 font-medium">{{ c.name }}</td>
              <td class="py-2.5 pr-4"><Badge :variant="'subtle'" :theme="c.status === 'Signed' ? 'green' : c.status === 'Cancelled' ? 'red' : 'blue'" :label="c.status" size="sm" /></td>
              <td class="py-2.5 pr-4">{{ c.contract_date || '-' }}</td>
              <td class="py-2.5 pr-4">{{ c.signed_date || '-' }}</td>
              <td class="py-2.5 pr-4"><a v-if="c.pdf_attachment" :href="c.pdf_attachment" target="_blank" class="text-ink-blue-5 underline">{{ __('Download') }}</a><span v-else>-</span></td>
              <td class="py-2.5"><Button v-if="c.status === 'Draft' || c.status === 'Sent'" variant="subtle" size="sm" :label="__('Mark Signed')" @click="markSigned(c.name)" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-10 text-ink-gray-5">
        <ContractIcon class="h-10 w-10 mb-3" />
        <p class="text-base">{{ __('No Contracts') }}</p>
      </div>
    </div>
    <!-- Payments Tab -->
    <div v-else-if="title == 'Payments'" class="px-3 pb-3 sm:px-10 sm:pb-5">
      <!-- Summary bar -->
      <div v-if="paymentSummary.data" class="grid grid-cols-4 gap-3 mb-4">
        <div class="rounded-lg border p-3"><div class="text-sm text-ink-gray-5">{{ __('Scheduled') }}</div><div class="text-lg font-semibold">{{ fmtAmount(paymentSummary.data.total_scheduled) }}</div></div>
        <div class="rounded-lg border p-3"><div class="text-sm text-ink-gray-5">{{ __('Collected') }}</div><div class="text-lg font-semibold text-green-600">{{ fmtAmount(paymentSummary.data.total_collected) }}</div></div>
        <div class="rounded-lg border p-3"><div class="text-sm text-ink-gray-5">{{ __('Outstanding') }}</div><div class="text-lg font-semibold text-orange-600">{{ fmtAmount(paymentSummary.data.outstanding) }}</div></div>
        <div class="rounded-lg border p-3"><div class="text-sm text-ink-gray-5">{{ __('Overdue') }}</div><div class="text-lg font-semibold text-red-600">{{ paymentSummary.data.overdue_count || 0 }}</div></div>
      </div>
      <!-- Payment Schedule -->
      <div class="flex items-center justify-between mb-2">
        <h4 class="text-base font-medium text-ink-gray-7">{{ __('Payment Schedule') }}</h4>
        <Button
          v-if="paymentScheduleRows.length && scheduleDirty"
          variant="solid"
          size="sm"
          :label="__('Save Schedule')"
          :loading="savingSchedule"
          @click="savePaymentSchedule"
        />
      </div>
      <div v-if="paymentScheduleRows.length" class="overflow-x-auto mb-6">
        <table class="w-full text-left">
          <thead><tr class="text-sm text-ink-gray-5 border-b">
            <th class="py-2 pr-4 font-medium">{{ __('Milestone') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Due Date') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Amount') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Status') }}</th>
            <th class="py-2 font-medium">{{ __('Payment Date') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="row in paymentScheduleRows" :key="row.name" class="border-b text-base" :class="row.due_date && row.due_date < todayStr && row.status !== 'Paid' ? 'text-red-600' : 'text-ink-gray-7'">
              <td class="py-2.5 pr-4">
                <input
                  v-model="row.milestone"
                  type="text"
                  class="w-full bg-transparent border-b border-transparent hover:border-ink-gray-3 focus:border-ink-blue-5 outline-none px-1 py-0.5"
                  @input="markScheduleDirty"
                />
              </td>
              <td class="py-2.5 pr-4">
                <input
                  v-model="row.due_date"
                  type="date"
                  class="w-full bg-transparent border-b border-transparent hover:border-ink-gray-3 focus:border-ink-blue-5 outline-none px-1 py-0.5"
                  @input="markScheduleDirty"
                />
              </td>
              <td class="py-2.5 pr-4">
                <input
                  v-model.number="row.amount"
                  type="number"
                  class="w-32 bg-transparent border-b border-transparent hover:border-ink-gray-3 focus:border-ink-blue-5 outline-none px-1 py-0.5 text-right"
                  @input="markScheduleDirty"
                />
              </td>
              <td class="py-2.5 pr-4"><Badge :variant="'subtle'" :theme="row.status === 'Paid' ? 'green' : row.status === 'Overdue' ? 'red' : 'orange'" :label="row.status" size="sm" /></td>
              <td class="py-2.5">{{ row.payment_date || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- Payment Collections -->
      <h4 class="text-base font-medium text-ink-gray-7 mb-2">{{ __('Payment Collections') }}</h4>
      <div v-if="paymentCollections.data?.length" class="overflow-x-auto">
        <table class="w-full text-left">
          <thead><tr class="text-sm text-ink-gray-5 border-b">
            <th class="py-2 pr-4 font-medium">{{ __('Payment #') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Date') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Amount') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Method') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Status') }}</th>
            <th class="py-2 font-medium">{{ __('Invoice') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="p in paymentCollections.data" :key="p.name" class="border-b text-base text-ink-gray-7">
              <td class="py-2.5 pr-4 font-medium">{{ p.name }}</td>
              <td class="py-2.5 pr-4">{{ p.payment_date || '-' }}</td>
              <td class="py-2.5 pr-4">{{ fmtAmount(p.amount_received) }}</td>
              <td class="py-2.5 pr-4">{{ p.payment_method || '-' }}</td>
              <td class="py-2.5 pr-4"><Badge :variant="'subtle'" :theme="p.status === 'Received' ? 'green' : p.status === 'Refunded' ? 'red' : 'orange'" :label="p.status" size="sm" /></td>
              <td class="py-2.5"><Button v-if="!p.invoice" variant="subtle" size="sm" :label="__('Gen. Invoice')" @click="generateInvoice(p.name)" /><a v-else-if="p.invoice_pdf" :href="p.invoice_pdf" target="_blank" class="text-ink-blue-5 underline">{{ p.invoice }}</a><span v-else>{{ p.invoice }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="text-center py-6 text-ink-gray-5 text-sm">{{ __('No payments recorded yet') }}</div>
    </div>
    <!-- Commissions Tab -->
    <div v-else-if="title == 'Commissions'" class="px-3 pb-3 sm:px-10 sm:pb-5">
      <!-- Commission list -->
      <div v-if="commissionsList.data?.length" class="overflow-x-auto">
        <table class="w-full text-left">
          <thead><tr class="text-sm text-ink-gray-5 border-b">
            <th class="py-2 pr-4 font-medium">{{ __('Agent') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Role') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Rate %') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Amount') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Split %') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Final') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Trigger') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Status') }}</th>
            <th class="py-2 font-medium">{{ __('Actions') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="cm in commissionsList.data" :key="cm.name" class="border-b text-base text-ink-gray-7">
              <td class="py-2.5 pr-4">{{ cm.agent_name }}</td>
              <td class="py-2.5 pr-4">{{ cm.role }}</td>
              <td class="py-2.5 pr-4">{{ cm.commission_rate }}%</td>
              <td class="py-2.5 pr-4">{{ fmtAmount(cm.commission_amount) }}</td>
              <td class="py-2.5 pr-4">{{ cm.split_percentage }}%</td>
              <td class="py-2.5 pr-4 font-medium">{{ fmtAmount(cm.final_commission) }}</td>
              <td class="py-2.5 pr-4">{{ cm.trigger_event }}</td>
              <td class="py-2.5 pr-4"><Badge :variant="'subtle'" :theme="cm.status === 'Approved' ? 'green' : cm.status === 'Paid' ? 'blue' : cm.status === 'Cancelled' ? 'red' : 'orange'" :label="cm.status" size="sm" /></td>
              <td class="py-2.5"><Button v-if="cm.status === 'Pending'" variant="subtle" size="sm" :label="__('Approve')" @click="approveCommission(cm.name)" /></td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="text-base font-semibold text-ink-gray-9 border-t">
              <td class="py-2.5 pr-4" colspan="5">{{ __('Total') }}</td>
              <td class="py-2.5 pr-4">{{ fmtAmount(commissionsList.data.reduce((s, c) => s + (c.final_commission || 0), 0)) }}</td>
              <td colspan="3"></td>
            </tr>
          </tfoot>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-10 text-ink-gray-5">
        <CommissionIcon class="h-10 w-10 mb-3" />
        <p class="text-base">{{ __('No Commissions') }}</p>
      </div>
    </div>
    <!-- Viewings Tab -->
    <div v-else-if="title == 'Viewings'" class="px-3 pb-3 sm:px-10 sm:pb-5">
      <div v-if="viewingsList.data?.length" class="overflow-x-auto">
        <table class="w-full text-left">
          <thead><tr class="text-sm text-ink-gray-5 border-b">
            <th class="py-2 pr-4 font-medium">{{ __('Date') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Time') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Status') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Agent') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Project') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Unit') }}</th>
            <th class="py-2 pr-4 font-medium">{{ __('Feedback') }}</th>
            <th class="py-2 font-medium">{{ __('Actions') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="v in viewingsList.data" :key="v.name" class="border-b text-base text-ink-gray-7">
              <td class="py-2.5 pr-4">{{ v.appointment_date || '-' }}</td>
              <td class="py-2.5 pr-4">{{ v.appointment_time || '-' }}</td>
              <td class="py-2.5 pr-4">
                <Badge :variant="'subtle'" :theme="v.status === 'Completed' ? 'green' : v.status === 'No-Show' ? 'red' : v.status === 'Cancelled' ? 'gray' : 'orange'" :label="v.status" size="sm" />
              </td>
              <td class="py-2.5 pr-4">{{ v.assigned_agent || '-' }}</td>
              <td class="py-2.5 pr-4">{{ v.project || '-' }}</td>
              <td class="py-2.5 pr-4">{{ v.unit || '-' }}</td>
              <td class="py-2.5 pr-4 max-w-[12rem] truncate">{{ v.feedback || '-' }}</td>
              <td class="py-2.5">
                <div v-if="v.status === 'Scheduled'" class="flex gap-1">
                  <Button variant="subtle" size="sm" :label="__('Complete')" @click="updateViewingStatus(v.name, 'Completed')" />
                  <Button variant="ghost" size="sm" :label="__('No-Show')" @click="updateViewingStatus(v.name, 'No-Show')" />
                  <Button variant="ghost" size="sm" :label="__('Cancel')" @click="updateViewingStatus(v.name, 'Cancelled')" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-10 text-ink-gray-5">
        <CalendarIcon class="h-10 w-10 mb-3" />
        <p class="text-base">{{ __('No Viewing Appointments') }}</p>
      </div>
    </div>
    <div
      v-else-if="
        activities?.length ||
        (whatsappMessages.data?.length && title == 'WhatsApp')
      "
      class="activities"
    >
      <div v-if="title == 'WhatsApp' && whatsappMessages.data?.length">
        <WhatsAppArea
          v-model="whatsappMessages"
          v-model:reply="replyMessage"
          class="px-3 sm:px-10"
          :messages="whatsappMessages.data"
        />
      </div>
      <div
        v-else-if="title == 'Notes'"
        class="grid grid-cols-1 gap-4 px-3 pb-3 sm:px-10 sm:pb-5 lg:grid-cols-2 xl:grid-cols-3"
      >
        <div
          v-for="note in activities"
          :key="note.name"
          @click="modalRef.showNote(note)"
        >
          <NoteArea v-model="all_activities" :note="note" />
        </div>
      </div>
      <div v-else-if="title == 'Comments'" class="pb-5">
        <div v-for="(comment, i) in activities" :key="comment.name">
          <div
            class="activity grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 px-3 sm:gap-4 sm:px-10"
          >
            <div
              class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-gray-modals"
              :class="
                i != activities.length - 1 ? 'before:h-full' : 'before:h-4'
              "
            >
              <div
                class="flex h-8 w-7 items-center justify-center bg-surface-white"
              >
                <CommentIcon class="text-ink-gray-8" />
              </div>
            </div>
            <CommentArea class="mb-4" :activity="comment" />
          </div>
        </div>
      </div>
      <div v-else-if="title == 'Tasks'" class="px-3 pb-3 sm:px-10 sm:pb-5">
        <TaskArea :modalRef="modalRef" :tasks="activities" :doctype="doctype" />
      </div>
      <div v-else-if="title == 'Calls'" class="activity">
        <div v-for="(call, i) in activities" :key="call.name">
          <div
            class="activity grid grid-cols-[30px_minmax(auto,_1fr)] gap-4 px-3 sm:px-10"
          >
            <div
              class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-gray-modals"
              :class="
                i != activities.length - 1 ? 'before:h-full' : 'before:h-4'
              "
            >
              <div
                class="flex h-8 w-7 items-center justify-center bg-surface-white text-ink-gray-8"
              >
                <MissedCallIcon
                  v-if="call.status == 'No Answer'"
                  class="text-ink-red-4"
                />
                <DeclinedCallIcon v-else-if="call.status == 'Busy'" />
                <component
                  :is="
                    call.type == 'Incoming' ? InboundCallIcon : OutboundCallIcon
                  "
                  v-else
                />
              </div>
            </div>
            <CallArea class="mb-4" :activity="call" />
          </div>
        </div>
      </div>
      <div
        v-else-if="title == 'Attachments'"
        class="px-3 pb-3 sm:px-10 sm:pb-5"
      >
        <AttachmentArea
          :attachments="activities"
          @reload="all_activities.reload() && scroll()"
        />
      </div>
      <template v-else>
        <div
          v-for="(activity, i) in activities"
          :key="activity.name"
          class="activity px-3 sm:px-10"
          :class="
            ['Activity', 'Emails'].includes(title)
              ? 'grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 sm:gap-4'
              : ''
          "
        >
          <div
            v-if="['Activity', 'Emails'].includes(title)"
            class="z-0 relative flex justify-center before:absolute before:left-[50%] before:-z-[1] before:top-0 before:border-l before:border-outline-gray-modals"
            :class="[
              i != activities.length - 1 ? 'before:h-full' : 'before:h-4',
            ]"
          >
            <div
              class="flex h-7 w-7 items-center justify-center bg-surface-white"
              :class="{
                'mt-2.5': ['communication'].includes(activity.activity_type),
                'bg-surface-white': ['added', 'removed', 'changed'].includes(
                  activity.activity_type,
                ),
                'h-8': [
                  'comment',
                  'communication',
                  'incoming_call',
                  'outgoing_call',
                ].includes(activity.activity_type),
              }"
            >
              <UserAvatar
                v-if="activity.activity_type == 'communication'"
                :user="activity.data.sender"
                size="md"
              />
              <MissedCallIcon
                v-else-if="
                  ['incoming_call', 'outgoing_call'].includes(
                    activity.activity_type,
                  ) && activity.status == 'No Answer'
                "
                class="text-ink-red-4"
              />
              <DeclinedCallIcon
                v-else-if="
                  ['incoming_call', 'outgoing_call'].includes(
                    activity.activity_type,
                  ) && activity.status == 'Busy'
                "
              />
              <component
                :is="activity.icon"
                v-else
                :class="
                  ['added', 'removed', 'changed'].includes(
                    activity.activity_type,
                  )
                    ? 'text-ink-gray-4'
                    : 'text-ink-gray-8'
                "
              />
            </div>
          </div>
          <div
            v-if="activity.activity_type == 'communication'"
            class="pb-5 mt-px"
          >
            <EmailArea :activity="activity" :emailBox="emailBox" />
          </div>
          <div
            v-else-if="activity.activity_type == 'comment'"
            :id="activity.name"
            class="mb-4"
          >
            <CommentArea :activity="activity" />
          </div>
          <div
            v-else-if="activity.activity_type == 'attachment_log'"
            :id="activity.name"
            class="mb-4 flex flex-col gap-2 py-1.5"
          >
            <div class="flex items-center justify-stretch gap-2 text-base">
              <div
                class="inline-flex items-center flex-wrap gap-1.5 text-ink-gray-8 font-medium"
              >
                <span class="font-medium">{{ activity.owner_name }}</span>
                <span class="text-ink-gray-5">{{
                  __(activity.data.type)
                }}</span>
                <a
                  v-if="activity.data.file_url"
                  :href="activity.data.file_url"
                  target="_blank"
                >
                  <span>{{ activity.data.file_name }}</span>
                </a>
                <span v-else>{{ activity.data.file_name }}</span>
                <FeatherIcon
                  v-if="activity.data.is_private"
                  name="lock"
                  class="size-3"
                />
              </div>
              <div class="ml-auto whitespace-nowrap">
                <Tooltip :text="formatDate(activity.creation)">
                  <div class="text-sm text-ink-gray-5">
                    {{ __(timeAgo(activity.creation)) }}
                  </div>
                </Tooltip>
              </div>
            </div>
          </div>
          <div
            v-else-if="
              activity.activity_type == 'incoming_call' ||
              activity.activity_type == 'outgoing_call'
            "
            class="mb-4"
          >
            <CallArea :activity="activity" />
          </div>
          <div v-else class="mb-4 flex flex-col gap-2 py-1.5">
            <div class="flex items-center justify-stretch gap-2 text-base">
              <div
                v-if="activity.other_versions"
                class="inline-flex flex-wrap gap-1.5 text-ink-gray-8 font-medium"
              >
                <span>{{
                  activity.show_others ? __('Hide') : __('Show')
                }}</span>
                <span> +{{ activity.other_versions.length + 1 }} </span>
                <span>{{ __('changes from') }}</span>
                <span>{{ activity.owner_name }}</span>
                <Button
                  class="!size-4"
                  variant="ghost"
                  :icon="SelectIcon"
                  @click="activity.show_others = !activity.show_others"
                />
              </div>
              <div
                v-else
                class="inline-flex items-center flex-wrap gap-1 text-ink-gray-5"
              >
                <span class="font-medium text-ink-gray-8">
                  {{ activity.owner_name }}
                </span>
                <span v-if="activity.type">{{ __(activity.type) }}</span>
                <span
                  v-if="activity.data?.field_label"
                  class="max-w-xs truncate font-medium text-ink-gray-8"
                >
                  {{ __(activity.data.field_label) }}
                </span>
                <span v-if="activity.value">{{ __(activity.value) }}</span>
                <span
                  v-if="activity.data?.old_value"
                  class="max-w-xs font-medium text-ink-gray-8"
                >
                  <div
                    v-if="activity.options == 'User'"
                    class="flex items-center gap-1"
                  >
                    <UserAvatar :user="activity.data.old_value" size="xs" />
                    {{ getUser(activity.data.old_value).full_name }}
                  </div>
                  <div v-else class="truncate">
                    {{ activity.data.old_value }}
                  </div>
                </span>
                <span v-if="activity.to">{{ __('to') }}</span>
                <span
                  v-if="activity.data?.value"
                  class="max-w-xs font-medium text-ink-gray-8"
                >
                  <div
                    v-if="activity.options == 'User'"
                    class="flex items-center gap-1"
                  >
                    <UserAvatar :user="activity.data.value" size="xs" />
                    {{ getUser(activity.data.value).full_name }}
                  </div>
                  <div v-else class="truncate">
                    {{ activity.data.value }}
                  </div>
                </span>
              </div>

              <div class="ml-auto whitespace-nowrap">
                <Tooltip :text="formatDate(activity.creation)">
                  <div class="text-sm text-ink-gray-5">
                    {{ __(timeAgo(activity.creation)) }}
                  </div>
                </Tooltip>
              </div>
            </div>
            <div
              v-if="activity.other_versions && activity.show_others"
              class="flex flex-col gap-0.5"
            >
              <div
                v-for="a in sortByCreation([
                  activity,
                  ...activity.other_versions,
                ])"
                :key="a.creation"
                class="flex items-start justify-stretch gap-2 py-1.5 text-base"
              >
                <div class="inline-flex flex-wrap gap-1 text-ink-gray-5">
                  <span
                    v-if="a.data?.field_label"
                    class="max-w-xs truncate text-ink-gray-5"
                  >
                    {{ __(a.data.field_label) }}
                  </span>
                  <FeatherIcon
                    name="arrow-right"
                    class="mx-1 h-4 w-4 text-ink-gray-5"
                  />
                  <span v-if="a.type">
                    {{ startCase(__(a.type)) }}
                  </span>
                  <span
                    v-if="a.data?.old_value"
                    class="max-w-xs font-medium text-ink-gray-8"
                  >
                    <div
                      v-if="a.options == 'User'"
                      class="flex items-center gap-1"
                    >
                      <UserAvatar :user="a.data.old_value" size="xs" />
                      {{ getUser(a.data.old_value).full_name }}
                    </div>
                    <div v-else class="truncate">
                      {{ a.data.old_value }}
                    </div>
                  </span>
                  <span v-if="a.to">{{ __('to') }}</span>
                  <span
                    v-if="a.data?.value"
                    class="max-w-xs font-medium text-ink-gray-8"
                  >
                    <div
                      v-if="a.options == 'User'"
                      class="flex items-center gap-1"
                    >
                      <UserAvatar :user="a.data.value" size="xs" />
                      {{ getUser(a.data.value).full_name }}
                    </div>
                    <div v-else class="truncate">
                      {{ a.data.value }}
                    </div>
                  </span>
                </div>

                <div class="ml-auto whitespace-nowrap">
                  <Tooltip :text="formatDate(a.creation)">
                    <div class="text-sm text-ink-gray-5">
                      {{ __(timeAgo(a.creation)) }}
                    </div>
                  </Tooltip>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
    <div v-else-if="title == 'Data'" class="h-full flex flex-col px-3 sm:px-10">
      <DataFields
        :doctype="doctype"
        :docname="docname"
        @beforeSave="(data) => emit('beforeSave', data)"
        @afterSave="(data) => emit('afterSave', data)"
      />
    </div>
    <EmptyState
      v-else
      :title="emptyText"
      :description="emptyTextDescription"
      :icon="emptyTextIcon"
      :top="top"
    />
  </FadedScrollableDiv>
  <div>
    <CommunicationArea
      v-if="['Emails', 'Comments', 'Activity'].includes(title)"
      ref="emailBox"
      v-model="doc"
      v-model:reload="reload_email"
      :doctype="doctype"
      @scroll="scroll"
    />
    <WhatsAppBox
      v-if="title == 'WhatsApp'"
      ref="whatsappBox"
      v-model="doc"
      v-model:reply="replyMessage"
      v-model:whatsapp="whatsappMessages"
      :doctype="doctype"
      @scroll="scroll"
    />
  </div>
  <WhatsappTemplateSelectorModal
    v-if="whatsappEnabled"
    v-model="showWhatsappTemplates"
    :doctype="doctype"
    @send="(t) => sendTemplate(t)"
  />
  <AllModals
    ref="modalRef"
    v-model="all_activities"
    :doctype="doctype"
    :doc="doc"
  />
  <FilesUploader
    v-model="showFilesUploader"
    :doctype="doctype"
    :docname="docname"
    @after="
      () => {
        all_activities.reload()
        changeTabTo('attachments')
      }
    "
  />
  <!-- Generate Contract Dialog -->
  <Dialog v-model="showContractDialog" :options="{ title: __('Generate Contract'), size: 'md' }">
    <template #body-content>
      <div class="space-y-1.5">
        <label class="block text-xs text-ink-gray-5">{{ __('Select Template') }}</label>
        <Link
          class="form-control"
          size="md"
          :value="contractTemplate"
          doctype="Contract Template"
          :placeholder="__('Search Contract Template')"
          @change="(data) => (contractTemplate = data)"
        />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Generate')" @click="generateContract" />
    </template>
  </Dialog>
  <!-- Record Payment Dialog -->
  <Dialog v-model="showPaymentDialog" :options="{ title: __('Record Payment'), size: 'lg' }">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <FormControl v-model="paymentForm.schedule_row" :label="__('Payment Schedule Milestone')" type="select" :options="[{ label: __('-- Select --'), value: '' }, ...paymentScheduleRows.map(r => ({ label: r.milestone + ' (' + fmtAmount(r.amount) + ')', value: r.name }))]" />
        <FormControl v-model="paymentForm.amount_received" :label="__('Amount Received')" type="number" />
        <FormControl v-model="paymentForm.payment_method" :label="__('Payment Method')" type="select" :options="[{ label: 'Bank Transfer', value: 'Bank Transfer' }, { label: 'Cash', value: 'Cash' }, { label: 'Cheque', value: 'Cheque' }, { label: 'Online', value: 'Online' }]" />
        <FormControl v-model="paymentForm.reference_number" :label="__('Reference Number')" type="text" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Record Payment')" @click="recordPayment" />
    </template>
  </Dialog>
  <!-- Add Commission Dialog -->
  <Dialog v-model="showCommissionDialog" :options="{ title: __('Add Commission'), size: 'lg' }">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <FormControl v-model="commissionForm.agent" :label="__('Sales Agent (User ID)')" type="text" :placeholder="__('user@example.com')" />
        <FormControl v-model="commissionForm.role" :label="__('Role')" type="select" :options="[{ label: 'Primary Agent', value: 'Primary Agent' }, { label: 'Co-Agent', value: 'Co-Agent' }, { label: 'Referrer', value: 'Referrer' }, { label: 'Manager Override', value: 'Manager Override' }]" />
        <div class="grid grid-cols-2 gap-4">
          <FormControl v-model="commissionForm.commission_rate" :label="__('Commission Rate %')" type="number" />
          <FormControl v-model="commissionForm.split_percentage" :label="__('Split %')" type="number" />
        </div>
        <FormControl v-model="commissionForm.trigger_event" :label="__('Payable When')" type="select" :options="[{ label: 'On Reservation', value: 'On Reservation' }, { label: 'On Contract Signing', value: 'On Contract Signing' }, { label: 'On Full Payment', value: 'On Full Payment' }]" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Add')" @click="addCommission" />
    </template>
  </Dialog>
  <!-- Schedule Viewing Dialog -->
  <Dialog v-model="showViewingDialog" :options="{ title: __('Schedule Viewing'), size: 'lg' }">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-4">
          <FormControl v-model="viewingForm.appointment_date" :label="__('Date')" type="date" required />
          <FormControl v-model="viewingForm.appointment_time" :label="__('Time')" type="time" />
        </div>
        <FormControl v-model="viewingForm.project" :label="__('Project')" type="text" :placeholder="__('Real Estate Project ID')" />
        <FormControl v-model="viewingForm.unit" :label="__('Unit')" type="text" :placeholder="__('Property Unit ID')" />
        <FormControl v-model="viewingForm.assigned_agent" :label="__('Assigned Agent (User ID)')" type="text" :placeholder="__('user@example.com')" />
        <FormControl v-model="viewingForm.notes" :label="__('Notes')" type="textarea" :placeholder="__('Any additional notes...')" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Schedule')" @click="scheduleViewing" />
    </template>
  </Dialog>
</template>
<script setup>
import ActivityHeader from '@/components/Activities/ActivityHeader.vue'
import EmailArea from '@/components/Activities/EmailArea.vue'
import CommentArea from '@/components/Activities/CommentArea.vue'
import CallArea from '@/components/Activities/CallArea.vue'
import NoteArea from '@/components/Activities/NoteArea.vue'
import TaskArea from '@/components/Activities/TaskArea.vue'
import AttachmentArea from '@/components/Activities/AttachmentArea.vue'
import DataFields from '@/components/Activities/DataFields.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import ActivityIcon from '@/components/Icons/ActivityIcon.vue'
import EmailIcon from '@/components/Icons/EmailIcon.vue'
import DetailsIcon from '@/components/Icons/DetailsIcon.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import AttachmentIcon from '@/components/Icons/AttachmentIcon.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import MoneyIcon from '@/components/Icons/MoneyIcon.vue'
import ContractIcon from '@/components/Icons/ContractIcon.vue'
import CommissionIcon from '@/components/Icons/CommissionIcon.vue'
import EventArea from '@/components/Activities/EventArea.vue'
import WhatsAppArea from '@/components/Activities/WhatsAppArea.vue'
import WhatsAppBox from '@/components/Activities/WhatsAppBox.vue'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import LeadsIcon from '@/components/Icons/LeadsIcon.vue'
import DealsIcon from '@/components/Icons/DealsIcon.vue'
import DotIcon from '@/components/Icons/DotIcon.vue'
import CommentIcon from '@/components/Icons/CommentIcon.vue'
import SelectIcon from '@/components/Icons/SelectIcon.vue'
import MissedCallIcon from '@/components/Icons/MissedCallIcon.vue'
import DeclinedCallIcon from '@/components/Icons/DeclinedCallIcon.vue'
import InboundCallIcon from '@/components/Icons/InboundCallIcon.vue'
import OutboundCallIcon from '@/components/Icons/OutboundCallIcon.vue'
import FadedScrollableDiv from '@/components/FadedScrollableDiv.vue'
import CommunicationArea from '@/components/CommunicationArea.vue'
import WhatsappTemplateSelectorModal from '@/components/Modals/WhatsappTemplateSelectorModal.vue'
import AllModals from '@/components/Activities/AllModals.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import Link from '@/components/Controls/Link.vue'
import { timeAgo, formatDate, startCase } from '@/utils'
import { globalStore } from '@/stores/global'
import { usersStore } from '@/stores/users'
import { whatsappEnabled } from '@/composables/settings'
import { useDocument } from '@/data/document'
import { useTelemetry } from 'frappe-ui/frappe'
import { Badge, Button, Dialog, FormControl, Tooltip, createResource, call, toast } from 'frappe-ui'
import { useElementVisibility } from '@vueuse/core'
import {
  ref,
  computed,
  h,
  markRaw,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount,
} from 'vue'
import { useRoute } from 'vue-router'

const { $socket } = globalStore()
const { getUser } = usersStore()
const { capture } = useTelemetry()

const props = defineProps({
  doctype: { type: String, default: 'CRM Lead' },
  docname: { type: String, default: '' },
  tabs: { type: Array, default: () => [] },
})

const emit = defineEmits(['beforeSave', 'afterSave'])

const route = useRoute()

const reload = defineModel('reload', { type: Boolean, default: false })
const tabIndex = defineModel('tabIndex', { type: Number, default: 0 })

const { document: _document } = useDocument(props.doctype, props.docname)

const doc = computed(() => _document.doc || {})

const paymentScheduleRows = computed(() => doc.value.re_payment_schedule || [])
const paymentScheduleTotal = computed(() =>
  paymentScheduleRows.value.reduce((sum, row) => sum + (row.amount || 0), 0),
)
const paymentScheduleTotalPercent = computed(() =>
  paymentScheduleRows.value.reduce(
    (sum, row) => sum + (row.percentage || 0),
    0,
  ),
)
function fmtAmount(val) {
  if (!val) return '-'
  return Number(val).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const todayStr = new Date().toISOString().split('T')[0]

// Inline-editable payment schedule
const scheduleDirty = ref(false)
const savingSchedule = ref(false)

function markScheduleDirty() {
  scheduleDirty.value = true
}

async function savePaymentSchedule() {
  if (!paymentScheduleRows.value.length) return
  savingSchedule.value = true
  try {
    const dealDoc = await call('frappe.client.get_doc', {
      doctype: 'CRM Deal',
      name: props.docname,
    })
    dealDoc.re_payment_schedule = paymentScheduleRows.value.map((r) => ({
      ...r,
      amount: r.amount || 0,
    }))
    await call('frappe.client.set_value', {
      doctype: 'CRM Deal',
      name: props.docname,
      fieldname: 're_payment_schedule',
      value: dealDoc.re_payment_schedule,
    }).catch(async () => {
      // Fallback: full doc save if set_value can't accept child rows
      await call('frappe.client.save', { doc: dealDoc })
    })
    scheduleDirty.value = false
    paymentSummary.reload()
    toast.success(__('Payment schedule saved'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Failed to save payment schedule'))
  } finally {
    savingSchedule.value = false
  }
}

// Contracts resources
const contractsList = createResource({
  url: 'frappe.client.get_list',
  makeParams() {
    return {
      doctype: 'Property Contract',
      filters: { deal: props.docname },
      fields: ['name', 'status', 'contract_date', 'signed_date', 'template', 'pdf_attachment'],
      order_by: 'creation desc',
      page_length: 50,
    }
  },
  auto: false,
})

const showContractDialog = ref(false)
const contractTemplate = ref('')

async function generateContract() {
  if (!contractTemplate.value) {
    toast.error(__('Please select a template'))
    return
  }
  try {
    const doc = await call('frappe.client.insert', {
      doc: {
        doctype: 'Property Contract',
        deal: props.docname,
        template: contractTemplate.value,
      },
    })
    await call('crm.fcrm.doctype.property_contract.property_contract.generate_contract', {
      contract_name: doc.name,
    })
    showContractDialog.value = false
    contractTemplate.value = ''
    contractsList.reload()
    toast.success(__('Contract generated'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error generating contract'))
  }
}

async function markSigned(contractName) {
  try {
    await call('crm.fcrm.doctype.property_contract.property_contract.mark_as_signed', {
      contract_name: contractName,
    })
    contractsList.reload()
    toast.success(__('Contract marked as signed'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error'))
  }
}

// Payment resources
const paymentCollections = createResource({
  url: 'frappe.client.get_list',
  makeParams() {
    return {
      doctype: 'Payment Collection',
      filters: { deal: props.docname },
      fields: ['name', 'amount_received', 'payment_date', 'payment_method', 'reference_number', 'status', 'invoice', 'milestone_description'],
      order_by: 'creation desc',
      page_length: 50,
    }
  },
  auto: false,
})

const paymentSummary = createResource({
  url: 'crm.fcrm.doctype.payment_collection.payment_collection.get_payment_summary',
  makeParams() {
    return { deal: props.docname }
  },
  auto: false,
})

const showPaymentDialog = ref(false)
const paymentForm = ref({
  schedule_row: '',
  amount_received: 0,
  payment_method: 'Bank Transfer',
  reference_number: '',
})

async function recordPayment() {
  if (!paymentForm.value.amount_received) {
    toast.error(__('Amount is required'))
    return
  }
  try {
    const scheduleRow = paymentScheduleRows.value.find(
      (r) => r.name === paymentForm.value.schedule_row,
    )
    await call('frappe.client.insert', {
      doc: {
        doctype: 'Payment Collection',
        deal: props.docname,
        payment_schedule_row: paymentForm.value.schedule_row || undefined,
        milestone_description: scheduleRow?.milestone || '',
        scheduled_amount: scheduleRow?.amount || 0,
        amount_received: paymentForm.value.amount_received,
        payment_method: paymentForm.value.payment_method,
        reference_number: paymentForm.value.reference_number,
      },
    })
    showPaymentDialog.value = false
    paymentForm.value = { schedule_row: '', amount_received: 0, payment_method: 'Bank Transfer', reference_number: '' }
    paymentCollections.reload()
    paymentSummary.reload()
    toast.success(__('Payment recorded'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error recording payment'))
  }
}

async function generateInvoice(paymentName) {
  try {
    const inv = await call('frappe.client.insert', {
      doc: {
        doctype: 'Property Invoice',
        deal: props.docname,
        payment_collection: paymentName,
      },
    })
    await call('crm.fcrm.doctype.property_invoice.property_invoice.generate_invoice_pdf', {
      invoice_name: inv.name,
    })
    paymentCollections.reload()
    toast.success(__('Invoice generated'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error generating invoice'))
  }
}

// Commissions resources
const commissionsList = createResource({
  url: 'crm.fcrm.doctype.sales_commission.sales_commission.get_commissions_for_deal',
  makeParams() {
    return { deal: props.docname }
  },
  auto: false,
})

const showCommissionDialog = ref(false)
const commissionForm = ref({
  agent: '',
  role: 'Primary Agent',
  commission_rate: 0,
  split_percentage: 100,
  trigger_event: 'On Reservation',
})

async function addCommission() {
  if (!commissionForm.value.agent) {
    toast.error(__('Agent is required'))
    return
  }
  try {
    await call('frappe.client.insert', {
      doc: {
        doctype: 'Sales Commission',
        deal: props.docname,
        agent: commissionForm.value.agent,
        role: commissionForm.value.role,
        commission_rate: commissionForm.value.commission_rate,
        split_percentage: commissionForm.value.split_percentage,
        trigger_event: commissionForm.value.trigger_event,
      },
    })
    showCommissionDialog.value = false
    commissionForm.value = { agent: '', role: 'Primary Agent', commission_rate: 0, split_percentage: 100, trigger_event: 'On Reservation' }
    commissionsList.reload()
    toast.success(__('Commission added'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error adding commission'))
  }
}

async function approveCommission(name) {
  try {
    await call('crm.fcrm.doctype.sales_commission.sales_commission.approve_commission', {
      commission_name: name,
    })
    commissionsList.reload()
    toast.success(__('Commission approved'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error'))
  }
}

// Viewings resources
const viewingsList = createResource({
  url: 'crm.fcrm.doctype.viewing_appointment.viewing_appointment.get_appointments',
  makeParams() {
    const params = {}
    if (props.doctype === 'CRM Lead') params.lead = props.docname
    else if (props.doctype === 'CRM Deal') params.deal = props.docname
    return params
  },
  auto: false,
})

const showViewingDialog = ref(false)
const viewingForm = ref({
  appointment_date: '',
  appointment_time: '',
  project: '',
  unit: '',
  assigned_agent: '',
  notes: '',
})

async function scheduleViewing() {
  if (!viewingForm.value.appointment_date) {
    toast.error(__('Date is required'))
    return
  }
  try {
    const params = {
      appointment_date: viewingForm.value.appointment_date,
      appointment_time: viewingForm.value.appointment_time || undefined,
      project: viewingForm.value.project || undefined,
      unit: viewingForm.value.unit || undefined,
      assigned_agent: viewingForm.value.assigned_agent || undefined,
      notes: viewingForm.value.notes || undefined,
    }
    if (props.doctype === 'CRM Lead') params.lead = props.docname
    else if (props.doctype === 'CRM Deal') params.deal = props.docname

    await call('crm.fcrm.doctype.viewing_appointment.viewing_appointment.schedule_viewing', params)
    showViewingDialog.value = false
    viewingForm.value = { appointment_date: '', appointment_time: '', project: '', unit: '', assigned_agent: '', notes: '' }
    viewingsList.reload()
    toast.success(__('Viewing scheduled'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error scheduling viewing'))
  }
}

async function updateViewingStatus(name, status) {
  try {
    await call('crm.fcrm.doctype.viewing_appointment.viewing_appointment.update_status', {
      appointment_name: name,
      status: status,
    })
    viewingsList.reload()
    toast.success(__('Status updated'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Error'))
  }
}

const reload_email = ref(false)
const modalRef = ref(null)
const showFilesUploader = ref(false)

const title = computed(() => props.tabs?.[tabIndex.value]?.name || 'Activity')

// Auto-load tab data when switching tabs
watch(
  () => title.value,
  (newTitle) => {
    if (newTitle === 'Contracts' && !contractsList.data) contractsList.fetch()
    if (newTitle === 'Payments') {
      if (!paymentCollections.data) paymentCollections.fetch()
      if (!paymentSummary.data) paymentSummary.fetch()
    }
    if (newTitle === 'Commissions' && !commissionsList.data) commissionsList.fetch()
    if (newTitle === 'Viewings' && !viewingsList.data) viewingsList.fetch()
  },
)

const changeTabTo = (tabName) => {
  const tabNames = props.tabs?.map((tab) => tab.name?.toLowerCase())
  const index = tabNames?.indexOf(tabName)
  if (index == -1) return
  tabIndex.value = index
}

const all_activities = createResource({
  url: 'crm.api.activities.get_activities',
  params: { name: props.docname },
  cache: ['activity', props.docname],
  auto: true,
  transform: ([versions, calls, notes, tasks, attachments]) => {
    return { versions, calls, notes, tasks, attachments }
  },
  onSuccess: () => nextTick(() => scroll()),
})

const showWhatsappTemplates = ref(false)

const whatsappMessages = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_messages',
  cache: ['whatsapp_messages', props.docname],
  params: {
    reference_doctype: props.doctype,
    reference_name: props.docname,
  },
  auto: whatsappEnabled.value,
  transform: (data) => sortByCreation(data),
  onSuccess: () => nextTick(() => scroll()),
})

onBeforeUnmount(() => {
  $socket.off('whatsapp_message')
})

onMounted(() => {
  $socket.on('whatsapp_message', (data) => {
    if (
      data.reference_doctype === props.doctype &&
      data.reference_name === props.docname
    ) {
      whatsappMessages.reload()
    }
  })

  nextTick(() => {
    const hash = route.hash.slice(1) || null
    let tabNames = props.tabs?.map((tab) => tab.name)
    if (!tabNames?.includes(hash)) {
      scroll(hash)
    }
  })
})

function sendTemplate(template) {
  showWhatsappTemplates.value = false
  capture('send_whatsapp_template', { doctype: props.doctype })
  createResource({
    url: 'crm.api.whatsapp.send_whatsapp_template',
    params: {
      reference_doctype: props.doctype,
      reference_name: props.docname,
      to: doc.value.mobile_no,
      template,
    },
    auto: true,
    onError: (error) => {
      toast.error(error.messages?.[0] || __('Failed to send WhatsApp template'))
    },
    onSuccess: () => whatsappMessages.reload(),
  })
}

const replyMessage = ref({})

function get_activities() {
  if (!all_activities.data?.versions) return []
  if (!all_activities.data?.calls.length)
    return all_activities.data.versions || []
  return [...all_activities.data.versions, ...all_activities.data.calls]
}

const activities = computed(() => {
  let _activities = []
  if (title.value == 'Activity') {
    _activities = get_activities()
  } else if (title.value == 'Emails') {
    if (!all_activities.data?.versions) return []
    _activities = all_activities.data.versions.filter(
      (activity) => activity.activity_type === 'communication',
    )
  } else if (title.value == 'Comments') {
    if (!all_activities.data?.versions) return []
    _activities = all_activities.data.versions.filter(
      (activity) => activity.activity_type === 'comment',
    )
  } else if (title.value == 'Calls') {
    if (!all_activities.data?.calls) return []
    return sortByCreation(all_activities.data.calls)
  } else if (title.value == 'Tasks') {
    if (!all_activities.data?.tasks) return []
    return sortByModified(all_activities.data.tasks)
  } else if (title.value == 'Notes') {
    if (!all_activities.data?.notes) return []
    return sortByModified(all_activities.data.notes)
  } else if (title.value == 'Attachments') {
    if (!all_activities.data?.attachments) return []
    return sortByModified(all_activities.data.attachments)
  }

  _activities.forEach((activity) => {
    activity.icon = timelineIcon(activity.activity_type, activity.is_lead)

    if (
      activity.activity_type == 'incoming_call' ||
      activity.activity_type == 'outgoing_call' ||
      activity.activity_type == 'communication'
    )
      return

    update_activities_details(activity)

    if (activity.other_versions) {
      activity.show_others = false
      activity.other_versions.forEach((other_version) => {
        update_activities_details(other_version)
      })
    }
  })
  return sortByCreation(_activities)
})

function sortByCreation(list) {
  return list.sort((a, b) => new Date(a.creation) - new Date(b.creation))
}
function sortByModified(list) {
  return list.sort((b, a) => new Date(a.modified) - new Date(b.modified))
}

function update_activities_details(activity) {
  activity.owner_name = getUser(activity.owner).full_name
  activity.type = ''
  activity.value = ''
  activity.to = ''

  if (activity.activity_type == 'creation') {
    activity.type = activity.data
  } else if (activity.activity_type == 'added') {
    activity.type = 'added'
    activity.value = 'as'
  } else if (activity.activity_type == 'removed') {
    activity.type = 'removed'
    activity.value = 'value'
  } else if (activity.activity_type == 'changed') {
    activity.type = 'changed'
    activity.value = 'from'
    activity.to = 'to'
  }
}

const top = computed(() => {
  if (['Activity', 'Emails', 'Comments'].includes(title.value)) {
    return '32.3%'
  }
  return '30%'
})

const emptyText = computed(() => {
  let text = 'No Activities Found'
  if (title.value == 'Emails') {
    text = 'No Emails Found'
  } else if (title.value == 'Comments') {
    text = 'No Comments Found'
  } else if (title.value == 'Data') {
    text = 'No Data Fields Added Yet'
  } else if (title.value == 'Calls') {
    text = 'No Call History'
  } else if (title.value == 'Notes') {
    text = 'No Notes Found'
  } else if (title.value == 'Tasks') {
    text = 'No Tasks Found'
  } else if (title.value == 'Attachments') {
    text = 'No Attachments Found'
  } else if (title.value == 'WhatsApp') {
    text = 'No WhatsApp Messages Found'
  }
  return text
})

const emptyTextDescription = computed(() => {
  let description =
    'There are no activities to display here. Go ahead and make some changes.'
  if (title.value == 'Emails') {
    description =
      'No emails found in your inbox. New messages will appear here soon.'
  } else if (title.value == 'Comments') {
    description = 'Be the first to add one.'
  } else if (title.value == 'Data') {
    description = 'No data fields have been added yet.'
  } else if (title.value == 'Calls') {
    description = 'No recent calls to display. Log a call or call someone now!'
  } else if (title.value == 'Notes') {
    description = 'Nothing here for now. Add a note to keep track of things.'
  } else if (title.value == 'Tasks') {
    description =
      'Nothing to do at the moment. Start organizing by adding one here.'
  } else if (title.value == 'Attachments') {
    description =
      'No files have been attached yet. Upload files to see them here.'
  } else if (title.value == 'WhatsApp') {
    description = 'Start a conversation now!'
  }
  return description
})

const emptyTextIcon = computed(() => {
  let icon = ActivityIcon
  if (title.value == 'Emails') {
    icon = EmailIcon
  } else if (title.value == 'Comments') {
    icon = CommentIcon
  } else if (title.value == 'Data') {
    icon = DetailsIcon
  } else if (title.value == 'Calls') {
    icon = PhoneIcon
  } else if (title.value == 'Notes') {
    icon = NoteIcon
  } else if (title.value == 'Tasks') {
    icon = TaskIcon
  } else if (title.value == 'Attachments') {
    icon = AttachmentIcon
  } else if (title.value == 'WhatsApp') {
    icon = WhatsAppIcon
  }
  return h(icon, { class: 'text-ink-gray-4' })
})

function timelineIcon(activity_type, is_lead) {
  let icon
  switch (activity_type) {
    case 'creation':
      icon = is_lead ? LeadsIcon : DealsIcon
      break
    case 'deal':
      icon = DealsIcon
      break
    case 'comment':
      icon = CommentIcon
      break
    case 'event':
      icon = CalendarIcon
      break
    case 'incoming_call':
      icon = InboundCallIcon
      break
    case 'outgoing_call':
      icon = OutboundCallIcon
      break
    case 'attachment_log':
      icon = AttachmentIcon
      break
    default:
      icon = DotIcon
  }

  return markRaw(icon)
}

const emailBox = ref(null)
const whatsappBox = ref(null)

watch([reload, reload_email], ([reload_value, reload_email_value]) => {
  if (reload_value || reload_email_value) {
    all_activities.reload()
    _document.reload()
    reload.value = false
    reload_email.value = false
  }
})

function scroll(hash) {
  if (['tasks', 'notes', 'events'].includes(route.hash?.slice(1))) return
  setTimeout(() => {
    let el
    if (!hash) {
      let e = document.getElementsByClassName('activity')
      el = e[e.length - 1]
    } else {
      el = document.getElementById(hash)
    }
    if (el && !useElementVisibility(el).value) {
      el.scrollIntoView({ behavior: 'smooth' })
      el.focus()
    }
  }, 500)
}

defineExpose({ emailBox, all_activities, changeTabTo })
</script>
