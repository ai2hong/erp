<template>
  <div class="page">

    <!-- ── 왼쪽 패널: 목록 ── -->
    <div class="left">

      <!-- 툴바 -->
      <div class="toolbar">
        <div class="search-wrap">
          <span class="si-ic">⌕</span>
          <input v-model="q" class="si" placeholder="고객명 · 전화번호 검색" @input="onSearch" />
        </div>
        <button class="btn-new" @click="openNewModal">＋ 신규 접수</button>
      </div>
      <div class="toolbar" style="padding-top:0">
        <div class="search-wrap" style="flex:1">
          <span class="si-ic">⌕</span>
          <input v-model="qProd" class="si" placeholder="기기명으로 검색" />
        </div>
      </div>

      <!-- 상태 탭 -->
      <div class="status-tabs">
        <button v-for="s in statusTabs" :key="s.key"
          class="stab" :class="[{ on: statusFilter === s.key }, `stab-${s.cls}`]"
          @click="statusFilter = s.key">
          {{ s.label }}
          <span class="stab-cnt">{{ s.key ? statusCounts[s.key] || 0 : items.length }}</span>
        </button>
      </div>

      <!-- 목록 -->
      <div class="list">
        <div v-if="loading" class="empty-s">로딩 중…</div>
        <div v-else-if="!filtered.length" class="empty-s">내역이 없습니다</div>
        <div v-else>
          <div v-for="a in filtered" :key="a.id"
            class="row" :class="[`row-${stKey(a.status)}`, { active: selected?.id === a.id }]"
            @click="selectCase(a.id)">
            <div class="row-top">
              <span class="cust-nm">{{ a.customer_name }}</span>
              <span class="status-bd" :class="`sb-${stKey(a.status)}`">{{ a.status }}</span>
            </div>
            <div class="row-mid">
              <span class="row-device-lbl">AS 접수 기기 :</span>
              <span class="row-device-nm">{{ a.product_name || a.serial_number || '기기 미지정' }}</span>
              <template v-if="a.loaner_note">
                <span class="row-loaner-sep"></span>
                <span class="loaner-tag" :class="a.loaner_return_date ? 'loaner-returned' : 'loaner-out'">[대여 기기 : {{ a.loaner_note }}]</span>
                <span v-if="!a.loaner_return_date" class="loaner-unreturned">미회수</span>
              </template>
            </div>
            <div class="row-bot">
              <span class="row-dt">{{ fmtDate(a.created_at) }}</span>
              <span v-if="a.received_by_name" class="row-staff">{{ a.received_by_name }}</span>
            </div>
            <div v-if="a.symptom" class="row-sym">{{ a.symptom }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 오른쪽 패널: 상세 ── -->
    <div class="right">

      <!-- 선택 없음 -->
      <div v-if="!selected" class="no-sel">
        <div class="ns-ic">◫</div>
        <div class="ns-tx">A/S 건을 선택하면 상세 내용이 표시됩니다</div>
      </div>

      <!-- 상세 뷰 -->
      <template v-else>
        <!-- 헤더 -->
        <div class="det-hd">
          <div class="dh-left">
            <div class="dh-name">{{ selected.customer_name }}</div>
            <div class="dh-sub">
              <span class="dh-phone">{{ selected.customer_phone }}</span>
              <span class="dh-dot">·</span>
              <span>{{ selected.product_name || selected.serial_number || '기기 미지정' }}</span>
              <span class="dh-dot">·</span>
              <span class="dh-date">{{ fmtDate(selected.created_at) }}</span>
              <span v-if="selected.received_by_name" class="dh-dot">·</span>
              <span v-if="selected.received_by_name" class="staff-sm">접수 {{ selected.received_by_name }}</span>
            </div>
          </div>
          <span class="status-bd lg" :class="`sb-${stKey(selected.status)}`">{{ selected.status }}</span>
        </div>

        <!-- ── 진행 단계 버튼 ── -->
        <div class="prog-wrap">
          <template v-for="(s, i) in STATUS_ORDER" :key="s">
            <div class="prog-col">
              <!-- 연결선 + 점 -->
              <div class="prog-dot-row">
                <div class="prog-line" :class="{ done: isStepDone(s) || selected.status === s, invisible: i === 0 }"></div>
                <span class="pb-dot" :class="{ done: isStepDone(s), current: selected.status === s }"></span>
                <div class="prog-line" :class="{ done: isStepDone(STATUS_ORDER[i+1]) || selected.status === STATUS_ORDER[i+1], invisible: i === STATUS_ORDER.length - 1 }"></div>
              </div>
              <!-- 클릭 가능한 글자 라벨 -->
              <button class="prog-label"
                :class="{ done: isStepDone(s), current: selected.status === s }"
                @click="onStepClick(s)">
                {{ s }}
              </button>
              <!-- 날짜/담당자 (현재 단계 이하만) -->
              <div v-if="stepInfo(s)" class="prog-info">
                <div class="pi-date">{{ fmtDate(stepInfo(s).created_at) }}</div>
                <div class="pi-time">{{ fmtTime(stepInfo(s).created_at) }}</div>
                <div class="pi-staff">{{ stepInfo(s).staff_name || '' }}</div>
              </div>
            </div>
          </template>
        </div>

        <!-- ── 스크롤 영역 ── -->
        <div class="det-body">

          <!-- 대여 기기 섹션 -->
          <div v-if="selected.loaner_note" class="section loaner-section">
            <div class="sec-title">대여 기기</div>
            <div class="loaner-box" :class="selected.loaner_return_date ? 'lb-returned' : 'lb-out'">
              <div class="lb-info">
                <div class="lb-name">{{ selected.loaner_note }}</div>
                <div class="lb-dates">
                  <span>출고 {{ fmtDateTime(selected.loaner_out_date) }}</span>
                  <span v-if="selected.loaner_return_date" class="lb-ret">· 회수 {{ fmtDateTime(selected.loaner_return_date) }}</span>
                </div>
              </div>
              <div class="lb-status">
                <template v-if="selected.loaner_return_date">
                  <span class="loaner-badge lb-done">회수 완료</span>
                  <button class="loaner-badge lb-btn-cancel" @click="cancelReturnLoaner">회수 취소</button>
                </template>
                <template v-else>
                  <button class="loaner-badge lb-btn" @click="returnLoaner">회수 완료 처리</button>
                  <button class="loaner-badge lb-btn-unreturned" @click="openUnreturnedModal">미반납 처리 요청</button>
                </template>
              </div>
            </div>
          </div>

          <!-- 미반납 처리 요청 모달 -->
          <div v-if="showUnreturnedModal" class="modal-back" @click.self="showUnreturnedModal=false">
            <div class="modal modal-sm">
              <div class="modal-hd">
                <div>
                  <div class="mh-title">대여 기기 미반납 처리 요청</div>
                  <div class="mh-sub">매니저·총괄·사장에게 처리 승인을 요청합니다</div>
                </div>
                <button class="btn-close" @click="showUnreturnedModal=false">✕</button>
              </div>
              <div class="modal-body">
                <div class="lb-info" style="margin-bottom:8px;padding:8px 10px;background:var(--bg3);border-radius:6px;font-size:12px">
                  <div><b>대여 기기 :</b> {{ selected.loaner_note }}</div>
                  <div><b>고객명 :</b> {{ selected.customer_name }}</div>
                </div>
                <div class="fg-row">
                  <label class="fg-lbl">사유 <span style="color:var(--re)">필수</span></label>
                  <textarea v-model="unreturnedReason" class="inp" rows="3" placeholder="미반납 사유를 입력하세요" />
                </div>
              </div>
              <div v-if="unreturnedErr" style="color:var(--re);font-size:11px;padding:0 16px">{{ unreturnedErr }}</div>
              <div class="modal-ft">
                <button class="btn-ghost" @click="showUnreturnedModal=false">취소</button>
                <button class="btn-submit" :disabled="unreturnedLoading" @click="submitUnreturned">
                  {{ unreturnedLoading ? '요청 중…' : '요청 전송' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 처리 내용 폼 -->
          <div class="section">
            <div class="sec-title">처리 내용</div>
            <div class="form-grid">
              <div class="fg-row">
                <label class="fg-lbl">증상</label>
                <textarea v-model="editForm.symptom" class="inp" rows="3" placeholder="고객 호소 증상" />
              </div>
              <div class="form-row-2">
                <div class="fg-row" style="flex:1">
                  <label class="fg-lbl">도매 판정</label>
                  <select v-model="editForm.wholesale_verdict" class="inp">
                    <option value="">— 미정 —</option>
                    <option>A/S 가능</option>
                    <option>A/S 불가능</option>
                  </select>
                </div>
                <div class="fg-row" style="flex:1">
                  <label class="fg-lbl">수리비</label>
                  <input v-model.number="editForm.repair_cost" type="number" class="inp" placeholder="0" min="0" />
                </div>
              </div>
            </div>
            <div class="save-row">
              <span v-if="saveMsg" class="save-msg" :class="{ err: saveErr }">{{ saveMsg }}</span>
              <button class="btn-save" :disabled="saving" @click="submitEdit">
                {{ saving ? '저장 중…' : '내용 저장' }}
              </button>
            </div>
          </div>

          <!-- 처리 이력 (맨 아래) -->
          <div class="section">
            <div class="sec-title">처리 이력</div>
            <div v-if="!detailLogs.length" class="empty-logs">이력이 없습니다</div>
            <div v-else class="log-table">
              <div class="lt-head">
                <span>상태</span>
                <span>일시</span>
                <span>담당자</span>
                <span>메모</span>
              </div>
              <div v-for="lg in detailLogs" :key="lg.id" class="lt-row">
                <span>
                  <span v-if="lg.from_status" class="lt-from">{{ lg.from_status }} →</span>
                  <span class="lt-to" :class="`tc-${stKey(lg.to_status)}`">{{ lg.to_status }}</span>
                </span>
                <span class="lt-dt mono">{{ fmtDateTime(lg.created_at) }}</span>
                <span class="lt-staff">{{ lg.staff_name || '—' }}</span>
                <span class="lt-memo">{{ lg.memo || '' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ── 상태 변경 확인 모달 ── -->
        <div v-if="showStatusModal" class="modal-back" @click.self="showStatusModal=false">
          <div class="modal modal-sm">
            <div class="modal-hd">
              <div>
                <div class="mh-title" :style="isRevert ? 'color:var(--re)' : ''">
                  {{ isRevert ? '단계 되돌리기' : '단계 진행' }}
                </div>
                <div class="mh-sub">
                  <span class="status-bd" :class="`sb-${stKey(selected.status)}`">{{ selected.status }}</span>
                  <span style="margin:0 6px">→</span>
                  <span class="status-bd" :class="`sb-${stKey(statusTarget)}`">{{ statusTarget }}</span>
                </div>
              </div>
              <button class="btn-close" @click="showStatusModal=false">✕</button>
            </div>
            <div class="modal-body">
              <div v-if="isRevert" class="revert-warn">
                ⚠ 이전 단계로 되돌립니다. 처리 이력에 <b>[취소]</b>로 기록됩니다.
              </div>
              <div class="fg-row">
                <label class="fg-lbl">메모 (선택)</label>
                <input v-model="statusMemo" class="inp" :placeholder="isRevert ? '취소 사유 입력…' : '메모 입력…'" />
              </div>
            </div>
            <div class="modal-ft">
              <button class="btn-ghost" @click="showStatusModal=false">닫기</button>
              <button :class="isRevert ? 'btn-danger' : 'btn-submit'" :disabled="statusChanging" @click="confirmStatusChange">
                {{ statusChanging ? '처리 중…' : (isRevert ? '되돌리기' : '진행') }}
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ── 신규 접수 모달 ── -->
    <div v-if="showNewModal" class="modal-back" @click.self="showNewModal=false">
      <div class="modal">
        <div class="modal-hd">
          <div>
            <div class="mh-title">A/S 신규 접수</div>
            <div class="mh-sub">고객 기기 수리·점검 접수</div>
          </div>
          <button class="btn-close" @click="showNewModal=false">✕</button>
        </div>

        <div class="modal-body">
          <!-- 고객 -->
          <div class="form-section">
            <div class="fs-lbl">고객 <span class="req">필수</span></div>
            <div class="sf-wrap">
              <input v-model="nf.customerQ" class="inp" placeholder="고객명 또는 전화번호 검색"
                @input="searchCust" @focus="showCDrop=true" @blur="hideCDrop" />
              <div v-if="showCDrop && custRes.length" class="drop">
                <div v-for="c in custRes" :key="c.id" class="drop-item" @mousedown.prevent="pickCust(c)">
                  <span class="di-nm">{{ c.name }}</span>
                  <span class="di-sub">{{ c.phone }}</span>
                </div>
              </div>
            </div>
            <div v-if="nf.customer" class="sel-ok">✓ {{ nf.customer.name }} · {{ nf.customer.phone }}</div>
            <div v-if="nErr === 'cust'" class="field-err">고객을 선택해주세요</div>
          </div>

          <div class="form-row-2">
            <!-- 기기 -->
            <div class="form-section" style="flex:1">
              <div class="fs-lbl">기기 / 상품명 <span class="req">필수</span></div>
              <div class="sf-wrap">
                <input v-model="nf.productQ" class="inp" :class="{ 'inp-err': nErr==='prod' && !nf.product && !nf.prodManual }"
                  placeholder="기기명 검색…"
                  @input="searchProd" @focus="showPDrop=true" @blur="hidePDrop" />
                <div v-if="showPDrop && prodRes.length" class="drop">
                  <div v-for="p in prodRes" :key="p.id" class="drop-item" @mousedown.prevent="pickProd(p)">
                    <span class="di-nm">{{ p.name }}</span>
                    <span class="di-sub cat-tag">{{ p.category }}</span>
                  </div>
                </div>
              </div>
              <div v-if="nf.product" class="sel-ok">✓ {{ nf.product.name }}</div>
              <div v-else class="manual-row">
                <span class="mr-lbl">직접 입력</span>
                <input v-model="nf.prodManual" class="inp inp-sm"
                  :class="{ 'inp-err': nErr==='prod' && !nf.product && !nf.prodManual }"
                  placeholder="목록에 없는 기기명"
                  @input="nf.product = null; nf.productQ = ''" />
              </div>
              <div v-if="nErr === 'prod' && !nf.product && !nf.prodManual" class="field-err">기기명을 선택하거나 입력해주세요</div>
            </div>

            <!-- 대여기기 -->
            <div class="form-section" style="flex:1">
              <div class="fs-lbl">대여 기기 <span class="opt">선택</span></div>
              <input v-model="nf.loanerNote" class="inp" placeholder="대여한 기기명" />
            </div>
          </div>

          <!-- 증상 -->
          <div class="form-section">
            <div class="fs-lbl">증상</div>
            <textarea v-model="nf.symptom" class="inp" rows="3" placeholder="고객이 호소하는 증상" />
          </div>
        </div>

        <div v-if="newApiErr" class="modal-err">{{ newApiErr }}</div>
        <div class="modal-ft">
          <button class="btn-ghost" @click="showNewModal=false">취소</button>
          <button class="btn-submit" :disabled="newLoading" @click="submitNew">
            {{ newLoading ? '접수 중…' : '접수 등록' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const STATUS_ORDER = ['접수', '발송/처리중', '입고', '연락완료', 'AS완료']

const statusTabs = [
  { key: '',         label: '전체',      cls: 'all' },
  { key: '접수',     label: '접수',      cls: 'ye' },
  { key: '발송/처리중', label: '발송/처리중', cls: 'or' },
  { key: '입고',     label: '입고',      cls: 'pu' },
  { key: '연락완료', label: '연락완료',   cls: 'te' },
  { key: 'AS완료',   label: 'AS완료',    cls: 'gr' },
]

function stKey(s) {
  const m = { '접수':'ye', '발송/처리중':'or', '입고':'pu', '연락완료':'te', 'AS완료':'gr' }
  return m[s] || 'ok'
}

function isStepDone(s) {
  if (!selected.value) return false
  const cur = STATUS_ORDER.indexOf(selected.value.status)
  const tgt = STATUS_ORDER.indexOf(s)
  return tgt < cur
}

// ── 목록 ──────────────────────────────────────────────────────
const items        = ref([])
const loading      = ref(false)
const q            = ref('')
const qProd        = ref('')
const statusFilter = ref('')

const filtered = computed(() => {
  let list = items.value
  if (statusFilter.value) list = list.filter(a => a.status === statusFilter.value)
  if (q.value.trim()) {
    const kw = q.value.trim()
    list = list.filter(a =>
      a.customer_name?.includes(kw) || a.customer_phone?.includes(kw)
    )
  }
  if (qProd.value.trim()) {
    const kw = qProd.value.trim()
    list = list.filter(a =>
      a.product_name?.includes(kw) || a.serial_number?.includes(kw) ||
      a.symptom?.includes(kw)
    )
  }
  return list
})

const statusCounts = computed(() => {
  const cnt = {}
  for (const s of STATUS_ORDER) cnt[s] = items.value.filter(a => a.status === s).length
  return cnt
})

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/as-cases')
    items.value = res.data
  } catch { items.value = [] }
  finally { loading.value = false }
}

onMounted(load)

// ── 상세 ──────────────────────────────────────────────────────
const selected    = ref(null)
const detailLogs  = ref([])
const detailLoading = ref(false)

const editForm = ref({ symptom:'', wholesale_verdict:'', repair_cost:null })
const saving   = ref(false)
const saveMsg  = ref('')
const saveErr  = ref(false)

// 상태 변경 모달
const showStatusModal  = ref(false)
const statusTarget     = ref('')
const isRevert         = ref(false)
const statusMemo       = ref('')
const statusChanging   = ref(false)

function stepInfo(s) {
  // 완료됐거나 현재 단계인 경우만 표시 (되돌린 단계엔 숨김)
  if (!isStepDone(s) && selected.value?.status !== s) return null
  return [...detailLogs.value].reverse().find(lg => lg.to_status === s) || null
}

function onStepClick(s) {
  if (!selected.value || s === selected.value.status) return
  statusTarget.value = s
  isRevert.value = STATUS_ORDER.indexOf(s) < STATUS_ORDER.indexOf(selected.value.status)
  statusMemo.value = ''
  showStatusModal.value = true
}

async function confirmStatusChange() {
  statusChanging.value = true
  try {
    const res = await api.post(`/as-cases/${selected.value.id}/set-status`, {
      to_status: statusTarget.value,
      memo: statusMemo.value || null,
    })
    selected.value   = res.data
    detailLogs.value = res.data.logs || []
    const idx = items.value.findIndex(a => a.id === selected.value.id)
    if (idx !== -1) items.value[idx] = { ...items.value[idx], ...res.data }
    showStatusModal.value = false
  } catch (e) {
    alert(e.response?.data?.detail || '상태 변경 실패')
  }
  finally { statusChanging.value = false }
}

async function selectCase(id) {
  detailLoading.value = true
  try {
    const res = await api.get(`/as-cases/${id}`)
    selected.value   = res.data
    detailLogs.value = res.data.logs || []
    editForm.value = {
      symptom:           res.data.symptom           || '',
      wholesale_verdict: res.data.wholesale_verdict  || '',
      repair_cost:       res.data.repair_cost        ?? null,
    }
    saveMsg.value = ''
    showStatusModal.value = false
  } catch { /* ignore */ }
  finally { detailLoading.value = false }
}

async function returnLoaner() {
  try {
    const res = await api.post(`/as-cases/${selected.value.id}/return-loaner`)
    const idx = items.value.findIndex(a => a.id === selected.value.id)
    if (idx !== -1) items.value[idx] = { ...items.value[idx], ...res.data }
    selected.value = { ...selected.value, ...res.data }
    detailLogs.value = res.data.logs ?? detailLogs.value
  } catch (e) {
    alert(e.response?.data?.detail || '회수 처리 실패')
  }
}

async function cancelReturnLoaner() {
  try {
    const res = await api.post(`/as-cases/${selected.value.id}/cancel-return-loaner`)
    const idx = items.value.findIndex(a => a.id === selected.value.id)
    if (idx !== -1) items.value[idx] = { ...items.value[idx], ...res.data }
    selected.value = { ...selected.value, ...res.data }
    detailLogs.value = res.data.logs ?? detailLogs.value
  } catch (e) {
    alert(e.response?.data?.detail || '회수 취소 실패')
  }
}

const showUnreturnedModal = ref(false)
const unreturnedReason    = ref('')
const unreturnedLoading   = ref(false)
const unreturnedErr       = ref('')

function openUnreturnedModal() {
  unreturnedReason.value = ''
  unreturnedErr.value    = ''
  showUnreturnedModal.value = true
}

async function submitUnreturned() {
  unreturnedErr.value = ''
  if (!unreturnedReason.value.trim()) { unreturnedErr.value = '사유를 입력해주세요'; return }
  unreturnedLoading.value = true
  try {
    await api.post(`/as-cases/${selected.value.id}/unreturned-loaner`, {
      reason: unreturnedReason.value.trim(),
    })
    showUnreturnedModal.value = false
    await selectCase(selected.value.id)
  } catch (e) {
    unreturnedErr.value = e.response?.data?.detail || '요청 실패'
  } finally { unreturnedLoading.value = false }
}

async function submitEdit() {
  saving.value = true
  saveMsg.value = ''
  saveErr.value = false
  try {
    const res = await api.put(`/as-cases/${selected.value.id}`, {
      symptom:           editForm.value.symptom,
      wholesale_verdict: editForm.value.wholesale_verdict || null,
      repair_cost:       editForm.value.repair_cost ?? null,
    })
    // update in list
    const idx = items.value.findIndex(a => a.id === selected.value.id)
    if (idx !== -1) items.value[idx] = { ...items.value[idx], ...res.data }
    selected.value = { ...selected.value, ...res.data }
    saveMsg.value = '저장되었습니다'
    setTimeout(() => { saveMsg.value = '' }, 2000)
  } catch (e) {
    saveErr.value = true
    saveMsg.value = e.response?.data?.detail || '저장 실패'
  }
  finally { saving.value = false }
}


// ── 신규 접수 ─────────────────────────────────────────────────
const showNewModal = ref(false)
const newLoading   = ref(false)
const newApiErr    = ref('')
const nErr         = ref('')   // 'cust' | 'prod' | ''

const nf = ref({ customerQ:'', customer:null, productQ:'', product:null, prodManual:'', loanerNote:'', symptom:'' })
const custRes  = ref([])
const showCDrop = ref(false)
const prodRes  = ref([])
const showPDrop = ref(false)

function openNewModal() {
  nErr.value = ''; newApiErr.value = ''
  nf.value = { customerQ:'', customer:null, productQ:'', product:null, prodManual:'', loanerNote:'', symptom:'' }
  custRes.value = []; prodRes.value = []
  showNewModal.value = true
}

function hideCDrop() { setTimeout(() => { showCDrop.value = false }, 150) }
function hidePDrop() { setTimeout(() => { showPDrop.value = false }, 150) }

let ctimer = null
function searchCust() {
  nf.value.customer = null
  clearTimeout(ctimer)
  if (!nf.value.customerQ.trim()) { custRes.value = []; return }
  ctimer = setTimeout(async () => {
    try {
      const r = await api.get('/customers/search', { params: { q: nf.value.customerQ } })
      custRes.value = r.data.slice(0, 8)
    } catch { custRes.value = [] }
  }, 250)
}
function pickCust(c) {
  nf.value.customer = c
  nf.value.customerQ = `${c.name} (${c.phone})`
  showCDrop.value = false
  if (nErr.value === 'cust') nErr.value = ''
}

let ptimer = null
function searchProd() {
  nf.value.product = null
  clearTimeout(ptimer)
  if (!nf.value.productQ.trim()) { prodRes.value = []; return }
  ptimer = setTimeout(async () => {
    try {
      const r = await api.get('/products/search', { params: { q: nf.value.productQ, device_only: true } })
      prodRes.value = r.data
    } catch { prodRes.value = [] }
  }, 250)
}
function pickProd(p) {
  nf.value.product = p
  nf.value.productQ = p.name
  showPDrop.value = false
  nErr.value = ''
}

async function submitNew() {
  nErr.value = ''; newApiErr.value = ''
  if (!nf.value.customer) { nErr.value = 'cust'; return }
  if (!nf.value.product && !nf.value.prodManual.trim()) { nErr.value = 'prod'; return }
  newLoading.value = true
  try {
    await api.post('/as-cases', {
      customer_id:   nf.value.customer.id,
      product_id:    nf.value.product?.id || undefined,
      serial_number: !nf.value.product ? (nf.value.prodManual.trim() || undefined) : undefined,
      symptom:       nf.value.symptom.trim() || undefined,
      loaner_note:   nf.value.loanerNote.trim() || undefined,
    })
    showNewModal.value = false
    await load()
  } catch (e) {
    const d = e.response?.data?.detail
    newApiErr.value = typeof d === 'string' ? d : `오류 (${e.response?.status ?? 'network'})`
  }
  finally { newLoading.value = false }
}

// ── 유틸 ──────────────────────────────────────────────────────
function fmtDate(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`
}
function fmtTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}
function fmtDateTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${fmtDate(dt)} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}
</script>

<style scoped>
/* ── 레이아웃 ── */
.page { display:grid; grid-template-columns:2fr 3fr; height:100%; overflow:hidden; background:var(--bg); }

/* ── 왼쪽 ── */
.left { display:flex; flex-direction:column; border-right:1px solid var(--bd); overflow:hidden; background:var(--bg2); }

.toolbar {
  display:flex; align-items:center; gap:8px; padding:10px 12px;
  border-bottom:1px solid var(--bd); flex-shrink:0;
}
.search-wrap { position:relative; flex:1; display:flex; align-items:center; }
.si-ic { position:absolute; left:9px; font-size:13px; color:var(--tx3); pointer-events:none; }
.si {
  padding:6px 8px 6px 27px; border:1px solid var(--bd2); border-radius:var(--r);
  background:var(--bg); font-size:12px; color:var(--tx); outline:none; width:100%;
}
.si:focus { border-color:var(--ac); }
.btn-new {
  padding:6px 11px; background:var(--ac); color:#fff; border:none;
  border-radius:var(--r); font-size:11px; font-weight:600; cursor:pointer;
  white-space:nowrap; flex-shrink:0;
}
.btn-new:hover { opacity:.88; }

/* 상태 탭 */
.status-tabs { display:flex; flex-wrap:wrap; gap:3px; padding:8px 12px; border-bottom:1px solid var(--bd); flex-shrink:0; }
.stab {
  padding:3px 8px; border-radius:20px; border:1px solid var(--bd2);
  background:none; cursor:pointer; font-size:10px; color:var(--tx2);
  font-family:var(--mono); display:flex; align-items:center; gap:4px;
  transition:all .1s;
}
.stab:hover { background:var(--bg3); }
.stab.on { color:#fff; border-color:transparent; }
.stab-all.on { background:var(--tx); }
.stab-ye.on  { background:#d4900f; }
.stab-or.on  { background:#c2600a; }
.stab-bl.on  { background:#2f6bbf; }
.stab-pu.on  { background:#6b45c8; }
.stab-te.on  { background:#0e7f6b; }
.stab-gr.on  { background:#1f8a5e; }
.stab-cnt {
  font-size:9px; background:var(--bg3); color:var(--tx3);
  padding:0 4px; border-radius:8px; font-weight:600;
}
.stab.on .stab-cnt { background:rgba(255,255,255,.25); color:#fff; }

/* 리스트 */
.list { flex:1; overflow-y:auto; }
.empty-s { text-align:center; padding:28px; color:var(--tx3); font-size:12px; }

.row {
  padding:10px 14px; border-bottom:1px solid var(--bd);
  cursor:pointer; transition:background .1s;
  border-left:3px solid transparent;
}
.row:hover { background:var(--bg3); }
.row.active { background:#fff8f4; border-left-color:var(--ac); }

.row-top  { display:flex; align-items:center; justify-content:space-between; margin-bottom:3px; }
.cust-nm  { font-size:13px; font-weight:700; color:var(--tx); }
.row-mid  { font-size:11px; color:var(--tx2); margin-bottom:2px; display:flex; align-items:center; gap:4px; }
.row-device-lbl { font-size:10px; color:var(--tx3); flex-shrink:0; }
.row-device-nm  { font-weight:700; color:var(--tx); font-size:12px; }
.row-loaner-sep { flex-shrink:0; width:20px; }
.loaner-tag { font-size:10px; }
.loaner-out { color:#b45309; }
.loaner-returned { color:var(--tx3); text-decoration:line-through; }
.loaner-unreturned { font-size:9px; background:#fef3c7; color:#b45310; border-radius:8px; padding:1px 5px; font-family:var(--mono); font-weight:600; }
.row-bot  { display:flex; align-items:center; gap:6px; }
.row-dt   { font-size:10px; color:var(--tx3); font-family:var(--mono); }
.row-staff { font-size:10px; color:var(--tx3); background:var(--bg3); padding:1px 5px; border-radius:8px; }
.row-sym  { font-size:10px; color:var(--tx3); margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* ── 대여 기기 섹션 ────────────────────────────────────────── */
.loaner-section { }
.loaner-box { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 14px; border-radius:8px; border:1px solid; }
.lb-out { background:#fffbeb; border-color:#fcd34d; }
.lb-returned { background:var(--bg3); border-color:var(--bd); }
.lb-info { display:flex; flex-direction:column; gap:4px; }
.lb-name { font-size:13px; font-weight:700; color:var(--tx); }
.lb-dates { font-size:10px; color:var(--tx3); font-family:var(--mono); }
.lb-ret { color:var(--gr); }
.loaner-badge { display:inline-flex; align-items:center; padding:5px 12px; border-radius:6px; font-size:11px; font-weight:600; white-space:nowrap; }
.lb-done { background:#dcfce7; color:#16a34a; border:none; }
.lb-btn { background:var(--ac); color:#fff; border:none; cursor:pointer; }
.lb-btn:hover { opacity:.85; }
.lb-btn-cancel { background:var(--bg3); color:var(--tx2); border:1px solid var(--bd2); cursor:pointer; }
.lb-btn-cancel:hover { background:var(--bd2); }
.lb-btn-unreturned { background:#f97316; color:#fff; border:none; cursor:pointer; }
.lb-btn-unreturned:hover { opacity:.85; }
.lb-status { display:flex; gap:6px; flex-wrap:wrap; }

/* 행 왼쪽 색상 */
.row-ye { border-left-color:#e8a800; }
.row-or { border-left-color:#e06a10; }
.row-bl { border-left-color:#4f86f7; }
.row-pu { border-left-color:#8b72d8; }
.row-te { border-left-color:#18a096; }
.row-gr { border-left-color:#34a87a; }

/* ── 오른쪽 ── */
.right { display:flex; flex-direction:column; overflow:hidden; }

.no-sel {
  flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;
  color:var(--tx3); gap:10px;
}
.ns-ic { font-size:32px; }
.ns-tx { font-size:13px; }

/* 헤더 */
.det-hd {
  display:flex; align-items:flex-start; justify-content:space-between;
  padding:16px 20px; border-bottom:1px solid var(--bd); flex-shrink:0;
  background:var(--bg2);
}
.dh-left   { display:flex; flex-direction:column; gap:4px; }
.dh-name   { font-size:16px; font-weight:700; color:var(--tx); }
.dh-sub    { display:flex; align-items:center; gap:5px; font-size:11px; color:var(--tx2); flex-wrap:wrap; }
.dh-phone  { font-family:var(--mono); }
.dh-dot    { color:var(--tx3); }
.dh-date   { font-family:var(--mono); color:var(--tx3); }
.staff-sm  { font-size:10px; background:var(--bg3); padding:1px 7px; border-radius:20px; }

/* ── 진행 단계 버튼 ── */
.prog-wrap {
  display:flex; align-items:flex-start;
  padding:14px 20px 12px;
  border-bottom:1px solid var(--bd); flex-shrink:0; background:var(--bg2);
  overflow-x:auto;
}
.prog-col {
  display:flex; flex-direction:column; align-items:center;
  flex:1; min-width:72px;
}
/* 점 + 선 행 — 양쪽 선 항상 렌더, 엣지는 invisible */
.prog-dot-row {
  display:flex; align-items:center; width:100%;
}
.prog-line {
  flex:1; height:2px; background:var(--bd2); transition:background .25s;
}
.prog-line.done      { background:var(--gr); }
.prog-line.invisible { background:transparent !important; }

.pb-dot {
  display:block; width:11px; height:11px; border-radius:50%; flex-shrink:0;
  background:var(--bd2); border:2px solid var(--bd2);
  transition:all .15s;
}
.pb-dot.done    { background:var(--gr); border-color:var(--gr); }
.pb-dot.current { background:var(--ac); border-color:var(--ac);
  transform:scale(1.3); box-shadow:0 0 0 3px rgba(244,132,95,.18); }

/* 글자 버튼 */
.prog-label {
  background:none; border:none; cursor:pointer; padding:4px 6px;
  font-size:10px; color:var(--tx3); font-family:var(--mono);
  text-align:center; white-space:nowrap; border-radius:4px;
  transition:all .12s; margin-top:4px;
}
.prog-label:hover  { background:var(--bg3); color:var(--tx); }
.prog-label.done   { color:var(--gr); font-weight:600; }
.prog-label.current { color:var(--ac); font-weight:700; }
.prog-label.current:hover { background:rgba(244,132,95,.1); }

.prog-info { display:flex; flex-direction:column; align-items:center; gap:1px; }
.pi-date  { font-size:9px; color:var(--tx3); font-family:var(--mono); }
.pi-time  { font-size:9px; color:var(--tx3); font-family:var(--mono); }
.pi-staff { font-size:9px; color:var(--tx2); font-weight:600; }

/* 상세 스크롤 */
.det-body { flex:1; overflow-y:auto; padding:16px 20px; display:flex; flex-direction:column; gap:20px; }

.section {}
.sec-title { font-size:11px; font-weight:700; color:var(--tx3); text-transform:uppercase;
  letter-spacing:.6px; font-family:var(--mono); margin-bottom:10px; }

/* 폼 */
.form-grid  { display:flex; flex-direction:column; gap:10px; }
.fg-row     { display:flex; flex-direction:column; gap:4px; }
.fg-lbl     { font-size:10px; font-weight:600; color:var(--tx2); }
.form-row-2 { display:flex; gap:12px; }

.inp {
  padding:8px 10px; border:1px solid var(--bd2); border-radius:var(--r);
  background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx);
  outline:none; resize:vertical; width:100%; box-sizing:border-box;
}
.inp:focus { border-color:var(--ac); }
.inp:disabled { opacity:.5; background:var(--bg3); }
.inp.inp-err { border-color:var(--re); }

.save-row { display:flex; align-items:center; justify-content:flex-end; gap:10px; margin-top:4px; }
.save-msg { font-size:11px; color:var(--gr); }
.save-msg.err { color:var(--re); }
.btn-save {
  padding:6px 14px; background:var(--bg2); border:1px solid var(--bd2);
  border-radius:var(--r); font-size:11px; cursor:pointer; color:var(--tx2);
}
.btn-save:hover { background:var(--bg3); }
.btn-save:disabled { opacity:.5; cursor:not-allowed; }

/* tc-* 색상 (처리이력 상태색) */
.tc-ye { color:#c27800; }
.tc-or { color:#c2600a; }
.tc-bl { color:#2f6bbf; }
.tc-pu { color:#6b45c8; }
.tc-te { color:#0e7f6b; }
.tc-gr { color:#1f8a5e; }

/* ── 처리이력 테이블 ── */
.log-table { width:100%; }
.lt-head {
  display:grid; grid-template-columns:160px 140px 80px 1fr;
  padding:5px 8px; background:var(--bg3); border-radius:var(--r);
  font-size:10px; font-weight:600; color:var(--tx3); font-family:var(--mono);
  margin-bottom:4px;
}
.lt-row {
  display:grid; grid-template-columns:160px 140px 80px 1fr;
  padding:7px 8px; border-bottom:1px solid var(--bd);
  font-size:11px; color:var(--tx2); align-items:center;
}
.lt-row:last-child { border-bottom:none; }
.lt-from  { color:var(--tx3); font-size:10px; }
.lt-to    { font-weight:700; }
.lt-dt    { font-size:10px; }
.lt-staff { }
.lt-memo  { color:var(--tx3); }
.empty-logs { font-size:12px; color:var(--tx3); padding:4px 0; }

/* ── 상태변경 모달 ── */
.revert-warn {
  padding:10px 12px; background:#fef5f5; border:1px solid #fbd8d8;
  border-radius:6px; font-size:11px; color:var(--re); margin-bottom:12px;
}
.modal-sm { width:420px; }
.btn-danger {
  padding:7px 20px; border:none; border-radius:var(--r);
  background:var(--re); color:#fff; font-size:12px; font-weight:600;
  cursor:pointer; font-family:var(--sans);
}
.btn-danger:hover { opacity:.88; }
.btn-danger:disabled { opacity:.5; cursor:not-allowed; }

/* 상태 뱃지 */
.status-bd {
  display:inline-flex; padding:2px 8px; border-radius:20px;
  font-size:10px; font-weight:700; letter-spacing:.3px;
}
.status-bd.lg { font-size:12px; padding:4px 12px; }
.sb-ye { background:#fef3d4; color:#9a6c1a; }
.sb-or { background:#fde8d0; color:#a04010; }
.sb-bl { background:#ddeeff; color:#2f6bbf; }
.sb-pu { background:#ede9fc; color:#6b45c8; }
.sb-te { background:#d4f5f1; color:#0e7f6b; }
.sb-gr { background:#d4f0e3; color:#1f8a5e; }
.sb-ok { background:#f1f0ec; color:#6b6b67; }

/* ── 신규 접수 모달 ── */
.modal-back {
  position:fixed; inset:0; background:rgba(0,0,0,.5);
  display:flex; align-items:center; justify-content:center; z-index:200;
}
.modal {
  background:var(--bg2); border-radius:12px; width:560px;
  display:flex; flex-direction:column; max-height:90vh; overflow:hidden;
  box-shadow:0 24px 64px rgba(0,0,0,.28);
}
.modal-hd {
  display:flex; align-items:flex-start; justify-content:space-between;
  padding:20px 22px 16px; border-bottom:1px solid var(--bd); flex-shrink:0;
}
.mh-title { font-size:15px; font-weight:700; }
.mh-sub   { font-size:11px; color:var(--tx2); margin-top:3px; }
.btn-close {
  border:none; background:none; cursor:pointer; color:var(--tx3);
  font-size:14px; padding:4px; border-radius:4px;
}
.btn-close:hover { background:var(--bg3); color:var(--tx); }

.modal-body { padding:18px 22px; display:flex; flex-direction:column; gap:14px; overflow-y:auto; }
.form-section { display:flex; flex-direction:column; gap:5px; }
.form-row-2   { display:flex; gap:12px; }
.fs-lbl { font-size:11px; font-weight:600; color:var(--tx2); display:flex; align-items:center; gap:5px; }
.req    { font-size:9px; background:#fde8e8; color:#c44b4b; padding:1px 5px; border-radius:4px; font-weight:700; }
.opt    { font-size:9px; background:var(--bg3); color:var(--tx3); padding:1px 5px; border-radius:4px; }

.sf-wrap  { position:relative; }
.drop {
  position:absolute; top:calc(100% + 3px); left:0; right:0;
  background:var(--bg2); border:1px solid var(--bd2); border-radius:var(--r);
  box-shadow:0 10px 28px rgba(0,0,0,.13); z-index:20; max-height:180px; overflow-y:auto;
}
.drop-item { display:flex; align-items:center; justify-content:space-between; padding:8px 12px; cursor:pointer; font-size:12px; }
.drop-item:hover { background:var(--bg3); }
.di-nm  { font-weight:600; color:var(--tx); }
.di-sub { font-size:10px; color:var(--tx3); font-family:var(--mono); }
.cat-tag { background:var(--bg3); padding:1px 5px; border-radius:4px; }

.sel-ok { font-size:11px; color:var(--gr); background:#f0faf5; padding:5px 10px; border-radius:6px; }
.manual-row { display:flex; align-items:center; gap:8px; }
.mr-lbl { font-size:10px; color:var(--tx3); white-space:nowrap; }
.inp-sm { flex:1; padding:6px 9px; }
.field-err { font-size:10px; color:var(--re); }

.modal-err {
  margin:0 22px 4px; padding:8px 12px; background:#fef5f5;
  border-radius:6px; font-size:11px; color:var(--re); border:1px solid #fbd8d8;
}
.modal-ft {
  display:flex; justify-content:flex-end; gap:8px;
  padding:14px 22px; border-top:1px solid var(--bd); flex-shrink:0;
}
.btn-ghost {
  padding:7px 16px; border:1px solid var(--bd2); border-radius:var(--r);
  background:none; cursor:pointer; font-size:12px; color:var(--tx2); font-family:var(--sans);
}
.btn-ghost:hover { background:var(--bg3); }
.btn-submit {
  padding:7px 20px; border:none; border-radius:var(--r);
  background:var(--ac); color:#fff; font-size:12px; font-weight:600;
  cursor:pointer; font-family:var(--sans);
}
.btn-submit:hover { opacity:.88; }
.btn-submit:disabled { opacity:.5; cursor:not-allowed; }
</style>
