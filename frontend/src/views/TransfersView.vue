<template>
  <div class="page">
    <!-- 상단 필터 -->
    <div class="toolbar">
      <select v-model="filterStatus" class="sel" @change="load">
        <option value="">전체 상태</option>
        <option>신청</option><option>발송중</option>
        <option>수령완료</option><option>취소</option>
      </select>
      <input v-model="filterMonth" type="month" class="sel" @change="load" />
      <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
      <button class="btn pr" @click="openRequest">+ 이동 신청</button>
    </div>

    <!-- 이동 목록 -->
    <div class="card" style="margin-bottom:12px">
      <table class="tw">
        <thead>
          <tr>
            <th>번호</th><th>방향</th><th>상품</th>
            <th class="num">수량</th><th>방법</th>
            <th>상태</th><th>신청일시</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="8" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!transfers.length"><td colspan="8" class="empty">이동 내역이 없습니다</td></tr>
          <tr v-for="t in transfers" :key="t.id">
            <td class="mono" style="font-size:10px">{{ t.transfer_number }}</td>
            <td>
              <span class="arrow">
                #{{ t.from_store_id }} → #{{ t.to_store_id }}
              </span>
            </td>
            <td>상품 #{{ t.product_id }}</td>
            <td class="num mono">{{ t.qty }}</td>
            <td>{{ t.transfer_method }}</td>
            <td>
              <span class="tag" :class="{
                'tag-ye': t.status === '신청',
                'tag-ac': t.status === '발송중',
                'tag-gr': t.status === '수령완료',
                'tag-re': t.status === '취소',
              }">{{ t.status }}</span>
            </td>
            <td class="mono" style="font-size:10px">{{ fmtDt(t.requested_at) }}</td>
            <td>
              <div class="actions">
                <button v-if="t.status === '신청'" class="btn xs" @click="ship(t.id)">발송</button>
                <button v-if="t.status === '발송중'" class="btn xs gr" @click="receive(t.id)">수령</button>
                <button v-if="t.status === '신청'" class="btn xs re" @click="openCancel(t)">취소</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 이동 신청 모달 -->
    <div v-if="showRequestModal" class="modal-backdrop" @click.self="showRequestModal = false">
      <div class="modal">
        <div class="modal-hd">재고 이동 신청</div>
        <div class="field">
          <label>출발 매장</label>
          <select v-model.number="reqForm.from_store_id" class="inp">
            <option value="">선택…</option>
            <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>도착 매장</label>
          <select v-model.number="reqForm.to_store_id" class="inp">
            <option value="">선택…</option>
            <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>상품 ID</label>
          <input v-model.number="reqForm.product_id" type="number" class="inp" placeholder="상품 번호 입력" />
        </div>
        <div class="field">
          <label>수량</label>
          <input v-model.number="reqForm.qty" type="number" min="1" class="inp" />
        </div>
        <div class="field">
          <label>이동 방법</label>
          <select v-model="reqForm.transfer_method" class="inp">
            <option>택배</option>
            <option>배달</option>
          </select>
        </div>
        <div class="field">
          <label>이동 사유</label>
          <input v-model="reqForm.reason" class="inp" placeholder="예: 재고 보충" />
        </div>
        <div class="field">
          <label>메모</label>
          <input v-model="reqForm.memo" class="inp" placeholder="선택 사항" />
        </div>
        <div v-if="reqError" class="err">{{ reqError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showRequestModal = false">취소</button>
          <button class="btn pr" :disabled="reqLoading" @click="submitRequest">
            {{ reqLoading ? '신청 중…' : '신청' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 취소 모달 -->
    <div v-if="showCancelModal" class="modal-backdrop" @click.self="showCancelModal = false">
      <div class="modal">
        <div class="modal-hd">이동 취소</div>
        <div style="font-size:12px;color:var(--tx2)">{{ cancelTarget?.transfer_number }} 을 취소합니다.</div>
        <div class="field">
          <label>취소 사유</label>
          <input v-model="cancelReason" class="inp" placeholder="사유를 입력하세요" />
        </div>
        <div v-if="cancelError" class="err">{{ cancelError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showCancelModal = false">닫기</button>
          <button class="btn re" @click="submitCancel">취소 확정</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth = useAuthStore()
const storeId = computed(() => auth.staff?.store_id || 1)

const transfers       = ref([])
const stores          = ref([])
const loading         = ref(false)
const filterStatus    = ref('')
const filterMonth     = ref('')

const showRequestModal = ref(false)
const reqLoading       = ref(false)
const reqError         = ref('')
const reqForm          = ref({ from_store_id: '', to_store_id: '', product_id: '', qty: 1, transfer_method: '택배', reason: '', memo: '' })

const showCancelModal  = ref(false)
const cancelTarget     = ref(null)
const cancelReason     = ref('')
const cancelError      = ref('')

async function load() {
  loading.value = true
  try {
    const params = { store_id: storeId.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterMonth.value)  params.month  = filterMonth.value
    const res = await api.get('/transfers', { params })
    transfers.value = res.data
  } catch { transfers.value = [] }
  finally { loading.value = false }
}

async function loadStores() {
  try {
    const res = await api.get('/auth/stores')
    stores.value = res.data
  } catch { stores.value = [] }
}

function openRequest() {
  reqError.value = ''
  reqForm.value = { from_store_id: storeId.value, to_store_id: '', product_id: '', qty: 1, transfer_method: '택배', reason: '', memo: '' }
  showRequestModal.value = true
}

async function submitRequest() {
  reqError.value = ''
  if (!reqForm.value.from_store_id || !reqForm.value.to_store_id) { reqError.value = '매장을 선택하세요'; return }
  if (!reqForm.value.product_id)  { reqError.value = '상품을 입력하세요'; return }
  if (!reqForm.value.reason.trim()) { reqError.value = '사유를 입력하세요'; return }
  reqLoading.value = true
  try {
    await api.post('/transfers', reqForm.value)
    showRequestModal.value = false
    await load()
  } catch (e) {
    reqError.value = e.response?.data?.detail || '신청 실패'
  } finally { reqLoading.value = false }
}

async function ship(id) {
  if (!confirm('발송 처리하시겠습니까?')) return
  try {
    await api.post(`/transfers/${id}/ship`)
    await load()
  } catch (e) { alert(e.response?.data?.detail || '처리 실패') }
}

async function receive(id) {
  if (!confirm('수령 완료 처리하시겠습니까?')) return
  try {
    await api.post(`/transfers/${id}/receive`)
    await load()
  } catch (e) { alert(e.response?.data?.detail || '처리 실패') }
}

function openCancel(t) {
  cancelTarget.value = t
  cancelReason.value = ''
  cancelError.value  = ''
  showCancelModal.value = true
}

async function submitCancel() {
  if (!cancelReason.value.trim()) { cancelError.value = '사유를 입력하세요'; return }
  try {
    await api.post(`/transfers/${cancelTarget.value.id}/cancel`, null, {
      params: { cancel_reason: cancelReason.value }
    })
    showCancelModal.value = false
    await load()
  } catch (e) { cancelError.value = e.response?.data?.detail || '취소 실패' }
}

function fmtDt(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

onMounted(() => { load(); loadStores() })
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; }
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:12px; flex-wrap:wrap; }
.sel { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:12px; color:var(--tx); outline:none; cursor:pointer; }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:8px 12px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.num { text-align:right; }
.mono { font-family:var(--mono); }
.arrow { font-family:var(--mono); font-size:11px; color:var(--tx2); }
.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-ac { background:#dbeafe; color:#1d4ed8; }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-re { background:#fee2e2; color:#dc2626; }
.actions { display:flex; gap:4px; }
.empty { text-align:center; color:var(--tx3); padding:24px; font-size:12px; }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.pr { background:var(--ac); color:#fff; border-color:var(--ac); }
.btn.sm { padding:4px 10px; font-size:11px; }
.btn.xs { padding:2px 8px; font-size:10px; }
.btn.gr { background:var(--gr); color:#fff; border-color:var(--gr); }
.btn.re { background:var(--re); color:#fff; border-color:var(--re); }
.modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { background:var(--bg2); border-radius:var(--r); padding:20px; width:380px; display:flex; flex-direction:column; gap:12px; max-height:90vh; overflow-y:auto; }
.modal-hd { font-size:14px; font-weight:700; }
.field { display:flex; flex-direction:column; gap:4px; }
.field label { font-size:11px; color:var(--tx2); }
.inp { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; }
.inp:focus { border-color:var(--ac); }
.err { color:var(--re); font-size:11px; }
.modal-ft { display:flex; justify-content:flex-end; gap:8px; }
</style>
