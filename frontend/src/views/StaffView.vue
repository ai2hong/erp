<template>
  <div class="page">

    <div class="toolbar">
      <div class="tab-group">
        <button class="tab" :class="{ on: tab === 'members' }" @click="tab = 'members'; loadMembers()">
          직원 목록
          <span v-if="members.length" class="tab-cnt">{{ members.length }}</span>
        </button>
        <button class="tab" :class="{ on: tab === 'pending' }" @click="tab = 'pending'; loadPending()">
          가입 대기
          <span v-if="pending.length" class="tab-cnt">{{ pending.length }}</span>
        </button>
        <button class="tab" :class="{ on: tab === 'all' }" @click="tab = 'all'; loadAll()">
          전체 신청
        </button>
        <button class="tab" :class="{ on: tab === 'register' }" @click="tab = 'register'">
          신규 가입 신청
        </button>
      </div>
      <button class="btn sm" @click="refresh" style="margin-left:auto">새로고침</button>
    </div>

    <!-- ── 직원 목록 탭 ── -->
    <div v-if="tab === 'members'">
      <div class="card">
        <table class="tw">
          <thead>
            <tr>
              <th>이름</th>
              <th>아이디</th>
              <th>역할</th>
              <th>매장</th>
              <th style="text-align:right">관리</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="5" class="empty">로딩 중…</td></tr>
            <tr v-else-if="!members.length"><td colspan="5" class="empty">직원이 없습니다</td></tr>
            <tr v-for="m in members" :key="m.id">
              <td><span class="staff-name">{{ m.name }}</span></td>
              <td class="mono">{{ m.login_id }}</td>
              <td>
                <span class="role-badge" :class="`rb-${roleKey(m.role)}`">{{ m.role }}</span>
              </td>
              <td style="font-size:11px;color:var(--tx2)">{{ m.store_name || `#${m.store_id}` }}</td>
              <td>
                <div class="actions" style="justify-content:flex-end">
                  <button class="btn xs" @click="openEdit(m)">수정</button>
                  <button class="btn xs bl" @click="openPw(m)">비번 재설정</button>
                  <button class="btn xs re" @click="openDel(m)">삭제</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── 가입 대기 탭 ── -->
    <div v-if="tab === 'pending'">
      <div class="card">
        <table class="tw">
          <thead>
            <tr><th>이름</th><th>아이디</th><th>매장</th><th>메모</th><th>신청일</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6" class="empty">로딩 중…</td></tr>
            <tr v-else-if="!pending.length"><td colspan="6" class="empty">대기 중인 신청이 없습니다</td></tr>
            <tr v-for="r in pending" :key="r.id">
              <td>{{ r.name }}</td>
              <td class="mono">{{ r.login_id }}</td>
              <td>{{ r.store_name || `#${r.store_id}` }}</td>
              <td style="font-size:11px;color:var(--tx3);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ r.memo || '—' }}</td>
              <td class="mono" style="font-size:10px">{{ fmtDt(r.created_at) }}</td>
              <td>
                <div class="actions">
                  <button class="btn xs gr" @click="openApprove(r)">승인</button>
                  <button class="btn xs re" @click="openReject(r)">반려</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── 전체 신청 탭 ── -->
    <div v-if="tab === 'all'">
      <div class="toolbar" style="margin-top:0;margin-bottom:10px">
        <select v-model="filterStatus" class="sel" @change="loadAll">
          <option value="">전체</option>
          <option value="대기">대기</option>
          <option value="승인">승인</option>
          <option value="반려">반려</option>
        </select>
      </div>
      <div class="card">
        <table class="tw">
          <thead>
            <tr><th>이름</th><th>아이디</th><th>매장</th><th>신청일</th><th>상태</th><th>검토자</th></tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6" class="empty">로딩 중…</td></tr>
            <tr v-else-if="!allRequests.length"><td colspan="6" class="empty">내역이 없습니다</td></tr>
            <tr v-for="r in allRequests" :key="r.id">
              <td>{{ r.name }}</td>
              <td class="mono">{{ r.login_id }}</td>
              <td>{{ r.store_name || `#${r.store_id}` }}</td>
              <td class="mono" style="font-size:10px">{{ fmtDt(r.created_at) }}</td>
              <td>
                <span class="tag" :class="{ 'tag-ye': r.status==='대기', 'tag-gr': r.status==='승인', 'tag-re': r.status==='반려' }">
                  {{ r.status }}
                </span>
              </td>
              <td style="font-size:11px;color:var(--tx3)">{{ r.reviewed_by || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── 신규 가입 신청 탭 ── -->
    <div v-if="tab === 'register'" class="reg-form-wrap">
      <div class="card reg-form">
        <div class="reg-hd">신규 직원 가입 신청</div>
        <div class="field">
          <label>이름</label>
          <input v-model="regForm.name" class="inp" placeholder="홍길동" />
        </div>
        <div class="field">
          <label>아이디</label>
          <input v-model="regForm.login_id" class="inp" placeholder="영문·숫자·밑줄, 4자 이상" />
        </div>
        <div class="field">
          <label>비밀번호</label>
          <input v-model="regForm.password" type="password" class="inp" placeholder="비밀번호 입력" />
        </div>
        <div class="field">
          <label>매장</label>
          <select v-model.number="regForm.store_id" class="inp">
            <option value="">선택…</option>
            <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>메모 (선택)</label>
          <input v-model="regForm.memo" class="inp" placeholder="관리자에게 전달할 메모" />
        </div>
        <div v-if="regError" class="err">{{ regError }}</div>
        <div v-if="regSuccess" class="suc">{{ regSuccess }}</div>
        <button class="btn pr" :disabled="regLoading" @click="submitRegister">
          {{ regLoading ? '신청 중…' : '가입 신청' }}
        </button>
      </div>
    </div>

    <!-- ── 수정 모달 ── -->
    <div v-if="showEditModal" class="modal-backdrop" @click.self="showEditModal=false">
      <div class="modal">
        <div class="modal-hd">직원 정보 수정 — {{ editTarget?.name }}</div>
        <div class="field">
          <label>이름</label>
          <input v-model="editForm.name" class="inp" />
        </div>
        <div class="field">
          <label>역할</label>
          <select v-model="editForm.role" class="inp">
            <option value="매니저">매니저</option>
            <option value="시니어">시니어</option>
            <option value="총괄">총괄</option>
            <option value="사장">사장</option>
          </select>
        </div>
        <div class="field">
          <label>매장</label>
          <select v-model.number="editForm.store_id" class="inp">
            <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div v-if="editErr" class="err">{{ editErr }}</div>
        <div v-if="editOk" class="suc">{{ editOk }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showEditModal=false">닫기</button>
          <button class="btn pr" :disabled="actionLoading" @click="submitEdit">저장</button>
        </div>
      </div>
    </div>

    <!-- ── 비번 재설정 모달 ── -->
    <div v-if="showPwModal" class="modal-backdrop" @click.self="showPwModal=false">
      <div class="modal">
        <div class="modal-hd">비밀번호 재설정 — {{ pwTarget?.name }}</div>
        <div class="field">
          <label>새 비밀번호</label>
          <input v-model="newPw" type="password" class="inp" placeholder="새 비밀번호 입력" />
        </div>
        <div class="field">
          <label>비밀번호 확인</label>
          <input v-model="newPwConfirm" type="password" class="inp" placeholder="다시 입력" />
        </div>
        <div v-if="pwErr" class="err">{{ pwErr }}</div>
        <div v-if="pwOk" class="suc">{{ pwOk }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showPwModal=false">닫기</button>
          <button class="btn pr" :disabled="actionLoading" @click="submitPw">재설정</button>
        </div>
      </div>
    </div>

    <!-- ── 삭제 확인 모달 ── -->
    <div v-if="showDelModal" class="modal-backdrop" @click.self="showDelModal=false">
      <div class="modal">
        <div class="modal-hd">직원 삭제</div>
        <div class="del-warn">
          <div class="dw-icon">⚠</div>
          <div>
            <div class="dw-name">{{ delTarget?.name }}</div>
            <div class="dw-sub">{{ delTarget?.login_id }} · {{ delTarget?.role }}</div>
            <div class="dw-msg">계정을 비활성화합니다. 거래 내역 등 기존 데이터는 보존됩니다.</div>
          </div>
        </div>
        <div v-if="delErr" class="err">{{ delErr }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showDelModal=false">취소</button>
          <button class="btn re" :disabled="actionLoading" @click="submitDel">삭제 확인</button>
        </div>
      </div>
    </div>

    <!-- ── 승인 모달 ── -->
    <div v-if="showApproveModal" class="modal-backdrop" @click.self="showApproveModal=false">
      <div class="modal">
        <div class="modal-hd">가입 승인 — {{ approveTarget?.name }}</div>
        <div class="field">
          <label>부여 역할</label>
          <select v-model="approveRole" class="inp">
            <option value="매니저">매니저</option>
            <option value="시니어">시니어</option>
            <option value="총괄">총괄</option>
            <option value="사장">사장</option>
          </select>
        </div>
        <div v-if="approveError" class="err">{{ approveError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showApproveModal=false">취소</button>
          <button class="btn pr" :disabled="actionLoading" @click="submitApprove">승인 확정</button>
        </div>
      </div>
    </div>

    <!-- ── 반려 모달 ── -->
    <div v-if="showRejectModal" class="modal-backdrop" @click.self="showRejectModal=false">
      <div class="modal">
        <div class="modal-hd">가입 반려 — {{ rejectTarget?.name }}</div>
        <div class="field">
          <label>반려 사유</label>
          <textarea v-model="rejectReason" class="inp" rows="3" />
        </div>
        <div v-if="rejectError" class="err">{{ rejectError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showRejectModal=false">취소</button>
          <button class="btn re" :disabled="actionLoading" @click="submitReject">반려</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const tab          = ref('members')
const members      = ref([])
const pending      = ref([])
const allRequests  = ref([])
const stores       = ref([])
const loading      = ref(false)
const filterStatus = ref('')
const actionLoading = ref(false)

// ── 직원 목록 ─────────────────────────────────────────────────
async function loadMembers() {
  loading.value = true
  try {
    const res = await api.get('/auth/admin/staff')
    members.value = res.data
  } catch { members.value = [] }
  finally { loading.value = false }
}

// ── 수정 ──────────────────────────────────────────────────────
const showEditModal = ref(false)
const editTarget    = ref(null)
const editForm      = ref({ name: '', role: '', store_id: null })
const editErr       = ref('')
const editOk        = ref('')

function openEdit(m) {
  editTarget.value = m
  editForm.value   = { name: m.name, role: m.role, store_id: m.store_id }
  editErr.value = ''; editOk.value = ''
  showEditModal.value = true
}

async function submitEdit() {
  editErr.value = ''; editOk.value = ''
  if (!editForm.value.name.trim()) { editErr.value = '이름을 입력하세요'; return }
  actionLoading.value = true
  try {
    const res = await api.put(`/auth/admin/staff/${editTarget.value.id}`, editForm.value)
    editOk.value = '저장되었습니다'
    const idx = members.value.findIndex(m => m.id === editTarget.value.id)
    if (idx !== -1) members.value[idx] = { ...members.value[idx], ...res.data }
    editTarget.value = { ...editTarget.value, ...res.data }
  } catch (e) {
    editErr.value = e.response?.data?.detail || '저장 실패'
  } finally { actionLoading.value = false }
}

// ── 비번 재설정 ────────────────────────────────────────────────
const showPwModal  = ref(false)
const pwTarget     = ref(null)
const newPw        = ref('')
const newPwConfirm = ref('')
const pwErr        = ref('')
const pwOk         = ref('')

function openPw(m) {
  pwTarget.value = m
  newPw.value = ''; newPwConfirm.value = ''
  pwErr.value = ''; pwOk.value = ''
  showPwModal.value = true
}

async function submitPw() {
  pwErr.value = ''; pwOk.value = ''
  if (!newPw.value.trim()) { pwErr.value = '새 비밀번호를 입력하세요'; return }
  if (newPw.value !== newPwConfirm.value) { pwErr.value = '비밀번호가 일치하지 않습니다'; return }
  actionLoading.value = true
  try {
    await api.post('/auth/admin/reset-password', { staff_id: pwTarget.value.id, new_password: newPw.value })
    pwOk.value = '비밀번호가 재설정되었습니다'
    newPw.value = ''; newPwConfirm.value = ''
  } catch (e) {
    pwErr.value = e.response?.data?.detail || '재설정 실패'
  } finally { actionLoading.value = false }
}

// ── 삭제 ──────────────────────────────────────────────────────
const showDelModal = ref(false)
const delTarget    = ref(null)
const delErr       = ref('')

function openDel(m) {
  delTarget.value = m
  delErr.value = ''
  showDelModal.value = true
}

async function submitDel() {
  delErr.value = ''
  actionLoading.value = true
  try {
    await api.delete(`/auth/admin/staff/${delTarget.value.id}`)
    members.value = members.value.filter(m => m.id !== delTarget.value.id)
    showDelModal.value = false
  } catch (e) {
    delErr.value = e.response?.data?.detail || '삭제 실패'
  } finally { actionLoading.value = false }
}

// ── 가입 대기 ─────────────────────────────────────────────────
const showApproveModal = ref(false)
const approveTarget    = ref(null)
const approveRole      = ref('시니어')
const approveError     = ref('')

const showRejectModal = ref(false)
const rejectTarget    = ref(null)
const rejectReason    = ref('')
const rejectError     = ref('')

async function loadPending() {
  loading.value = true
  try {
    const res = await api.get('/auth/admin/requests', { params: { status: '대기' } })
    pending.value = res.data
  } catch { pending.value = [] }
  finally { loading.value = false }
}

async function loadAll() {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    const res = await api.get('/auth/admin/requests', { params })
    allRequests.value = res.data
  } catch { allRequests.value = [] }
  finally { loading.value = false }
}

async function loadStores() {
  try {
    const res = await api.get('/auth/stores')
    stores.value = res.data
  } catch { stores.value = [] }
}

function refresh() {
  if (tab.value === 'members') loadMembers()
  else if (tab.value === 'pending') loadPending()
  else if (tab.value === 'all') loadAll()
}

function openApprove(r) {
  approveTarget.value = r; approveRole.value = '시니어'; approveError.value = ''
  showApproveModal.value = true
}

async function submitApprove() {
  approveError.value = ''; actionLoading.value = true
  try {
    await api.post('/auth/admin/approve', { request_id: approveTarget.value.id, role_granted: approveRole.value })
    showApproveModal.value = false
    await loadPending()
  } catch (e) {
    approveError.value = e.response?.data?.detail || '처리 실패'
  } finally { actionLoading.value = false }
}

function openReject(r) {
  rejectTarget.value = r; rejectReason.value = ''; rejectError.value = ''
  showRejectModal.value = true
}

async function submitReject() {
  rejectError.value = ''
  if (!rejectReason.value.trim()) { rejectError.value = '반려 사유를 입력하세요'; return }
  actionLoading.value = true
  try {
    await api.post('/auth/admin/reject', { request_id: rejectTarget.value.id, reason: rejectReason.value })
    showRejectModal.value = false
    await loadPending()
  } catch (e) {
    rejectError.value = e.response?.data?.detail || '처리 실패'
  } finally { actionLoading.value = false }
}

// ── 신규 가입 신청 ─────────────────────────────────────────────
const regForm    = ref({ name: '', login_id: '', password: '', store_id: '', memo: '' })
const regLoading = ref(false)
const regError   = ref('')
const regSuccess = ref('')

async function submitRegister() {
  regError.value = ''; regSuccess.value = ''
  if (!regForm.value.name || !regForm.value.login_id || !regForm.value.password || !regForm.value.store_id) {
    regError.value = '필수 항목을 모두 입력하세요'; return
  }
  regLoading.value = true
  try {
    await api.post('/auth/register', regForm.value)
    regSuccess.value = '가입 신청이 완료됐습니다. 관리자 승인 후 로그인할 수 있습니다.'
    regForm.value = { name: '', login_id: '', password: '', store_id: '', memo: '' }
  } catch (e) {
    regError.value = e.response?.data?.detail || '신청 실패'
  } finally { regLoading.value = false }
}

// ── 유틸 ──────────────────────────────────────────────────────
function roleKey(r) {
  const m = { '매니저':'mg','시니어':'sr','총괄':'gm','사장':'ow','관리자':'ad' }
  return m[r] || 'mg'
}

function fmtDt(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

onMounted(() => { loadMembers(); loadStores() })
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; }
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:12px; flex-wrap:wrap; }
.tab-group { display:flex; gap:2px; background:var(--bg3); border:1px solid var(--bd); border-radius:var(--r); padding:3px; }
.tab { padding:5px 12px; border-radius:6px; border:none; background:transparent; cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); display:flex; align-items:center; gap:6px; }
.tab.on { background:var(--bg2); color:var(--tx); font-weight:600; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.tab-cnt { background:var(--ac); color:#fff; font-size:10px; padding:0 5px; border-radius:20px; font-family:var(--mono); font-weight:600; }
.sel { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:12px; color:var(--tx); outline:none; cursor:pointer; }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:8px 14px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:10px 14px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.mono { font-family:var(--mono); }

.staff-name { font-weight:600; font-size:13px; }

/* 역할 배지 */
.role-badge { display:inline-flex; padding:2px 8px; border-radius:20px; font-size:10px; font-weight:700; font-family:var(--mono); }
.rb-mg { background:#f1f0ec; color:#6b6b67; }
.rb-sr { background:#ddeeff; color:#2f6bbf; }
.rb-gm { background:#ede9fc; color:#6b45c8; }
.rb-ow { background:#fde8d0; color:#a04010; }
.rb-ad { background:#fde8e8; color:#c44b4b; }

.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-re { background:#fee2e2; color:#dc2626; }

.actions { display:flex; gap:4px; }
.empty { text-align:center; color:var(--tx3); padding:24px; font-size:12px; }

/* 신규 가입 폼 */
.reg-form-wrap { display:flex; justify-content:center; padding-top:20px; }
.reg-form { width:400px; padding:20px; display:flex; flex-direction:column; gap:12px; }
.reg-hd { font-size:14px; font-weight:700; }
.field { display:flex; flex-direction:column; gap:4px; }
.field label { font-size:11px; color:var(--tx2); font-weight:500; }
.inp { padding:8px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; resize:vertical; width:100%; box-sizing:border-box; }
.inp:focus { border-color:var(--ac); }
.err { color:var(--re); font-size:11px; }
.suc { color:var(--gr); font-size:11px; }

/* 버튼 */
.btn { display:inline-flex; align-items:center; justify-content:center; padding:7px 14px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); transition:all .1s; }
.btn:hover { background:var(--bg3); }
.btn:disabled { opacity:.5; cursor:not-allowed; }
.btn.pr { background:var(--ac); color:#fff; border-color:var(--ac); }
.btn.re { background:var(--re); color:#fff; border-color:var(--re); }
.btn.bl { background:#4f86f7; color:#fff; border-color:#4f86f7; }
.btn.gr { background:var(--gr); color:#fff; border-color:var(--gr); }
.btn.sm { padding:4px 10px; font-size:11px; }
.btn.xs { padding:3px 9px; font-size:10px; font-weight:500; }

/* 모달 */
.modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { background:var(--bg2); border-radius:10px; padding:22px; width:380px; display:flex; flex-direction:column; gap:14px; box-shadow:0 20px 60px rgba(0,0,0,.25); }
.modal-hd { font-size:14px; font-weight:700; color:var(--tx); }
.modal-ft { display:flex; justify-content:flex-end; gap:8px; margin-top:4px; }

/* 삭제 경고 */
.del-warn { display:flex; gap:14px; align-items:flex-start; padding:12px 14px; background:#fef5f5; border:1px solid #fbd8d8; border-radius:8px; }
.dw-icon { font-size:22px; flex-shrink:0; margin-top:1px; }
.dw-name { font-size:14px; font-weight:700; color:var(--tx); }
.dw-sub  { font-size:11px; color:var(--tx3); font-family:var(--mono); margin-top:2px; }
.dw-msg  { font-size:11px; color:var(--re); margin-top:6px; }
</style>
