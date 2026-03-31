<template>
  <div class="page">

    <!-- 상단: 달력 + KPI -->
    <div class="top-grid">

      <!-- 달력 -->
      <div class="card cal-card">
        <div class="cal-nav">
          <button class="nav-btn" @click="prevMonth">‹</button>
          <span class="cal-title">{{ calYear }}년 {{ calMonth + 1 }}월</span>
          <button class="nav-btn" @click="nextMonth">›</button>
          <button class="nav-btn today-btn" @click="goToday">오늘</button>
        </div>
        <div class="cal-grid">
          <div class="cal-dow" v-for="d in ['일','월','화','수','목','금','토']" :key="d">{{ d }}</div>
          <div
            v-for="cell in calCells" :key="cell.key"
            class="cal-cell"
            :class="{
              'other-month': !cell.thisMonth,
              'is-today':    cell.isToday,
              'is-selected': cell.isSelected,
              'is-sunday':   cell.dow === 0,
              'is-saturday': cell.dow === 6,
            }"
            @click="selectDate(cell.dateStr)"
          >
            {{ cell.day }}
          </div>
        </div>
      </div>

      <!-- KPI 카드들 -->
      <div class="kpi-col">
        <div class="kpi">
          <div class="kl">{{ selectedDate }} 매출</div>
          <div class="kv">{{ totalSales.toLocaleString() }}원</div>
          <div class="kd">{{ transactions.length }}건</div>
        </div>
        <div class="kpi">
          <div class="kl">정상 거래</div>
          <div class="kv" style="color:var(--gr)">{{ normalCount }}건</div>
          <div class="kd" style="color:var(--re)">서비스/할인 {{ specialCount }}건</div>
        </div>
        <div class="kpi">
          <div class="kl">채널별</div>
          <div class="ch-stats">
            <span v-for="(cnt, ch) in channelCounts" :key="ch" class="ch-pill">
              {{ ch }} <b>{{ cnt }}</b>
            </span>
          </div>
        </div>
        <div class="kpi">
          <div class="kl">담당별</div>
          <div class="ch-stats">
            <span v-for="(cnt, nm) in staffCounts" :key="nm" class="ch-pill">
              {{ nm }} <b>{{ cnt }}</b>
            </span>
            <span v-if="!Object.keys(staffCounts).length" style="font-size:11px;color:var(--tx3)">—</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 거래 목록 -->
    <div class="card">
      <div class="ch">
        판매 내역
        <span class="ch-sub">{{ selectedDate }}</span>
        <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
      </div>
      <table class="tw">
        <thead>
          <tr>
            <th>시각</th>
            <th>거래번호</th>
            <th>채널</th>
            <th class="num">금액</th>
            <th>유형</th>
            <th>담당</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="6" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!transactions.length"><td colspan="6" class="empty">거래 내역이 없습니다</td></tr>
          <tr v-for="tx in transactions" :key="tx.id">
            <td class="mono">{{ fmtTime(tx.created_at) }}</td>
            <td class="mono" style="font-size:10px;color:var(--tx3)">{{ tx.tx_number || '—' }}</td>
            <td>
              <span class="ch-tag" :class="'ch-' + tx.channel">{{ tx.channel }}</span>
            </td>
            <td class="num mono fw">{{ tx.total_amount.toLocaleString() }}원</td>
            <td>
              <span class="tag" :class="{
                'tag-gr': tx.tx_color === '정상',
                'tag-ye': tx.tx_color === '서비스',
                'tag-re': tx.tx_color === '할인',
                'tag-pu': tx.tx_color === '교환',
              }">{{ tx.tx_color }}</span>
            </td>
            <td>
              <span v-if="tx.staff_name" class="staff-badge">{{ tx.staff_name }}</span>
              <span v-else style="color:var(--tx3);font-size:10px">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <!-- 하단 합계 -->
      <div v-if="transactions.length" class="total-row">
        <span>합계</span>
        <span class="mono fw">{{ totalSales.toLocaleString() }}원</span>
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

// ── 날짜 ────────────────────────────────────────
const now = new Date()
const calYear    = ref(now.getFullYear())
const calMonth   = ref(now.getMonth())   // 0-based
const selectedDate = ref(toDateStr(now))

function toDateStr(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

function prevMonth() {
  if (calMonth.value === 0) { calYear.value--; calMonth.value = 11 }
  else calMonth.value--
}
function nextMonth() {
  if (calMonth.value === 11) { calYear.value++; calMonth.value = 0 }
  else calMonth.value++
}
function goToday() {
  const d = new Date()
  calYear.value  = d.getFullYear()
  calMonth.value = d.getMonth()
  selectDate(toDateStr(d))
}

function selectDate(str) {
  selectedDate.value = str
  load()
}

// ── 달력 셀 생성 ─────────────────────────────────
const calCells = computed(() => {
  const year  = calYear.value
  const month = calMonth.value
  const first = new Date(year, month, 1)
  const last  = new Date(year, month + 1, 0)
  const todayStr = toDateStr(new Date())
  const cells = []

  // 앞 빈칸 (이전 달)
  for (let i = 0; i < first.getDay(); i++) {
    const d = new Date(year, month, -first.getDay() + i + 1)
    cells.push({ key: `p${i}`, day: d.getDate(), thisMonth: false, dateStr: toDateStr(d), dow: d.getDay(), isToday: false, isSelected: false })
  }
  // 이번 달
  for (let d = 1; d <= last.getDate(); d++) {
    const dt  = new Date(year, month, d)
    const str = toDateStr(dt)
    cells.push({ key: str, day: d, thisMonth: true, dateStr: str, dow: dt.getDay(), isToday: str === todayStr, isSelected: str === selectedDate.value })
  }
  // 뒷 빈칸 (다음 달)
  const rem = 42 - cells.length
  for (let i = 1; i <= rem; i++) {
    const d = new Date(year, month + 1, i)
    cells.push({ key: `n${i}`, day: d.getDate(), thisMonth: false, dateStr: toDateStr(d), dow: d.getDay(), isToday: false, isSelected: false })
  }
  return cells
})

// ── 거래 데이터 ──────────────────────────────────
const transactions = ref([])
const loading      = ref(false)

const totalSales   = computed(() => transactions.value.reduce((s, t) => s + t.total_amount, 0))
const normalCount  = computed(() => transactions.value.filter(t => t.tx_color === '정상').length)
const specialCount = computed(() => transactions.value.filter(t => t.tx_color !== '정상').length)

const channelCounts = computed(() => {
  const m = {}
  for (const t of transactions.value) m[t.channel] = (m[t.channel] || 0) + 1
  return m
})
const staffCounts = computed(() => {
  const m = {}
  for (const t of transactions.value) {
    const nm = t.staff_name || '미지정'
    m[nm] = (m[nm] || 0) + 1
  }
  return m
})

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

function fmtTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

onMounted(load)
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; display:flex; flex-direction:column; gap:12px; }

/* 상단 그리드 */
.top-grid { display:grid; grid-template-columns:auto 1fr; gap:12px; align-items:start; }

/* 달력 카드 */
.cal-card { padding:14px 16px; width:280px; }
.cal-nav { display:flex; align-items:center; gap:6px; margin-bottom:12px; }
.cal-title { flex:1; text-align:center; font-size:13px; font-weight:700; }
.nav-btn { width:26px; height:26px; border:1px solid var(--bd2); border-radius:5px; background:var(--bg); cursor:pointer; font-size:14px; color:var(--tx2); display:flex; align-items:center; justify-content:center; line-height:1; }
.nav-btn:hover { background:var(--bg3); }
.today-btn { width:auto; padding:0 8px; font-size:10px; font-family:var(--mono); }
.cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:2px; }
.cal-dow { text-align:center; font-size:9px; color:var(--tx3); font-family:var(--mono); padding:3px 0 5px; font-weight:600; }
.cal-cell { text-align:center; font-size:12px; padding:5px 0; border-radius:5px; cursor:pointer; color:var(--tx); line-height:1.2; }
.cal-cell:hover { background:var(--bg3); }
.cal-cell.other-month { color:var(--tx3); }
.cal-cell.is-sunday   { color:var(--re); }
.cal-cell.is-saturday { color:var(--ac2); }
.cal-cell.other-month.is-sunday   { color:#fca5a5; }
.cal-cell.other-month.is-saturday { color:#bfdbfe; }
.cal-cell.is-today    { background:#fff3eb; font-weight:700; color:var(--ac); }
.cal-cell.is-selected { background:var(--ac); color:#fff !important; font-weight:700; }

/* KPI 열 */
.kpi-col { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.kpi { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); padding:14px 16px; }
.kl  { font-size:10px; color:var(--tx3); font-family:var(--mono); letter-spacing:.5px; margin-bottom:6px; text-transform:uppercase; }
.kv  { font-size:20px; font-weight:700; font-family:var(--mono); margin-bottom:2px; }
.kd  { font-size:11px; color:var(--tx2); }
.ch-stats { display:flex; flex-wrap:wrap; gap:5px; margin-top:4px; }
.ch-pill { font-size:10px; font-family:var(--mono); background:var(--bg3); border:1px solid var(--bd); border-radius:20px; padding:2px 8px; color:var(--tx2); }
.ch-pill b { color:var(--tx); font-weight:700; }

/* 거래 테이블 */
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.ch   { display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--bd); font-weight:600; font-size:12px; }
.ch-sub { font-family:var(--mono); font-size:10px; color:var(--tx3); font-weight:400; }
.tw   { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:9px 12px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.empty { text-align:center; color:var(--tx3); padding:28px; font-size:12px; }
.num   { text-align:right; }
.mono  { font-family:var(--mono); }
.fw    { font-weight:700; }
.ch-tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:500; font-family:var(--mono); background:var(--bg3); color:var(--tx2); }
.ch-매장 { background:#ecfdf5; color:#065f46; }
.ch-배달 { background:#eff6ff; color:#1e40af; }
.ch-택배 { background:#faf5ff; color:#6b21a8; }
.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-re { background:#fee2e2; color:#dc2626; }
.tag-pu { background:#ede9fe; color:#7c3aed; }
.staff-badge { display:inline-flex; padding:2px 8px; background:var(--bg3); border-radius:20px; font-size:10px; color:var(--tx2); font-weight:500; }
.total-row { display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:var(--bg); border-top:2px solid var(--bd2); font-size:12px; font-weight:600; color:var(--tx2); }
.btn { display:inline-flex; align-items:center; padding:4px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); cursor:pointer; font-size:11px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.sm { padding:3px 8px; font-size:10px; }
</style>
