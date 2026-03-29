<template>
  <div class="page">
    <div class="toolbar">
      <select v-model="filterStatus" class="sel" @change="load">
        <option value="">전체 상태</option>
        <option value="대기">대기</option>
        <option value="승인">승인</option>
        <option value="반려">반려</option>
      </select>
      <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
    </div>

    <div class="card">
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
              <span class="tag" :class="{
                'tag-ye': r.status === '대기',
                'tag-gr': r.status === '승인',
                'tag-re': r.status === '반려',
              }">{{ r.status }}</span>
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

    <!-- 승인 모달 -->
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

    <!-- 반려 모달 -->
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const requests     = ref([])
const loading      = ref(false)
const filterStatus = ref('대기')

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
  } catch (e) {
    if (e.response?.status === 403) requests.value = []
    else requests.value = []
  } finally { loading.value = false }
}

function openApprove(r) {
  approveTarget.value = r
  approveForm.value   = { request_id: r.id, role_granted: '시니어' }
  approveError.value  = ''
  showApproveModal.value = true
}

async function submitApprove() {
  approveError.value  = ''
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
.modal { background:var(--bg2); border-radius:var(--r); padding:20px; width:360px; display:flex; flex-direction:column; gap:12px; }
.modal-hd { font-size:14px; font-weight:700; }
.info-row { display:flex; gap:12px; font-size:12px; }
.info-k { min-width:48px; color:var(--tx3); font-size:10px; font-family:var(--mono); }
.field { display:flex; flex-direction:column; gap:4px; }
.field label { font-size:11px; color:var(--tx2); }
.inp { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; resize:vertical; }
.inp:focus { border-color:var(--ac); }
.err { color:var(--re); font-size:11px; }
.modal-ft { display:flex; justify-content:flex-end; gap:8px; }
</style>
