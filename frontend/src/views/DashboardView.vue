<template>
  <div class="page">
    <!-- KPI 카드 -->
    <div class="kpi-row">
      <div class="kpi">
        <div class="kl">오늘 매출</div>
        <div class="kv">{{ totalSales.toLocaleString() }}원</div>
        <div class="kd">{{ transactions.length }}건 거래</div>
      </div>
      <div class="kpi">
        <div class="kl">현금 매출</div>
        <div class="kv">{{ cashSales.toLocaleString() }}원</div>
        <div class="kd">카드 {{ cardSales.toLocaleString() }}원</div>
      </div>
      <div class="kpi">
        <div class="kl">정상 거래</div>
        <div class="kv" style="color:var(--gr)">{{ normalCount }}건</div>
        <div class="kd" style="color:var(--re)">서비스/할인 {{ specialCount }}건</div>
      </div>
      <div class="kpi">
        <div class="kl">재고 부족</div>
        <div class="kv" :style="shortages.length ? 'color:var(--re)' : 'color:var(--gr)'">
          {{ shortages.length }}종
        </div>
        <div class="kd">{{ outOfStock.length }}종 품절</div>
      </div>
      <div class="kpi">
        <div class="kl">마지막 거래</div>
        <div class="kv" style="font-size:14px">{{ lastTxTime || '—' }}</div>
        <div class="kd">{{ lastTxAmount ? lastTxAmount.toLocaleString() + '원' : '' }}</div>
      </div>
    </div>

    <!-- 본문 그리드 -->
    <div class="g65">
      <!-- 판매 목록 -->
      <div class="card">
        <div class="ch">
          오늘 판매 내역
          <span class="ch-sub">{{ today }}</span>
          <router-link to="/tx-history" style="margin-left:auto;text-decoration:none">
            <button class="btn sm">전체 보기 →</button>
          </router-link>
          <button class="btn sm" @click="load">새로고침</button>
        </div>
        <table class="tw">
          <thead>
            <tr><th>시각</th><th>채널</th><th>금액</th><th>색상</th><th>담당</th></tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="5" class="empty">로딩 중…</td></tr>
            <tr v-else-if="!transactions.length"><td colspan="5" class="empty">오늘 거래가 없습니다</td></tr>
            <tr v-for="tx in transactions" :key="tx.id">
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
              <td style="font-size:11px;color:var(--tx2)">{{ tx.staff_name || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 우측 패널 -->
      <div>
        <!-- 재고 부족 알림 -->
        <div class="card" style="margin-bottom:12px">
          <div class="ch">재고 부족 알림</div>
          <div v-if="loadingInv" class="empty">로딩 중…</div>
          <div v-else-if="!shortages.length" class="empty" style="color:var(--gr)">부족 재고 없음 ✓</div>
          <div v-for="s in shortages" :key="s.id" class="al">
            <span class="al-ic" :style="s.is_out_of_stock ? 'color:var(--re)' : 'color:var(--ye)'">
              {{ s.is_out_of_stock ? '●' : '▲' }}
            </span>
            <div class="al-tx">
              <div>{{ s.product_name }}</div>
              <div class="al-sub">가용 {{ s.qty_available }}개 · 실재고 {{ s.qty_actual }}개</div>
            </div>
          </div>
        </div>

        <!-- 매장 정보 -->
        <div class="card">
          <div class="ch">담당자 정보</div>
          <div class="si-row"><span class="si-k">이름</span><span>{{ auth.staff?.name }}</span></div>
          <div class="si-row"><span class="si-k">역할</span><span>{{ auth.staff?.role }}</span></div>
          <div class="si-row"><span class="si-k">매장 ID</span><span class="mono">#{{ auth.staff?.store_id }}</span></div>
          <div class="si-row"><span class="si-k">날짜</span><span class="mono">{{ today }}</span></div>
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

const transactions = ref([])
const inventory    = ref([])
const loading      = ref(false)
const loadingInv   = ref(false)

const today = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
})

const totalSales  = computed(() => transactions.value.reduce((s, t) => s + t.total_amount, 0))
const cashSales   = computed(() => 0)  // transactions list doesn't include payment breakdown
const cardSales   = computed(() => 0)
const normalCount = computed(() => transactions.value.filter(t => t.tx_color === '정상').length)
const specialCount = computed(() => transactions.value.filter(t => t.tx_color !== '정상').length)
const shortages   = computed(() => inventory.value.filter(i => i.is_shortage || i.is_out_of_stock))
const outOfStock  = computed(() => inventory.value.filter(i => i.is_out_of_stock))
const lastTx      = computed(() => transactions.value[0])
const lastTxTime  = computed(() => lastTx.value ? fmtTime(lastTx.value.created_at) : null)
const lastTxAmount = computed(() => lastTx.value?.total_amount)

function fmtTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/transactions', { params: { store_id: storeId.value } })
    transactions.value = res.data
  } catch { transactions.value = [] }
  finally { loading.value = false }
}

async function loadInventory() {
  loadingInv.value = true
  try {
    const res = await api.get('/inventory', { params: { store_id: storeId.value } })
    inventory.value = res.data
  } catch { inventory.value = [] }
  finally { loadingInv.value = false }
}

onMounted(() => { load(); loadInventory() })
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; }
.kpi-row { display:flex; gap:12px; margin-bottom:16px; }
.kpi { flex:1; background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); padding:14px 16px; }
.kl { font-size:10px; color:var(--tx3); font-family:var(--mono); letter-spacing:.5px; margin-bottom:6px; text-transform:uppercase; }
.kv { font-size:20px; font-weight:700; font-family:var(--mono); margin-bottom:2px; }
.kd { font-size:11px; color:var(--tx2); }
.g65 { display:grid; grid-template-columns:1fr 320px; gap:12px; }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.ch { display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--bd); font-weight:600; font-size:12px; }
.ch-sub { font-family:var(--mono); font-size:10px; color:var(--tx3); font-weight:400; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:8px 12px; border-bottom:1px solid var(--bd); }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.empty { text-align:center; color:var(--tx3); padding:20px; font-size:12px; }
.num { text-align:right; }
.mono { font-family:var(--mono); }
.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-re { background:#fee2e2; color:#dc2626; }
.tag-pu { background:#ede9fe; color:#7c3aed; }
.al { display:flex; align-items:flex-start; gap:10px; padding:8px 14px; border-bottom:1px solid var(--bd); }
.al:last-child { border-bottom:none; }
.al-ic { font-size:10px; margin-top:2px; flex-shrink:0; }
.al-tx { font-size:12px; flex:1; }
.al-sub { font-size:10px; color:var(--tx3); margin-top:2px; font-family:var(--mono); }
.si-row { display:flex; align-items:center; padding:8px 14px; border-bottom:1px solid var(--bd); font-size:12px; }
.si-row:last-child { border-bottom:none; }
.si-k { width:60px; color:var(--tx3); font-size:10px; font-family:var(--mono); }
.btn { display:inline-flex; align-items:center; padding:4px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); cursor:pointer; font-size:11px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.sm { padding:3px 8px; font-size:10px; }
</style>
