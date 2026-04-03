<template>
  <div class="page">
    <div class="toolbar">
      <div class="tab-group">
        <button class="tab" :class="{ on: tab === 'staff' }" @click="tab='staff'; load()">
          가입 신청
          <span v-if="staffPending" class="tab-cnt">{{ staffPending }}</span>
        </button>
        <button class="tab" :class="{ on: tab === 'del' }" @click="tab='del'; loadDel()">
          회원 삭제 요청
          <span v-if="delPending" class="tab-cnt">{{ delPending }}</span>
        </button>
        <button class="tab" :class="{ on: tab === 'loaner' }" @click="tab='loaner'; loadLoaner()">
          대여기기 미반납
          <span v-if="loanerPending" class="tab-cnt">{{ loanerPending }}</span>
        </button>
      </div>
      <select v-model="filterStatus" class="sel" @change="tab==='staff'?load():tab==='del'?loadDel():loadLoaner()" style="margin-left:auto">
        <option value="">전체 상태</option>
        <option value="대기">대기</option>
        <option value="승인">승인</option>
        <option value="반려">반려</option>
      </select>
      <button class="btn sm" @click="tab==='staff'?load():tab==='del'?loadDel():loadLoaner()">새로고침</button>
    </div>

    <!-- ── 가입 신청 탭 ── -->
    <div v-if="tab === 'staff'" class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>#</th><th>이름</th><th>아이디</th><th>매장</th>
            <th>신청일시</th><th>상태</th><th>메모</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="8" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!requests.length"><td colspan="8" class="empty">신청 내역이 없습니다</td></tr>
          <tr v-for="r in requests" :key="r.id">
            <td class="mono" style="font-size:10px">{{ r.id }}</td>
            <td>{{ r.name }}</td>
            <td class="mono">{{ r.login_id }}</td>
            <td>{{ r.store_name || `#${r.store_id}` }}</td>
            <td class="mono" style="font-size:10px">{{ fmtDt(r.created_at) }}</td>
            <td>
              <span class="tag" :class="statusClass(r.status)">{{ r.status }}</span>
            </td>
            <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;color:var(--tx3)">
              {{ r.memo || '—' }}
            </td>
            <td>
              <div v-if="r.status === '대기'" class="actions">
                <button class="btn xs gr" @click="openApprove(r)">승인</button>
                <button class="btn xs re" @click="openReject(r)">반려</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── 회원 삭제 요청 탭 ── -->
    <div v-if="tab === 'del'" class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>회원명</th><th>전화번호</th><th>요청자</th>
            <th>삭제 사유</th><th>요청일시</th><th>상태</th><th>처리자</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="delLoading"><td colspan="8" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!delRequests.length"><td colspan="8" class="empty">삭제 요청 내역이 없습니다</td></tr>
          <tr v-for="r in delRequests" :key="r.id">
            <td>{{ r.customer_name || r.original_value?.name || '—' }}</td>
            <td class="mono" style="font-size:11px">{{ r.customer_phone || r.original_value?.phone || '—' }}</td>
            <td style="font-size:11px">{{ r.requester_name || '—' }}</td>
            <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;color:var(--tx3)">
              {{ r.exception_reason || '—' }}
            </td>
            <td class="mono" style="font-size:10px">{{ fmtDt(r.requested_at) }}</td>
            <td>
              <span class="tag" :class="statusClass(r.status)">{{ r.status }}</span>
            </td>
            <td style="font-size:11px;color:var(--tx3)">
              {{ r.approver_name || '—' }}
              <span v-if="r.rejected_reason" class="rej-reason">{{ r.rejected_reason }}</span>
            </td>
            <td>
              <div v-if="r.status === '대기'" class="actions">
                <button class="btn xs gr" @click="openDelApprove(r)">승인</button>
                <button class="btn xs re" @click="openDelReject(r)">반려</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── 대여기기 미반납 탭 ── -->
    <div v-if="tab === 'loaner'" class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>고객명</th><th>대여 기기</th><th>요청자</th>
            <th>사유</th><th>요청일시</th><th>상태</th><th>처리자</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loanerLoading"><td colspan="8" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!loanerRequests.length"><td colspan="8" class="empty">미반납 요청 내역이 없습니다</td></tr>
          <tr v-for="r in loanerRequests" :key="r.id">
            <td>{{ r.original_value?.customer_name || r.customer_name || '—' }}</td>
            <td style="font-size:11px;font-weight:600">{{ r.original_value?.loaner_note || '—' }}</td>
            <td style="font-size:11px">{{ r.requester_name || '—' }}</td>
            <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;color:var(--tx3)">
              {{ r.exception_reason || '—' }}
            </td>
            <td class="mono" style="font-size:10px">{{ fmtDt(r.requested_at) }}</td>
            <td>
              <span class="tag" :class="statusClass(r.status)">{{ r.status }}</span>
            </td>
            <td style="font-size:11px;color:var(--tx3)">
              {{ r.approver_name || '—' }}
              <template v-if="r.changed_value?.decision">
                <span class="tag" :class="r.changed_value.decision==='청구'?'tag-re':'tag-gr'" style="margin-left:4px">{{ r.changed_value.decision }}</span>
              </template>
              <span v-if="r.rejected_reason" class="rej-reason">{{ r.rejected_reason }}</span>
            </td>
            <td>
              <div v-if="r.status === '대기'" class="actions">
                <button class="btn xs gr" @click="openLoanerApprove(r)">처리</button>
                <button class="btn xs re" @click="openLoanerReject(r)">반려</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 가입 승인 모달 -->
    <div v-if="showApproveModal" class="modal-backdrop" @click.self="showApproveModal = false">
      <div class="modal">
        <div class="modal-hd">가입 승인</div>
        <div class="info-row"><span class="info-k">이름</span><span>{{ approveTarget?.name }}</span></div>
        <div class="info-row"><span class="info-k">아이디</span><span class="mono">{{ approveTarget?.login_id }}</span></div>
        <div class="info-row"><span class="info-k">매장</span><span>{{ approveTarget?.store_name }}</span></div>
        <div class="field">
          <label>부여 역할</label>
          <select v-model="approveForm.role_granted" class="inp">
            <option value="매니저">매니저</option>
            <option value="시니어">시니어</option>
            <option value="총괄">총괄</option>
            <option value="사장">사장</option>
          </select>
        </div>
        <div v-if="approveError" class="err">{{ approveError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showApproveModal = false">취소</button>
          <button class="btn pr" :disabled="approveLoading" @click="submitApprove">
            {{ approveLoading ? '처리 중…' : '승인 확정' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 가입 반려 모달 -->
    <div v-if="showRejectModal" class="modal-backdrop" @click.self="showRejectModal = false">
      <div class="modal">
        <div class="modal-hd">가입 반려</div>
        <div class="info-row"><span class="info-k">이름</span><span>{{ rejectTarget?.name }}</span></div>
        <div class="field">
          <label>반려 사유</label>
          <textarea v-model="rejectReason" class="inp" rows="3" placeholder="반려 사유를 입력하세요" />
        </div>
        <div v-if="rejectError" class="err">{{ rejectError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showRejectModal = false">취소</button>
          <button class="btn re" :disabled="rejectLoading" @click="submitReject">
            {{ rejectLoading ? '처리 중…' : '반려' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 회원 삭제 승인 모달 -->
    <div v-if="showDelApproveModal" class="modal-backdrop" @click.self="showDelApproveModal=false">
      <div class="modal">
        <div class="modal-hd" style="color:var(--re)">회원 삭제 승인</div>
        <div style="font-size:12px;color:var(--tx2);background:#fee2e2;border-radius:6px;padding:10px 12px;line-height:1.6">
          이 작업은 <b>되돌릴 수 없습니다.</b><br>회원의 모든 정보가 삭제됩니다.
        </div>
        <div class="info-row"><span class="info-k">회원명</span><span>{{ delApproveTarget?.customer_name }}</span></div>
        <div class="info-row"><span class="info-k">전화번호</span><span class="mono">{{ delApproveTarget?.customer_phone }}</span></div>
        <div class="info-row"><span class="info-k">삭제 사유</span><span style="font-size:11px;color:var(--tx2)">{{ delApproveTarget?.exception_reason }}</span></div>
        <div v-if="delApproveErr" class="err">{{ delApproveErr }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showDelApproveModal=false">취소</button>
          <button class="btn re" :disabled="delApproveLoading" @click="submitDelApprove">
            {{ delApproveLoading ? '처리 중…' : '삭제 승인' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 회원 삭제 반려 모달 -->
    <div v-if="showDelRejectModal" class="modal-backdrop" @click.self="showDelRejectModal=false">
      <div class="modal">
        <div class="modal-hd">삭제 요청 반려</div>
        <div class="info-row"><span class="info-k">회원명</span><span>{{ delRejectTarget?.customer_name }}</span></div>
        <div class="field">
          <label>반려 사유</label>
          <textarea v-model="delRejectReason" class="inp" rows="3" placeholder="반려 사유 (선택)" />
        </div>
        <div v-if="delRejectErr" class="err">{{ delRejectErr }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showDelRejectModal=false">취소</button>
          <button class="btn re" :disabled="delRejectLoading" @click="submitDelReject">
            {{ delRejectLoading ? '처리 중…' : '반려' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 대여기기 미반납 처리 모달 -->
    <div v-if="showLoanerApproveModal" class="modal-backdrop" @click.self="showLoanerApproveModal=false">
      <div class="modal">
        <div class="modal-hd">대여기기 미반납 처리</div>
        <div class="info-row"><span class="info-k">고객명</span><span>{{ loanerApproveTarget?.original_value?.customer_name }}</span></div>
        <div class="info-row"><span class="info-k">대여 기기</span><span style="font-weight:600">{{ loanerApproveTarget?.original_value?.loaner_note }}</span></div>
        <div class="info-row"><span class="info-k">요청 사유</span><span style="font-size:11px;color:var(--tx2)">{{ loanerApproveTarget?.exception_reason }}</span></div>
        <div class="field">
          <label>처리 방법</label>
          <div class="radio-group">
            <label class="radio-opt">
              <input type="radio" v-model="loanerDecision" value="청구" />
              <span>청구 ({{ loanerAmount.toLocaleString() }}원)</span>
            </label>
            <label class="radio-opt">
              <input type="radio" v-model="loanerDecision" value="포기" />
              <span>포기 (청구 안함)</span>
            </label>
          </div>
        </div>
        <template v-if="loanerDecision === '청구'">
          <div class="field">
            <label>청구 금액</label>
            <input v-model.number="loanerAmount" type="number" class="inp" min="0" step="1000" />
          </div>
          <div class="field">
            <label>결제 방법</label>
            <select v-model="loanerPayment" class="inp">
              <option value="">— 미정 —</option>
              <option value="현금">현금</option>
              <option value="이체">이체</option>
              <option value="카드">카드</option>
            </select>
          </div>
        </template>
        <div v-if="loanerApproveErr" class="err">{{ loanerApproveErr }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showLoanerApproveModal=false">취소</button>
          <button class="btn pr" :disabled="loanerApproveLoading" @click="submitLoanerApprove">
            {{ loanerApproveLoading ? '처리 중…' : '처리 확정' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 대여기기 미반납 반려 모달 -->
    <div v-if="showLoanerRejectModal" class="modal-backdrop" @click.self="showLoanerRejectModal=false">
      <div class="modal">
        <div class="modal-hd">미반납 요청 반려</div>
        <div class="info-row"><span class="info-k">고객명</span><span>{{ loanerRejectTarget?.original_value?.customer_name }}</span></div>
        <div class="info-row"><span class="info-k">대여 기기</span><span>{{ loanerRejectTarget?.original_value?.loaner_note }}</span></div>
        <div class="field">
          <label>반려 사유</label>
          <textarea v-model="loanerRejectReason" class="inp" rows="3" placeholder="반려 사유 (선택)" />
        </div>
        <div v-if="loanerRejectErr" class="err">{{ loanerRejectErr }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showLoanerRejectModal=false">취소</button>
          <button class="btn re" :disabled="loanerRejectLoading" @click="submitLoanerReject">
            {{ loanerRejectLoading ? '처리 중…' : '반려' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const tab          = ref('staff')
const filterStatus = ref('대기')

// ── 가입 신청 ──────────────────────────────────────────────────
const requests     = ref([])
const loading      = ref(false)
const staffPending = ref(0)

const showApproveModal = ref(false)
const approveTarget    = ref(null)
const approveForm      = ref({ request_id: null, role_granted: '시니어' })
const approveLoading   = ref(false)
const approveError     = ref('')

const showRejectModal = ref(false)
const rejectTarget    = ref(null)
const rejectReason    = ref('')
const rejectLoading   = ref(false)
const rejectError     = ref('')

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    const res = await api.get('/auth/admin/requests', { params })
    requests.value = res.data
    staffPending.value = res.data.filter(r => r.status === '대기').length
  } catch {
    requests.value = []
  } finally { loading.value = false }
}

function openApprove(r) {
  approveTarget.value = r
  approveForm.value   = { request_id: r.id, role_granted: '시니어' }
  approveError.value  = ''
  showApproveModal.value = true
}

async function submitApprove() {
  approveError.value   = ''
  approveLoading.value = true
  try {
    await api.post('/auth/admin/approve', approveForm.value)
    showApproveModal.value = false
    await load()
  } catch (e) {
    approveError.value = e.response?.data?.detail || '처리 실패'
  } finally { approveLoading.value = false }
}

function openReject(r) {
  rejectTarget.value = r
  rejectReason.value = ''
  rejectError.value  = ''
  showRejectModal.value = true
}

async function submitReject() {
  rejectError.value = ''
  if (!rejectReason.value.trim()) { rejectError.value = '반려 사유를 입력하세요'; return }
  rejectLoading.value = true
  try {
    await api.post('/auth/admin/reject', { request_id: rejectTarget.value.id, reason: rejectReason.value })
    showRejectModal.value = false
    await load()
  } catch (e) {
    rejectError.value = e.response?.data?.detail || '처리 실패'
  } finally { rejectLoading.value = false }
}

// ── 회원 삭제 요청 ─────────────────────────────────────────────
const delRequests  = ref([])
const delLoading   = ref(false)
const delPending   = ref(0)

const showDelApproveModal = ref(false)
const delApproveTarget    = ref(null)
const delApproveLoading   = ref(false)
const delApproveErr       = ref('')

const showDelRejectModal  = ref(false)
const delRejectTarget     = ref(null)
const delRejectReason     = ref('')
const delRejectLoading    = ref(false)
const delRejectErr        = ref('')

async function loadDel() {
  delLoading.value = true
  try {
    const params = { exception_type: '회원삭제' }
    if (filterStatus.value) params.status = filterStatus.value
    const res = await api.get('/approvals', { params })
    delRequests.value = res.data
    delPending.value  = res.data.filter(r => r.status === '대기').length
  } catch {
    delRequests.value = []
  } finally { delLoading.value = false }
}

function openDelApprove(r) {
  delApproveTarget.value = r
  delApproveErr.value    = ''
  showDelApproveModal.value = true
}

async function submitDelApprove() {
  delApproveErr.value    = ''
  delApproveLoading.value = true
  try {
    await api.post(`/approvals/${delApproveTarget.value.id}/approve`)
    showDelApproveModal.value = false
    await loadDel()
  } catch (e) {
    delApproveErr.value = e.response?.data?.detail || '처리 실패'
  } finally { delApproveLoading.value = false }
}

function openDelReject(r) {
  delRejectTarget.value  = r
  delRejectReason.value  = ''
  delRejectErr.value     = ''
  showDelRejectModal.value = true
}

async function submitDelReject() {
  delRejectErr.value     = ''
  delRejectLoading.value = true
  try {
    await api.post(`/approvals/${delRejectTarget.value.id}/reject`, { reason: delRejectReason.value || null })
    showDelRejectModal.value = false
    await loadDel()
  } catch (e) {
    delRejectErr.value = e.response?.data?.detail || '처리 실패'
  } finally { delRejectLoading.value = false }
}

// ── 대여기기 미반납 ────────────────────────────────────────────
const loanerRequests = ref([])
const loanerLoading  = ref(false)
const loanerPending  = ref(0)

const showLoanerApproveModal = ref(false)
const loanerApproveTarget    = ref(null)
const loanerDecision         = ref('청구')
const loanerAmount           = ref(20000)
const loanerPayment          = ref('')
const loanerApproveLoading   = ref(false)
const loanerApproveErr       = ref('')

const showLoanerRejectModal  = ref(false)
const loanerRejectTarget     = ref(null)
const loanerRejectReason     = ref('')
const loanerRejectLoading    = ref(false)
const loanerRejectErr        = ref('')

async function loadLoaner() {
  loanerLoading.value = true
  try {
    const params = { exception_type: '대여기기미반납' }
    if (filterStatus.value) params.status = filterStatus.value
    const res = await api.get('/approvals', { params })
    loanerRequests.value = res.data
    loanerPending.value  = res.data.filter(r => r.status === '대기').length
  } catch {
    loanerRequests.value = []
  } finally { loanerLoading.value = false }
}

function openLoanerApprove(r) {
  loanerApproveTarget.value = r
  loanerDecision.value      = '청구'
  loanerAmount.value        = 20000
  loanerPayment.value       = ''
  loanerApproveErr.value    = ''
  showLoanerApproveModal.value = true
}

async function submitLoanerApprove() {
  loanerApproveErr.value    = ''
  loanerApproveLoading.value = true
  try {
    await api.post(`/approvals/${loanerApproveTarget.value.id}/approve`, {
      decision:       loanerDecision.value,
      payment_method: loanerDecision.value === '청구' ? loanerPayment.value : null,
      charge_amount:  loanerDecision.value === '청구' ? loanerAmount.value : 0,
    })
    showLoanerApproveModal.value = false
    await loadLoaner()
  } catch (e) {
    loanerApproveErr.value = e.response?.data?.detail || '처리 실패'
  } finally { loanerApproveLoading.value = false }
}

function openLoanerReject(r) {
  loanerRejectTarget.value  = r
  loanerRejectReason.value  = ''
  loanerRejectErr.value     = ''
  showLoanerRejectModal.value = true
}

async function submitLoanerReject() {
  loanerRejectErr.value     = ''
  loanerRejectLoading.value = true
  try {
    await api.post(`/approvals/${loanerRejectTarget.value.id}/reject`, { reason: loanerRejectReason.value || null })
    showLoanerRejectModal.value = false
    await loadLoaner()
  } catch (e) {
    loanerRejectErr.value = e.response?.data?.detail || '처리 실패'
  } finally { loanerRejectLoading.value = false }
}

// ── 유틸 ──────────────────────────────────────────────────────
function statusClass(s) {
  return { 'tag-ye': s === '대기', 'tag-gr': s === '승인', 'tag-re': s === '반려' }
}

function fmtDt(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

onMounted(load)
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; }
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:12px; }
.tab-group { display:flex; gap:4px; }
.tab { padding:5px 12px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; color:var(--tx2); font-family:var(--sans); display:inline-flex; align-items:center; gap:5px; }
.tab.on { background:var(--ac); color:#fff; border-color:var(--ac); font-weight:500; }
.tab-cnt { background:rgba(255,255,255,.3); border-radius:10px; padding:0 5px; font-size:10px; font-family:var(--mono); }
.tab:not(.on) .tab-cnt { background:var(--re); color:#fff; }
.sel { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:12px; color:var(--tx); outline:none; cursor:pointer; }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:8px 12px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.mono { font-family:var(--mono); }
.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-re { background:#fee2e2; color:#dc2626; }
.rej-reason { display:block; font-size:10px; color:var(--re); margin-top:2px; }
.actions { display:flex; gap:4px; }
.empty { text-align:center; color:var(--tx3); padding:24px; font-size:12px; }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.pr { background:var(--ac); color:#fff; border-color:var(--ac); }
.btn.re { background:var(--re); color:#fff; border-color:var(--re); }
.btn.sm { padding:4px 10px; font-size:11px; }
.btn.xs { padding:2px 8px; font-size:10px; }
.btn.gr { background:var(--gr); color:#fff; border-color:var(--gr); }
.modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { background:var(--bg2); border-radius:var(--r); padding:20px; width:380px; display:flex; flex-direction:column; gap:12px; }
.modal-hd { font-size:14px; font-weight:700; }
.info-row { display:flex; gap:12px; font-size:12px; align-items:flex-start; }
.info-k { min-width:56px; color:var(--tx3); font-size:10px; font-family:var(--mono); padding-top:1px; }
.field { display:flex; flex-direction:column; gap:4px; }
.field label { font-size:11px; color:var(--tx2); }
.inp { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; resize:vertical; }
.inp:focus { border-color:var(--ac); }
.err { color:var(--re); font-size:11px; }
.modal-ft { display:flex; justify-content:flex-end; gap:8px; }
.radio-group { display:flex; gap:16px; }
.radio-opt { display:flex; align-items:center; gap:6px; font-size:12px; cursor:pointer; }
.radio-opt input { cursor:pointer; }
</style>
