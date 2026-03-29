<template>
  <div class="page">
    <!-- 검색 바 -->
    <div class="search-bar">
      <input
        v-model="q"
        placeholder="이름 또는 전화번호 검색…"
        class="search-input"
        @input="onSearch"
        @keydown.esc="clearSearch"
      />
      <button class="btn pr" @click="showRegModal = true">+ 신규 등록</button>
    </div>

    <!-- 검색 결과 드롭다운 -->
    <div v-if="results.length" class="search-results">
      <div
        v-for="r in results"
        :key="r.id"
        class="sr-item"
        @click="selectCustomer(r)"
      >
        <span class="sr-name">{{ r.name }}</span>
        <span class="sr-phone mono">{{ r.phone }}</span>
        <span class="sr-mil mono">{{ r.mileage_balance.toLocaleString() }}P</span>
        <span class="sr-cnt">{{ r.visit_count }}회</span>
      </div>
    </div>

    <!-- 고객 상세 -->
    <div v-if="customer" class="g2" style="margin-top:16px">
      <!-- 프로필 카드 -->
      <div>
        <div class="card prof-card">
          <div class="prof-avatar">{{ customer.name?.[0] }}</div>
          <div class="prof-name">{{ customer.name }}</div>
          <div class="prof-phone mono">{{ customer.phone }}</div>
          <div class="prof-stats">
            <div class="stat">
              <div class="stat-v mono">{{ customer.mileage_balance?.toLocaleString() }}</div>
              <div class="stat-k">적립금</div>
            </div>
            <div class="stat">
              <div class="stat-v mono">{{ customer.visit_count }}</div>
              <div class="stat-k">방문 횟수</div>
            </div>
            <div class="stat">
              <div class="stat-v mono">{{ customer.total_purchase?.toLocaleString() }}</div>
              <div class="stat-k">누적 구매</div>
            </div>
          </div>
          <div v-if="customer.last_visit_at" class="prof-last">
            마지막 방문: <span class="mono">{{ fmtDate(customer.last_visit_at) }}</span>
          </div>
          <div v-if="customer.staff_memo" class="prof-memo">
            <div class="memo-label">직원 메모</div>
            <div class="memo-body">{{ customer.staff_memo }}</div>
          </div>
          <div class="prof-actions">
            <button class="btn" @click="showMemoModal = true">메모 편집</button>
          </div>
        </div>
      </div>

      <!-- 거래 이력 탭 -->
      <div class="card">
        <div class="ch">
          <span>거래 이력</span>
          <span class="ch-sub">오늘 기준</span>
          <button class="btn sm" style="margin-left:auto" @click="loadTxHistory">새로고침</button>
        </div>
        <div v-if="loadingTx" class="empty">로딩 중…</div>
        <div v-else-if="!txHistory.length" class="empty">거래 이력이 없습니다</div>
        <table v-else class="tw">
          <thead><tr><th>날짜</th><th>채널</th><th>금액</th><th>색상</th></tr></thead>
          <tbody>
            <tr v-for="tx in txHistory" :key="tx.id">
              <td class="mono">{{ fmtTime(tx.created_at) }}</td>
              <td>{{ tx.channel }}</td>
              <td class="num mono">{{ tx.total_amount.toLocaleString() }}원</td>
              <td>
                <span class="tag" :class="{
                  'tag-gr': tx.tx_color === '정상',
                  'tag-ye': tx.tx_color === '서비스',
                  'tag-re': tx.tx_color === '할인',
                  'tag-pu': tx.tx_color === '교환',
                }">{{ tx.tx_color }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 미선택 상태 -->
    <div v-else-if="!results.length" class="empty-state">
      <div class="es-icon">◉</div>
      <div class="es-text">고객을 검색하세요</div>
    </div>

    <!-- 신규 등록 모달 -->
    <div v-if="showRegModal" class="modal-backdrop" @click.self="showRegModal = false">
      <div class="modal">
        <div class="modal-hd">신규 고객 등록</div>
        <div class="field">
          <label>이름</label>
          <input v-model="regForm.name" placeholder="홍길동" class="inp" />
        </div>
        <div class="field">
          <label>전화번호</label>
          <input v-model="regForm.phone" placeholder="010-0000-0000" class="inp" />
        </div>
        <div class="field">
          <label>직원 메모</label>
          <textarea v-model="regForm.staff_memo" class="inp" rows="2" placeholder="선택 사항" />
        </div>
        <div v-if="regError" class="err">{{ regError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showRegModal = false">취소</button>
          <button class="btn pr" :disabled="regLoading" @click="registerCustomer">
            {{ regLoading ? '등록 중…' : '등록' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 메모 편집 모달 -->
    <div v-if="showMemoModal" class="modal-backdrop" @click.self="showMemoModal = false">
      <div class="modal">
        <div class="modal-hd">직원 메모 편집</div>
        <textarea v-model="memoEdit" class="inp" rows="4" placeholder="고객에 대한 메모를 입력하세요" />
        <div class="modal-ft">
          <button class="btn" @click="showMemoModal = false">취소</button>
          <button class="btn pr" @click="saveMemo">저장</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth = useAuthStore()
const storeId = computed(() => auth.staff?.store_id || 1)

const q         = ref('')
const results   = ref([])
const customer  = ref(null)
const txHistory = ref([])
const loadingTx = ref(false)

const showRegModal  = ref(false)
const showMemoModal = ref(false)
const regLoading    = ref(false)
const regError      = ref('')
const memoEdit      = ref('')

const regForm = ref({ name: '', phone: '', staff_memo: '' })

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  if (!q.value.trim()) { results.value = []; return }
  searchTimer = setTimeout(async () => {
    try {
      const res = await api.get('/customers/search', { params: { q: q.value } })
      results.value = res.data
    } catch { results.value = [] }
  }, 300)
}

function clearSearch() {
  q.value = ''
  results.value = []
}

async function selectCustomer(r) {
  results.value = []
  q.value = ''
  try {
    const res = await api.get(`/customers/${r.id}`)
    customer.value = res.data
    memoEdit.value = res.data.staff_memo || ''
    loadTxHistory()
  } catch { customer.value = r }
}

async function loadTxHistory() {
  if (!customer.value) return
  loadingTx.value = true
  try {
    const res = await api.get('/transactions', { params: { store_id: storeId.value } })
    txHistory.value = res.data
  } catch { txHistory.value = [] }
  finally { loadingTx.value = false }
}

async function registerCustomer() {
  regError.value = ''
  if (!regForm.value.name.trim() || !regForm.value.phone.trim()) {
    regError.value = '이름과 전화번호를 입력하세요'
    return
  }
  regLoading.value = true
  try {
    const res = await api.post('/customers', regForm.value)
    customer.value = { ...res.data, visit_count: 0, total_purchase: 0 }
    showRegModal.value = false
    regForm.value = { name: '', phone: '', staff_memo: '' }
    txHistory.value = []
  } catch (e) {
    regError.value = e.response?.data?.detail || '등록 실패'
  } finally { regLoading.value = false }
}

async function saveMemo() {
  showMemoModal.value = false
  if (customer.value) customer.value.staff_memo = memoEdit.value
}

function fmtDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('ko-KR')
}

function fmtTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; position:relative; }
.search-bar { display:flex; gap:8px; margin-bottom:4px; }
.search-input { flex:1; padding:8px 12px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:13px; font-family:var(--sans); color:var(--tx); outline:none; }
.search-input:focus { border-color:var(--ac); }
.search-results { background:var(--bg2); border:1px solid var(--bd2); border-radius:var(--r); overflow:hidden; margin-bottom:8px; }
.sr-item { display:flex; align-items:center; gap:12px; padding:9px 14px; cursor:pointer; font-size:12px; border-bottom:1px solid var(--bd); }
.sr-item:last-child { border-bottom:none; }
.sr-item:hover { background:var(--bg3); }
.sr-name { font-weight:600; min-width:60px; }
.sr-phone { color:var(--tx2); flex:1; }
.sr-mil { color:var(--ac); font-size:11px; }
.sr-cnt { color:var(--tx3); font-size:11px; min-width:40px; text-align:right; }
.g2 { display:grid; grid-template-columns:280px 1fr; gap:12px; }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.prof-card { padding:20px; display:flex; flex-direction:column; align-items:center; gap:8px; }
.prof-avatar { width:56px; height:56px; border-radius:50%; background:var(--ac); color:#fff; font-size:22px; font-weight:700; display:flex; align-items:center; justify-content:center; }
.prof-name { font-size:16px; font-weight:700; }
.prof-phone { font-size:12px; color:var(--tx2); }
.prof-stats { display:flex; gap:0; width:100%; margin:8px 0; border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.stat { flex:1; text-align:center; padding:10px 4px; border-right:1px solid var(--bd); }
.stat:last-child { border-right:none; }
.stat-v { font-size:16px; font-weight:700; }
.stat-k { font-size:9px; color:var(--tx3); margin-top:2px; }
.prof-last { font-size:11px; color:var(--tx3); }
.prof-memo { width:100%; background:var(--bg3); border-radius:6px; padding:8px 10px; }
.memo-label { font-size:9px; color:var(--tx3); font-family:var(--mono); margin-bottom:4px; }
.memo-body { font-size:12px; color:var(--tx2); white-space:pre-wrap; }
.prof-actions { margin-top:4px; width:100%; }
.ch { display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--bd); font-weight:600; font-size:12px; }
.ch-sub { font-family:var(--mono); font-size:10px; color:var(--tx3); font-weight:400; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:8px 12px; border-bottom:1px solid var(--bd); }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.num { text-align:right; }
.mono { font-family:var(--mono); }
.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-re { background:#fee2e2; color:#dc2626; }
.tag-pu { background:#ede9fe; color:#7c3aed; }
.empty { text-align:center; color:var(--tx3); padding:20px; font-size:12px; }
.empty-state { display:flex; flex-direction:column; align-items:center; justify-content:center; height:300px; gap:8px; }
.es-icon { font-size:36px; color:var(--tx3); }
.es-text { font-size:14px; color:var(--tx3); }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); width:100%; justify-content:center; }
.btn.pr { background:var(--ac); color:#fff; border-color:var(--ac); }
.btn.sm { padding:3px 8px; font-size:10px; width:auto; }
.modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { background:var(--bg2); border-radius:var(--r); padding:20px; width:360px; display:flex; flex-direction:column; gap:12px; }
.modal-hd { font-size:14px; font-weight:700; }
.field { display:flex; flex-direction:column; gap:4px; }
.field label { font-size:11px; color:var(--tx2); }
.inp { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; resize:vertical; }
.inp:focus { border-color:var(--ac); }
.err { color:var(--re); font-size:11px; }
.modal-ft { display:flex; justify-content:flex-end; gap:8px; }
.modal-ft .btn { width:auto; }
</style>
