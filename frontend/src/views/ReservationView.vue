<template>
  <div class="page">
    <div class="toolbar">
      <input v-model="q" class="si" placeholder="고객명 · 전화번호 · 상품명 검색" />
      <div class="sf-group">
        <button v-for="s in statusList" :key="s" class="sf-btn" :class="{ on: statusFilter === s }" @click="statusFilter = s">
          {{ s || '전체' }}
          <span class="sf-cnt">{{ s ? items.filter(r=>r.status===s).length : items.length }}</span>
        </button>
      </div>
      <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
    </div>

    <div class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>접수일</th>
            <th>고객</th>
            <th>상품</th>
            <th class="num">수량</th>
            <th>메모</th>
            <th>접수 담당</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!filtered.length"><td colspan="7" class="empty">예약 주문이 없습니다</td></tr>
          <tr v-for="r in filtered" :key="r.id">
            <td class="mono" style="font-size:10px;white-space:nowrap">{{ fmtDt(r.created_at) }}</td>
            <td>
              <div class="cust-name">{{ r.customer_name }}</div>
              <div class="cust-phone">{{ r.customer_phone }}</div>
            </td>
            <td>{{ r.product_name || '—' }}</td>
            <td class="num mono">{{ r.quantity }}</td>
            <td class="note-cell">{{ r.note || '—' }}</td>
            <td>
              <span v-if="r.staff_name" class="staff-badge">{{ r.staff_name }}</span>
              <span v-else class="empty-dash">—</span>
            </td>
            <td>
              <span class="tag" :class="{
                'tag-ye': r.status === '예약접수',
                'tag-ac': r.status === '입고대기',
                'tag-gr': r.status === '완료',
                'tag-re': r.status === '취소',
              }">{{ r.status }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

const items        = ref([])
const loading      = ref(false)
const q            = ref('')
const statusFilter = ref('')
const statusList   = ['', '예약접수', '입고대기', '완료', '취소']

const filtered = computed(() => {
  let list = items.value
  if (statusFilter.value) list = list.filter(r => r.status === statusFilter.value)
  if (q.value.trim()) {
    const kw = q.value.trim()
    list = list.filter(r =>
      r.customer_name?.includes(kw) || r.customer_phone?.includes(kw) || r.product_name?.includes(kw)
    )
  }
  return list
})

async function load() {
  loading.value = true
  try {
    const res = await api.get('/reservations')
    items.value = res.data
  } catch { items.value = [] }
  finally { loading.value = false }
}

function fmtDt(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

onMounted(load)
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; display:flex; flex-direction:column; gap:12px; }
.toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.si { width:240px; padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; color:var(--tx); outline:none; }
.si:focus { border-color:var(--ac); }
.sf-group { display:flex; gap:3px; }
.sf-btn { display:flex; align-items:center; gap:4px; padding:4px 10px; border:1px solid var(--bd2); border-radius:20px; background:none; cursor:pointer; font-size:11px; color:var(--tx2); font-family:var(--sans); transition:all .1s; }
.sf-btn:hover { background:var(--bg3); }
.sf-btn.on { background:var(--ac); color:#fff; border-color:var(--ac); }
.sf-cnt { font-family:var(--mono); font-size:10px; background:var(--bg3); color:var(--tx3); padding:0 4px; border-radius:8px; }
.sf-btn.on .sf-cnt { background:rgba(255,255,255,.25); color:#fff; }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:8px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:9px 12px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.num { text-align:right; }
.mono { font-family:var(--mono); }
.cust-name  { font-weight:600; }
.cust-phone { font-size:10px; color:var(--tx3); margin-top:2px; font-family:var(--mono); }
.note-cell  { font-size:11px; color:var(--tx3); max-width:140px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.empty      { text-align:center; color:var(--tx3); padding:28px; font-size:12px; }
.empty-dash { color:var(--tx3); }
.staff-badge { display:inline-flex; padding:2px 8px; background:var(--bg3); border-radius:20px; font-size:10px; color:var(--tx2); font-weight:500; }
.tag { display:inline-flex; padding:2px 8px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-ye { background:#fef3d4; color:#9a6c1a; }
.tag-ac { background:#ddeeff; color:#2f6bbf; }
.tag-gr { background:#d4f0e3; color:#1f8a5e; }
.tag-re { background:#fde8e8; color:#c44b4b; }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.sm { padding:4px 10px; font-size:11px; }
</style>
