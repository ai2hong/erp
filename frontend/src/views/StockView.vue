<template>
  <div class="page">
    <div class="toolbar">
      <input v-model="filterQ" placeholder="상품명 검색…" class="search-input" />
      <select v-model="filterCat" class="sel">
        <option value="">전체 분류</option>
        <option v-for="c in categories" :key="c">{{ c }}</option>
      </select>
      <label class="chk-label">
        <input type="checkbox" v-model="showShortageOnly" /> 부족만 보기
      </label>
      <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
      <button class="btn pr" @click="openInbound(null)">+ 입고 처리</button>
    </div>

    <div class="badges">
      <span class="bdg">전체 <b>{{ inventory.length }}</b>종</span>
      <span class="bdg ye">부족 <b>{{ shortageCount }}</b>종</span>
      <span class="bdg re">품절 <b>{{ outOfStockCount }}</b>종</span>
      <span class="bdg gr">정상 <b>{{ normalCount }}</b>종</span>
    </div>

    <div class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>상품명</th><th>분류</th>
            <th class="num">실재고</th><th class="num">미지급</th>
            <th class="num">예약</th><th class="num">가용</th>
            <th>재고율</th><th>상태</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="9" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!filtered.length"><td colspan="9" class="empty">항목 없음</td></tr>
          <tr v-for="r in filtered" :key="r.id">
            <td class="pname">{{ r.product_name }}</td>
            <td><span class="cat-tag">{{ r.product_category }}</span></td>
            <td class="num mono">{{ r.qty_actual }}</td>
            <td class="num mono" :style="r.qty_undelivered > 0 ? 'color:var(--ye)' : ''">{{ r.qty_undelivered }}</td>
            <td class="num mono" :style="r.qty_reserved > 0 ? 'color:var(--pu)' : ''">{{ r.qty_reserved }}</td>
            <td class="num mono" :style="r.qty_available < 2 ? 'color:var(--re);font-weight:600' : ''">{{ r.qty_available }}</td>
            <td>
              <div class="bar-wrap">
                <div class="bar" :class="barClass(r)" :style="`width:${barPct(r)}%`"></div>
              </div>
            </td>
            <td>
              <span v-if="r.is_out_of_stock" class="tag tag-re">품절</span>
              <span v-else-if="r.is_shortage" class="tag tag-ye">부족</span>
              <span v-else class="tag tag-gr">정상</span>
            </td>
            <td><button class="btn xs" @click="openInbound(r)">입고</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 입고 모달 -->
    <div v-if="showInboundModal" class="modal-backdrop" @click.self="showInboundModal = false">
      <div class="modal">
        <div class="modal-hd">입고 처리</div>
        <div class="field">
          <label>상품</label>
          <select v-model="inForm.product_id" class="inp">
            <option value="">선택…</option>
            <option v-for="r in inventory" :key="r.product_id" :value="r.product_id">
              {{ r.product_name }} (현재 {{ r.qty_actual }}개)
            </option>
          </select>
        </div>
        <div class="field">
          <label>입고 수량</label>
          <input v-model.number="inForm.qty" type="number" min="1" class="inp" />
        </div>
        <div class="field">
          <label>메모</label>
          <input v-model="inForm.memo" class="inp" placeholder="선택 사항" />
        </div>
        <div v-if="inError" class="err">{{ inError }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showInboundModal = false">취소</button>
          <button class="btn pr" :disabled="inLoading" @click="submitInbound">
            {{ inLoading ? '처리 중…' : '입고 확정' }}
          </button>
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
const storeId = computed(() => auth.storeId)

const inventory        = ref([])
const loading          = ref(false)
const filterQ          = ref('')
const filterCat        = ref('')
const showShortageOnly = ref(false)
const showInboundModal = ref(false)
const inLoading        = ref(false)
const inError          = ref('')
const inForm           = ref({ product_id: '', qty: 1, memo: '' })

const categories = computed(() => [...new Set(inventory.value.map(r => r.product_category))])

const filtered = computed(() => {
  let list = inventory.value
  if (filterQ.value)          list = list.filter(r => r.product_name.includes(filterQ.value))
  if (filterCat.value)        list = list.filter(r => r.product_category === filterCat.value)
  if (showShortageOnly.value) list = list.filter(r => r.is_shortage || r.is_out_of_stock)
  return list
})

const shortageCount   = computed(() => inventory.value.filter(r => r.is_shortage && !r.is_out_of_stock).length)
const outOfStockCount = computed(() => inventory.value.filter(r => r.is_out_of_stock).length)
const normalCount     = computed(() => inventory.value.filter(r => !r.is_shortage && !r.is_out_of_stock).length)

function barPct(r) {
  if (!r.safety_qty) return r.qty_available > 0 ? 80 : 0
  return Math.min(100, Math.round((r.qty_available / r.safety_qty) * 100))
}
function barClass(r) {
  if (r.is_out_of_stock) return 'bar-re'
  if (r.is_shortage)     return 'bar-ye'
  return 'bar-gr'
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/inventory', { params: { store_id: storeId.value } })
    inventory.value = res.data
  } catch { inventory.value = [] }
  finally { loading.value = false }
}

function openInbound(row) {
  inError.value = ''
  inForm.value = { product_id: row?.product_id || '', qty: 1, memo: '' }
  showInboundModal.value = true
}

async function submitInbound() {
  inError.value = ''
  if (!inForm.value.product_id) { inError.value = '상품을 선택하세요'; return }
  if (inForm.value.qty < 1)     { inError.value = '수량은 1 이상이어야 합니다'; return }
  inLoading.value = true
  try {
    await api.post('/inventory/inbound', {
      store_id:   storeId.value,
      product_id: inForm.value.product_id,
      qty:        inForm.value.qty,
      memo:       inForm.value.memo,
    })
    showInboundModal.value = false
    await load()
  } catch (e) {
    inError.value = e.response?.data?.detail || '입고 처리 실패'
  } finally { inLoading.value = false }
}

onMounted(load)
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; }
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }
.search-input { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; width:200px; }
.search-input:focus { border-color:var(--ac); }
.sel { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:12px; color:var(--tx); outline:none; cursor:pointer; }
.chk-label { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--tx2); cursor:pointer; }
.badges { display:flex; gap:6px; margin-bottom:10px; flex-wrap:wrap; }
.bdg { display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:20px; font-size:11px; background:var(--bg3); color:var(--tx2); border:1px solid var(--bd); }
.bdg b { font-family:var(--mono); }
.bdg.ye { background:#fef9c3; color:#854d0e; border-color:#fef08a; }
.bdg.re { background:#fee2e2; color:#dc2626; border-color:#fca5a5; }
.bdg.gr { background:#dcfce7; color:#16a34a; border-color:#bbf7d0; }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:8px 12px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.num { text-align:right; }
.mono { font-family:var(--mono); }
.pname { font-weight:500; }
.cat-tag { display:inline-flex; padding:1px 6px; border-radius:4px; font-size:10px; background:var(--bg3); color:var(--tx2); font-family:var(--mono); }
.bar-wrap { width:70px; height:6px; background:var(--bg3); border-radius:3px; overflow:hidden; }
.bar { height:100%; border-radius:3px; }
.bar-gr { background:var(--gr); }
.bar-ye { background:var(--ye); }
.bar-re { background:var(--re); }
.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-re { background:#fee2e2; color:#dc2626; }
.empty { text-align:center; color:var(--tx3); padding:24px; font-size:12px; }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.pr { background:var(--ac); color:#fff; border-color:var(--ac); }
.btn.sm { padding:4px 10px; font-size:11px; }
.btn.xs { padding:2px 8px; font-size:10px; }
.modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { background:var(--bg2); border-radius:var(--r); padding:20px; width:360px; display:flex; flex-direction:column; gap:12px; }
.modal-hd { font-size:14px; font-weight:700; }
.field { display:flex; flex-direction:column; gap:4px; }
.field label { font-size:11px; color:var(--tx2); }
.inp { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; }
.inp:focus { border-color:var(--ac); }
.err { color:var(--re); font-size:11px; }
.modal-ft { display:flex; justify-content:flex-end; gap:8px; }
</style>
