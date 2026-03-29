<template>
  <div class="page">
    <div class="toolbar">
      <input v-model="selectedDate" type="date" class="sel" @change="load" />
      <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
    </div>

    <!-- 요약 카드 -->
    <div class="summary-row">
      <div class="sum-card">
        <div class="sum-label">총 매출</div>
        <div class="sum-val mono">{{ totalSales.toLocaleString() }}원</div>
      </div>
      <div class="sum-card">
        <div class="sum-label">거래 건수</div>
        <div class="sum-val mono">{{ transactions.length }}건</div>
      </div>
      <div class="sum-card">
        <div class="sum-label">정상 거래</div>
        <div class="sum-val mono" style="color:var(--gr)">{{ normalCount }}건</div>
      </div>
      <div class="sum-card">
        <div class="sum-label">서비스/할인</div>
        <div class="sum-val mono" style="color:var(--ye)">{{ specialCount }}건</div>
      </div>
    </div>

    <!-- 채널별 분류 -->
    <div class="ch-grid">
      <div class="card ch-card" v-for="(txs, ch) in byChannel" :key="ch">
        <div class="cch">
          <span class="ch-name">{{ ch }}</span>
          <span class="ch-cnt mono">{{ txs.length }}건</span>
        </div>
        <div class="ch-total mono">{{ txs.reduce((s, t) => s + t.total_amount, 0).toLocaleString() }}원</div>
        <div v-for="c in colorGroups(txs)" :key="c.color" class="ch-row">
          <span class="ch-color" :class="{
            'tag-gr': c.color === '정상',
            'tag-ye': c.color === '서비스',
            'tag-re': c.color === '할인',
            'tag-pu': c.color === '교환',
          }">{{ c.color }}</span>
          <span class="ch-c-cnt mono">{{ c.count }}건</span>
          <span class="ch-c-amt mono">{{ c.total.toLocaleString() }}원</span>
        </div>
      </div>
    </div>

    <!-- 거래 상세 목록 -->
    <div class="card" style="margin-top:12px">
      <div class="ch-hd">
        거래 상세
        <span class="ch-sub">{{ selectedDate }}</span>
        <span class="close-status" :class="todayClosed ? 'closed' : 'open'">
          {{ todayClosed ? '마감 완료' : '마감 전' }}
        </span>
        <button v-if="!todayClosed" class="btn pr sm" style="margin-left:auto" @click="confirmClose">
          일마감 처리
        </button>
      </div>
      <table class="tw">
        <thead>
          <tr><th>시각</th><th>채널</th><th class="num">금액</th><th>색상</th></tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="4" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!transactions.length"><td colspan="4" class="empty">거래 없음</td></tr>
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
          </tr>
        </tbody>
      </table>
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
const loading      = ref(false)
const todayClosed  = ref(false)

const today = new Date()
const selectedDate = ref(
  `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`
)

const totalSales   = computed(() => transactions.value.reduce((s, t) => s + t.total_amount, 0))
const normalCount  = computed(() => transactions.value.filter(t => t.tx_color === '정상').length)
const specialCount = computed(() => transactions.value.filter(t => t.tx_color !== '정상').length)

const byChannel = computed(() => {
  const map = {}
  for (const tx of transactions.value) {
    if (!map[tx.channel]) map[tx.channel] = []
    map[tx.channel].push(tx)
  }
  return map
})

function colorGroups(txs) {
  const map = {}
  for (const tx of txs) {
    if (!map[tx.tx_color]) map[tx.tx_color] = { color: tx.tx_color, count: 0, total: 0 }
    map[tx.tx_color].count++
    map[tx.tx_color].total += tx.total_amount
  }
  return Object.values(map)
}

function fmtTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/transactions', {
      params: { store_id: storeId.value, tx_date: selectedDate.value }
    })
    transactions.value = res.data
  } catch { transactions.value = [] }
  finally { loading.value = false }
}

function confirmClose() {
  if (!confirm(`${selectedDate.value} 일마감을 처리하시겠습니까?\n총 ${transactions.value.length}건 · ${totalSales.value.toLocaleString()}원`)) return
  todayClosed.value = true
}

onMounted(load)
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; }
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:12px; }
.sel { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:12px; color:var(--tx); outline:none; cursor:pointer; }
.summary-row { display:flex; gap:10px; margin-bottom:12px; }
.sum-card { flex:1; background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); padding:14px 16px; }
.sum-label { font-size:10px; color:var(--tx3); font-family:var(--mono); text-transform:uppercase; margin-bottom:6px; }
.sum-val { font-size:20px; font-weight:700; }
.ch-grid { display:flex; gap:10px; flex-wrap:wrap; }
.ch-card { flex:1; min-width:180px; padding:14px; }
.cch { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.ch-name { font-size:12px; font-weight:600; }
.ch-cnt { font-size:11px; color:var(--tx3); }
.ch-total { font-size:18px; font-weight:700; margin-bottom:8px; }
.ch-row { display:flex; align-items:center; gap:6px; margin-bottom:4px; font-size:11px; }
.ch-color { padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.ch-c-cnt { color:var(--tx3); }
.ch-c-amt { margin-left:auto; font-family:var(--mono); color:var(--tx2); }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.ch-hd { display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--bd); font-weight:600; font-size:12px; }
.ch-sub { font-family:var(--mono); font-size:10px; color:var(--tx3); font-weight:400; }
.close-status { font-size:10px; font-weight:600; padding:2px 8px; border-radius:20px; font-family:var(--mono); }
.close-status.open { background:#fef9c3; color:#854d0e; }
.close-status.closed { background:#dcfce7; color:#16a34a; }
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
.empty { text-align:center; color:var(--tx3); padding:24px; font-size:12px; }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.pr { background:var(--ac); color:#fff; border-color:var(--ac); }
.btn.sm { padding:3px 8px; font-size:10px; }
</style>
