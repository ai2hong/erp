<template>
  <div class="page">

    <!-- ── 툴바 ── -->
    <div class="toolbar">
      <div class="tb-left">
        <div class="search-wrap">
          <span class="si-ic">⌕</span>
          <input v-model="q" class="si" placeholder="고객명 · 전화번호 · 기기명 검색" @input="onSearch" />
        </div>
        <div class="sf-group">
          <button v-for="s in statusList" :key="s.key"
            class="sf-btn" :class="[{ on: statusFilter === s.key }, s.cls]"
            @click="setStatus(s.key)">
            {{ s.label }}
            <span class="sf-cnt">{{ s.key ? statusCounts[s.key] : items.length }}</span>
          </button>
        </div>
      </div>
      <button class="btn-new" @click="openNewModal">
        <span>＋</span> 신규 접수
      </button>
    </div>

    <!-- ── 목록 ── -->
    <div class="list-wrap">
      <!-- 로딩 -->
      <div v-if="loading" class="empty-state">
        <div class="es-icon">⟳</div>
        <div class="es-text">불러오는 중…</div>
      </div>
      <!-- 빈 목록 -->
      <div v-else-if="!filtered.length" class="empty-state">
        <div class="es-icon">◎</div>
        <div class="es-text">{{ statusFilter ? `'${statusFilter}' 상태의 A/S 내역이 없습니다` : 'A/S 접수 내역이 없습니다' }}</div>
      </div>
      <!-- 카드 목록 -->
      <div v-else class="as-table">
        <div class="at-head">
          <div class="col-date">접수일시</div>
          <div class="col-cust">고객</div>
          <div class="col-prod">기기 / 상품</div>
          <div class="col-sym">증상</div>
          <div class="col-diag">진단 · 처리</div>
          <div class="col-staff">접수 담당</div>
          <div class="col-status">상태</div>
          <div class="col-act"></div>
        </div>
        <div v-for="a in filtered" :key="a.id"
          class="at-row" :class="`row-${statusKey(a.status)}`"
          @click="openEditModal(a)">
          <div class="col-date">
            <div class="dt-main">{{ fmtDate(a.created_at) }}</div>
            <div class="dt-time">{{ fmtTime(a.created_at) }}</div>
          </div>
          <div class="col-cust">
            <div class="cust-name">{{ a.customer_name }}</div>
            <div class="cust-phone">{{ a.customer_phone }}</div>
          </div>
          <div class="col-prod">
            <div class="prod-name">{{ a.product_name || a.serial_number || '—' }}</div>
            <div v-if="a.product_name && a.serial_number" class="prod-manual">{{ a.serial_number }}</div>
          </div>
          <div class="col-sym text-cell">{{ a.symptom || '—' }}</div>
          <div class="col-diag text-cell">
            <span v-if="a.diagnosis" class="diag-text">{{ a.diagnosis }}</span>
            <span v-else class="empty-dash">—</span>
          </div>
          <div class="col-staff">
            <div v-if="a.received_by_name" class="staff-badge">{{ a.received_by_name }}</div>
            <span v-else class="empty-dash">—</span>
          </div>
          <div class="col-status">
            <span class="status-badge" :class="`sb-${statusKey(a.status)}`">{{ a.status }}</span>
          </div>
          <div class="col-act">
            <span class="edit-hint">수정 ›</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 신규 접수 모달 ── -->
    <div v-if="showNewModal" class="modal-backdrop" @click.self="showNewModal=false">
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
            <div class="fs-label">고객 <span class="req">필수</span></div>
            <div class="search-field">
              <input v-model="newForm.customerQ" class="inp" placeholder="고객명 또는 전화번호로 검색"
                @input="searchCustomer" @focus="showCustDrop=true" @blur="hideCustDrop" />
              <div v-if="showCustDrop && custResults.length" class="drop">
                <div v-for="c in custResults" :key="c.id" class="drop-item" @mousedown.prevent="selectCust(c)">
                  <span class="di-name">{{ c.name }}</span>
                  <span class="di-sub">{{ c.phone }}</span>
                </div>
              </div>
            </div>
            <div v-if="newForm.customer" class="sel-badge">
              <span class="sb-check">✓</span> {{ newForm.customer.name }} · {{ newForm.customer.phone }}
            </div>
            <div v-if="newErr === '고객을 선택해주세요'" class="field-err">고객을 선택해주세요</div>
          </div>

          <div class="form-row">
            <!-- 기기명 -->
            <div class="form-section" style="flex:1">
              <div class="fs-label">기기 / 상품명 <span class="req">필수</span></div>
              <div class="search-field">
                <input v-model="newForm.productQ" class="inp" :class="{ 'inp-err': productRequired && !newForm.product && !newForm.productManual }"
                  placeholder="기기명 검색…"
                  @input="searchProduct" @focus="showProdDrop=true" @blur="hideProdDrop" />
                <div v-if="showProdDrop && prodResults.length" class="drop">
                  <div v-for="p in prodResults" :key="p.id" class="drop-item" @mousedown.prevent="selectProd(p)">
                    <span class="di-name">{{ p.name }}</span>
                    <span class="di-sub cat-tag">{{ p.category }}</span>
                  </div>
                </div>
              </div>
              <div v-if="newForm.product" class="sel-badge">
                <span class="sb-check">✓</span> {{ newForm.product.name }}
              </div>
              <div v-if="!newForm.product" class="manual-row">
                <span class="mr-label">목록에 없으면</span>
                <input v-model="newForm.productManual" class="inp inp-sm"
                  :class="{ 'inp-err': productRequired && !newForm.product && !newForm.productManual }"
                  placeholder="직접 입력"
                  @input="newForm.product = null; newForm.productQ = ''" />
              </div>
              <div v-if="productRequired && !newForm.product && !newForm.productManual" class="field-err">기기명을 선택하거나 입력해주세요</div>
            </div>

            <!-- 대여기기 -->
            <div class="form-section" style="flex:1">
              <div class="fs-label">대여 기기 <span class="opt">선택</span></div>
              <input v-model="newForm.loanerNote" class="inp" placeholder="대여한 기기명" />
            </div>
          </div>

          <!-- 증상 -->
          <div class="form-section">
            <div class="fs-label">증상</div>
            <textarea v-model="newForm.symptom" class="inp" rows="3"
              placeholder="고객이 호소하는 증상을 입력하세요" />
          </div>
        </div>

        <div v-if="newErr && newErr !== '고객을 선택해주세요'" class="modal-err">{{ newErr }}</div>
        <div class="modal-ft">
          <button class="btn-ghost" @click="showNewModal=false">취소</button>
          <button class="btn-submit" :disabled="newLoading" @click="submitNew">
            {{ newLoading ? '접수 중…' : '접수 등록' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 수정 모달 ── -->
    <div v-if="showEditModal" class="modal-backdrop" @click.self="showEditModal=false">
      <div class="modal modal-lg">
        <div class="modal-hd">
          <div>
            <div class="mh-title">A/S 처리 내역</div>
            <div class="mh-sub">
              <span class="status-badge" :class="`sb-${statusKey(editTarget?.status)}`" style="margin-right:6px">{{ editTarget?.status }}</span>
              {{ editTarget?.customer_name }} · {{ editTarget?.product_name || editTarget?.serial_number || '기기 미지정' }}
              <span style="color:var(--tx3);margin-left:8px;font-size:10px">{{ fmtDate(editTarget?.created_at) }}</span>
            </div>
          </div>
          <button class="btn-close" @click="showEditModal=false">✕</button>
        </div>

        <div class="modal-body">
          <div class="form-row">
            <div class="form-section" style="flex:1">
              <div class="fs-label">증상</div>
              <textarea v-model="editForm.symptom" class="inp" rows="3" />
            </div>
            <div class="form-section" style="flex:1">
              <div class="fs-label">진단 결과</div>
              <textarea v-model="editForm.diagnosis" class="inp" rows="3" />
            </div>
          </div>

          <div class="form-section">
            <div class="fs-label">처리 내용</div>
            <textarea v-model="editForm.resolution" class="inp" rows="2" />
          </div>

          <div class="form-section">
            <div class="fs-label">처리 상태</div>
            <div class="status-picker">
              <label v-for="s in statusOptions" :key="s"
                class="sp-item" :class="{ on: editForm.status === s, [`sp-${statusKey(s)}`]: true }">
                <input type="radio" v-model="editForm.status" :value="s" style="display:none" />
                {{ s }}
              </label>
            </div>
          </div>
        </div>

        <div v-if="editErr" class="modal-err">{{ editErr }}</div>
        <div class="modal-ft">
          <button class="btn-ghost" @click="showEditModal=false">닫기</button>
          <button class="btn-submit" :disabled="editLoading" @click="submitEdit">
            {{ editLoading ? '저장 중…' : '변경 저장' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const STATUS_LIST = ['접수', '처리중', 'AS완료']
const statusOptions = STATUS_LIST

const statusList = [
  { key: '',      label: '전체',  cls: '' },
  { key: '접수',  label: '접수',  cls: 'sf-ye' },
  { key: '처리중', label: '처리중', cls: 'sf-ac' },
  { key: 'AS완료', label: 'AS완료', cls: 'sf-gr' },
]

// ── 목록 ──────────────────────────────────────────────────────
const items        = ref([])
const loading      = ref(false)
const q            = ref('')
const statusFilter = ref('')

const filtered = computed(() => {
  let list = items.value
  if (statusFilter.value) list = list.filter(a => a.status === statusFilter.value)
  if (q.value.trim()) {
    const kw = q.value.trim()
    list = list.filter(a =>
      a.customer_name?.includes(kw) || a.customer_phone?.includes(kw) ||
      a.product_name?.includes(kw)  || a.serial_number?.includes(kw) ||
      a.symptom?.includes(kw)
    )
  }
  return list
})

const statusCounts = computed(() => {
  const cnt = {}
  for (const s of STATUS_LIST) cnt[s] = items.value.filter(a => a.status === s).length
  return cnt
})

function statusKey(s) {
  const map = { '접수':'ye', '처리중':'ac', 'AS완료':'gr' }
  return map[s] || 'ok'
}

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

function setStatus(s) { statusFilter.value = s }

async function load() {
  loading.value = true
  try {
    const res = await api.get('/as-cases')
    items.value = res.data
  } catch { items.value = [] }
  finally { loading.value = false }
}

onMounted(load)

// ── 신규 접수 ─────────────────────────────────────────────────
const showNewModal    = ref(false)
const newLoading      = ref(false)
const newErr          = ref('')
const productRequired = ref(false)
const newForm         = ref({ customerQ:'', customer:null, productQ:'', product:null, productManual:'', loanerNote:'', symptom:'' })
const custResults     = ref([])
const showCustDrop    = ref(false)
const prodResults     = ref([])
const showProdDrop    = ref(false)

function openNewModal() {
  newErr.value = ''
  productRequired.value = false
  newForm.value = { customerQ:'', customer:null, productQ:'', product:null, productManual:'', loanerNote:'', symptom:'' }
  custResults.value = []
  prodResults.value = []
  showNewModal.value = true
}

function hideCustDrop() { setTimeout(() => { showCustDrop.value = false }, 150) }
function hideProdDrop() { setTimeout(() => { showProdDrop.value = false }, 150) }

let custTimer = null
function searchCustomer() {
  newForm.value.customer = null
  clearTimeout(custTimer)
  if (!newForm.value.customerQ.trim()) { custResults.value = []; return }
  custTimer = setTimeout(async () => {
    try {
      const res = await api.get('/customers/search', { params: { q: newForm.value.customerQ } })
      custResults.value = res.data.slice(0, 8)
    } catch { custResults.value = [] }
  }, 250)
}

function selectCust(c) {
  newForm.value.customer  = c
  newForm.value.customerQ = `${c.name} (${c.phone})`
  showCustDrop.value = false
  if (newErr.value === '고객을 선택해주세요') newErr.value = ''
}

let prodTimer = null
function searchProduct() {
  newForm.value.product = null
  productRequired.value = false
  clearTimeout(prodTimer)
  if (!newForm.value.productQ.trim()) { prodResults.value = []; return }
  prodTimer = setTimeout(async () => {
    try {
      const res = await api.get('/products/search', { params: { q: newForm.value.productQ, device_only: true } })
      prodResults.value = res.data
    } catch { prodResults.value = [] }
  }, 250)
}

function selectProd(p) {
  newForm.value.product  = p
  newForm.value.productQ = p.name
  showProdDrop.value = false
  productRequired.value = false
}

async function submitNew() {
  newErr.value = ''
  if (!newForm.value.customer) { newErr.value = '고객을 선택해주세요'; return }
  if (!newForm.value.product && !newForm.value.productManual.trim()) { productRequired.value = true; return }
  newLoading.value = true
  const loanerPrefix = newForm.value.loanerNote.trim() ? `[대여기기: ${newForm.value.loanerNote.trim()}]\n` : ''
  const symptomText  = loanerPrefix + (newForm.value.symptom.trim() || '')
  try {
    await api.post('/as-cases', {
      customer_id:   newForm.value.customer.id,
      product_id:    newForm.value.product?.id || undefined,
      serial_number: !newForm.value.product ? (newForm.value.productManual.trim() || undefined) : undefined,
      symptom:       symptomText || undefined,
    })
    showNewModal.value = false
    await load()
  } catch (e) {
    const d = e.response?.data?.detail
    newErr.value = typeof d === 'string' ? d : `오류 (HTTP ${e.response?.status ?? 'network'})`
  }
  finally { newLoading.value = false }
}

// ── 수정 ─────────────────────────────────────────────────────
const showEditModal = ref(false)
const editLoading   = ref(false)
const editErr       = ref('')
const editTarget    = ref(null)
const editForm      = ref({ status:'', diagnosis:'', resolution:'', symptom:'' })

function openEditModal(a) {
  editTarget.value = a
  editForm.value   = { status: a.status, diagnosis: a.diagnosis || '', resolution: a.resolution || '', symptom: a.symptom || '' }
  editErr.value    = ''
  showEditModal.value = true
}

async function submitEdit() {
  editErr.value = ''
  editLoading.value = true
  try {
    const res = await api.put(`/as-cases/${editTarget.value.id}`, {
      status:     editForm.value.status,
      diagnosis:  editForm.value.diagnosis,
      resolution: editForm.value.resolution,
      symptom:    editForm.value.symptom,
    })
    const idx = items.value.findIndex(a => a.id === editTarget.value.id)
    if (idx !== -1) items.value[idx] = res.data
    showEditModal.value = false
  } catch (e) { editErr.value = e.response?.data?.detail || '저장 실패' }
  finally { editLoading.value = false }
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
</script>

<style scoped>
/* ── 레이아웃 ── */
.page { display:flex; flex-direction:column; height:100%; overflow:hidden; background:var(--bg); }

/* ── 툴바 ── */
.toolbar {
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 20px; background:var(--bg2); border-bottom:1px solid var(--bd);
  flex-shrink:0; gap:12px;
}
.tb-left { display:flex; align-items:center; gap:10px; flex:1; min-width:0; }

.search-wrap { position:relative; display:flex; align-items:center; }
.si-ic { position:absolute; left:9px; font-size:14px; color:var(--tx3); pointer-events:none; }
.si {
  padding:7px 10px 7px 28px; border:1px solid var(--bd2); border-radius:var(--r);
  background:var(--bg); font-size:12px; color:var(--tx); outline:none; width:220px;
}
.si:focus { border-color:var(--ac); }

.sf-group { display:flex; gap:3px; }
.sf-btn {
  display:flex; align-items:center; gap:5px; padding:5px 10px;
  border:1px solid var(--bd2); border-radius:20px; background:none;
  cursor:pointer; font-size:11px; color:var(--tx2); font-family:var(--sans); transition:all .1s;
}
.sf-btn:hover { background:var(--bg3); }
.sf-cnt {
  font-family:var(--mono); font-size:10px; font-weight:600;
  background:var(--bg3); color:var(--tx3); padding:0 5px; border-radius:10px;
}
/* 활성 상태 */
.sf-btn.on           { background:var(--tx); color:#fff; border-color:var(--tx); }
.sf-btn.on .sf-cnt   { background:rgba(255,255,255,.2); color:#fff; }

.btn-new {
  display:flex; align-items:center; gap:5px; padding:7px 14px;
  background:var(--ac); color:#fff; border:none; border-radius:var(--r);
  font-size:12px; font-weight:600; cursor:pointer; transition:opacity .1s; white-space:nowrap;
}
.btn-new:hover { opacity:.88; }

/* ── 목록 ── */
.list-wrap { flex:1; overflow-y:auto; }

.empty-state {
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  height:200px; color:var(--tx3); gap:8px;
}
.es-icon { font-size:28px; }
.es-text  { font-size:13px; }

/* 테이블 */
.as-table { width:100%; }
.at-head {
  display:grid; grid-template-columns: 90px 130px 160px 1fr 1fr 80px 80px 52px;
  padding:8px 20px; background:var(--bg2); border-bottom:2px solid var(--bd);
  position:sticky; top:0; z-index:5;
  font-size:10px; font-weight:600; color:var(--tx3); letter-spacing:.5px; text-transform:uppercase;
}
.at-row {
  display:grid; grid-template-columns: 90px 130px 160px 1fr 1fr 80px 80px 52px;
  padding:11px 20px; border-bottom:1px solid var(--bd);
  cursor:pointer; transition:background .1s; align-items:start;
  border-left:3px solid transparent;
}
.at-row:hover { background:var(--bg3); }
.at-row:last-child { border-bottom:none; }

/* 행 상태별 왼쪽 색상 */
.row-ye { border-left-color:#f0b429; }
.row-ac { border-left-color:#4f86f7; }
.row-pu { border-left-color:#8b72d8; }
.row-gr { border-left-color:#34a87a; }
.row-re { border-left-color:#e05c5c; }

.dt-main { font-size:12px; font-weight:500; color:var(--tx); }
.dt-time { font-size:10px; color:var(--tx3); margin-top:2px; font-family:var(--mono); }

.cust-name  { font-size:13px; font-weight:600; color:var(--tx); }
.cust-phone { font-size:10px; color:var(--tx3); margin-top:2px; font-family:var(--mono); }

.prod-name   { font-size:12px; color:var(--tx); }
.prod-manual { font-size:10px; color:var(--tx3); margin-top:2px; }

.text-cell { font-size:12px; color:var(--tx2); line-height:1.5; white-space:pre-wrap; }
.diag-text { color:var(--tx2); }
.empty-dash { color:var(--tx3); }

.edit-hint { font-size:11px; color:var(--tx3); }
.at-row:hover .edit-hint { color:var(--ac); }

.staff-badge {
  display:inline-flex; align-items:center; padding:2px 7px;
  background:var(--bg3); border-radius:20px; font-size:10px;
  color:var(--tx2); font-weight:500;
}

/* 상태 뱃지 */
.status-badge {
  display:inline-flex; padding:3px 9px; border-radius:20px;
  font-size:10px; font-weight:700; letter-spacing:.3px;
}
.sb-ye { background:#fef3d4; color:#9a6c1a; }
.sb-ac { background:#ddeeff; color:#2f6bbf; }
.sb-pu { background:#ede9fc; color:#6b45c8; }
.sb-gr { background:#d4f0e3; color:#1f8a5e; }
.sb-re { background:#fde8e8; color:#c44b4b; }
.sb-ok { background:#f1f0ec; color:#6b6b67; }

/* ── 모달 ── */
.modal-backdrop {
  position:fixed; inset:0; background:rgba(0,0,0,.5);
  display:flex; align-items:center; justify-content:center; z-index:200;
}
.modal {
  background:var(--bg2); border-radius:12px; width:500px;
  display:flex; flex-direction:column; max-height:90vh; overflow:hidden;
  box-shadow:0 24px 64px rgba(0,0,0,.28);
}
.modal-lg { width:640px; }

.modal-hd {
  display:flex; align-items:flex-start; justify-content:space-between;
  padding:20px 22px 16px; border-bottom:1px solid var(--bd); flex-shrink:0;
}
.mh-title { font-size:15px; font-weight:700; color:var(--tx); }
.mh-sub   { font-size:11px; color:var(--tx2); margin-top:3px; display:flex; align-items:center; flex-wrap:wrap; }

.btn-close {
  border:none; background:none; cursor:pointer; color:var(--tx3);
  font-size:14px; padding:4px; border-radius:4px; transition:all .1s; flex-shrink:0;
}
.btn-close:hover { background:var(--bg3); color:var(--tx); }

.modal-body   { padding:18px 22px; display:flex; flex-direction:column; gap:14px; overflow-y:auto; }
.form-section { display:flex; flex-direction:column; gap:5px; }
.form-row     { display:flex; gap:14px; }

.fs-label { font-size:11px; font-weight:600; color:var(--tx2); display:flex; align-items:center; gap:5px; }
.req { font-size:9px; background:#fde8e8; color:#c44b4b; padding:1px 5px; border-radius:4px; font-weight:700; }
.opt { font-size:9px; background:var(--bg3); color:var(--tx3); padding:1px 5px; border-radius:4px; }

.inp {
  padding:8px 11px; border:1px solid var(--bd2); border-radius:var(--r);
  background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx);
  outline:none; resize:vertical; width:100%; box-sizing:border-box; transition:border .1s;
}
.inp:focus { border-color:var(--ac); box-shadow:0 0 0 2px rgba(244,132,95,.12); }
.inp.inp-err { border-color:var(--re); }

.search-field { position:relative; }
.drop {
  position:absolute; top:calc(100% + 3px); left:0; right:0;
  background:var(--bg2); border:1px solid var(--bd2); border-radius:var(--r);
  box-shadow:0 10px 28px rgba(0,0,0,.13); z-index:20; max-height:200px; overflow-y:auto;
}
.drop-item { display:flex; align-items:center; justify-content:space-between; padding:9px 12px; cursor:pointer; font-size:12px; }
.drop-item:hover { background:var(--bg3); }
.di-name { font-weight:600; color:var(--tx); }
.di-sub  { font-size:10px; color:var(--tx3); font-family:var(--mono); }
.cat-tag { background:var(--bg3); padding:1px 6px; border-radius:4px; }

.sel-badge {
  font-size:11px; color:var(--gr); background:#f0faf5;
  padding:5px 10px; border-radius:6px; display:flex; align-items:center; gap:4px;
}
.sb-check { font-weight:700; }

.manual-row { display:flex; align-items:center; gap:8px; }
.mr-label   { font-size:10px; color:var(--tx3); white-space:nowrap; }
.inp-sm     { flex:1; padding:6px 9px; font-size:12px; }

.field-err { font-size:10px; color:var(--re); }

/* 상태 선택기 */
.status-picker { display:flex; flex-wrap:wrap; gap:6px; }
.sp-item {
  padding:5px 12px; border-radius:20px; cursor:pointer;
  font-size:11px; font-weight:600; border:2px solid transparent; transition:all .1s;
  background:var(--bg3); color:var(--tx2);
}
.sp-item.on { transform:scale(1.04); }
.sp-ye { background:#fef9e8; color:#9a6c1a; }
.sp-ye.on { border-color:#f0b429; background:#fef3d4; }
.sp-ac { background:#eef4ff; color:#2f6bbf; }
.sp-ac.on { border-color:#4f86f7; background:#ddeeff; }
.sp-gr { background:#edfaf4; color:#1f8a5e; }
.sp-gr.on { border-color:#34a87a; background:#d4f0e3; }
.sp-re { background:#fef5f5; color:#c44b4b; }
.sp-re.on { border-color:#e05c5c; background:#fde8e8; }

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
  cursor:pointer; font-family:var(--sans); transition:opacity .1s;
}
.btn-submit:hover { opacity:.88; }
.btn-submit:disabled { opacity:.5; cursor:not-allowed; }
</style>
