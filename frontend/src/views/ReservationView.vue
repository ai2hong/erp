<template>
  <div class="page">
    <div class="toolbar">
      <span class="info-txt">예약 주문 — 입고 예정 상품 선 결제 현황입니다.</span>
      <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
    </div>

    <div class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>예약번호</th><th>고객</th><th>상품</th>
            <th class="num">금액</th><th>입고 예정</th>
            <th>상태</th><th>처리</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="empty">로딩 중…</td></tr>
          <tr v-else-if="error"><td colspan="7" class="empty err-txt">{{ error }}</td></tr>
          <tr v-else-if="!items.length">
            <td colspan="7" class="empty">예약 주문이 없습니다</td>
          </tr>
          <tr v-for="r in items" :key="r.id">
            <td class="mono" style="font-size:10px">{{ r.reservation_number }}</td>
            <td>{{ r.customer_name }}</td>
            <td>{{ r.product_name }}</td>
            <td class="num mono">{{ r.amount?.toLocaleString() }}원</td>
            <td class="mono" style="font-size:10px">{{ r.expected_date || '미정' }}</td>
            <td>
              <span class="tag" :class="{
                'tag-ye': r.status === '대기',
                'tag-ac': r.status === '입고대기',
                'tag-gr': r.status === '완료',
                'tag-re': r.status === '취소',
              }">{{ r.status }}</span>
            </td>
            <td>
              <div class="actions">
                <button v-if="r.status === '대기'" class="btn xs" @click="markReady(r)">입고 확인</button>
                <button v-if="r.status === '입고대기'" class="btn xs gr" @click="markDone(r)">완료</button>
                <button v-if="['대기','입고대기'].includes(r.status)" class="btn xs re" @click="cancel(r)">취소</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!error && !loading" class="notice">
      <span class="notice-ic">ℹ</span>
      예약 주문 기능은 백엔드 <code>/reservations</code> API가 필요합니다.
      현재 데이터가 없으면 빈 화면이 표시됩니다.
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth = useAuthStore()
const storeId = computed(() => auth.staff?.store_id || 1)

const items   = ref([])
const loading = ref(false)
const error   = ref('')

async function load() {
  loading.value = true
  error.value   = ''
  try {
    // 예약 API가 구현되면 아래 URL을 /reservations 로 교체
    const res = await api.get('/reservations', { params: { store_id: storeId.value } })
    items.value = res.data
  } catch (e) {
    if (e.response?.status === 404) {
      // /reservations 엔드포인트가 없는 경우 빈 목록으로 처리
      items.value = []
    } else {
      error.value = e.response?.data?.detail || '데이터 로드 실패'
      items.value = []
    }
  } finally { loading.value = false }
}

async function markReady(r) {
  try {
    await api.post(`/reservations/${r.id}/ready`)
    await load()
  } catch (e) { alert(e.response?.data?.detail || '처리 실패') }
}

async function markDone(r) {
  try {
    await api.post(`/reservations/${r.id}/complete`)
    await load()
  } catch (e) { alert(e.response?.data?.detail || '처리 실패') }
}

async function cancel(r) {
  if (!confirm('예약을 취소하시겠습니까?')) return
  try {
    await api.post(`/reservations/${r.id}/cancel`)
    await load()
  } catch (e) { alert(e.response?.data?.detail || '처리 실패') }
}

onMounted(load)
</script>

<style scoped>
.page { padding:16px; height:100%; overflow-y:auto; }
.toolbar { display:flex; align-items:center; gap:8px; margin-bottom:12px; }
.info-txt { font-size:12px; color:var(--tx2); }
.card { background:var(--bg2); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg); }
.tw td { padding:8px 12px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.num { text-align:right; }
.mono { font-family:var(--mono); }
.tag { display:inline-flex; padding:1px 6px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-ye { background:#fef9c3; color:#854d0e; }
.tag-ac { background:#dbeafe; color:#1d4ed8; }
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-re { background:#fee2e2; color:#dc2626; }
.actions { display:flex; gap:4px; }
.empty { text-align:center; color:var(--tx3); padding:24px; font-size:12px; }
.err-txt { color:var(--re) !important; }
.notice { margin-top:12px; padding:10px 14px; background:#f0f9ff; border:1px solid #bae6fd; border-radius:var(--r); font-size:11px; color:#0369a1; display:flex; align-items:center; gap:8px; }
.notice-ic { font-size:14px; }
.notice code { background:#e0f2fe; padding:1px 4px; border-radius:3px; font-family:var(--mono); font-size:10px; }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.sm { padding:4px 10px; font-size:11px; }
.btn.xs { padding:2px 8px; font-size:10px; }
.btn.gr { background:var(--gr); color:#fff; border-color:var(--gr); }
.btn.re { background:var(--re); color:#fff; border-color:var(--re); }
</style>
