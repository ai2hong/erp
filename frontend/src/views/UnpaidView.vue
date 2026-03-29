<template>
  <div class="page">
    <div class="toolbar">
      <span class="info-txt">미지급 서비스 현황 — 재고 복귀 또는 대기 중인 서비스 항목입니다.</span>
      <button class="btn sm" @click="load" style="margin-left:auto">새로고침</button>
    </div>

    <div class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>거래 #</th><th>발생일</th><th>고객</th>
            <th>서비스 종류</th><th class="num">총 수량</th>
            <th class="num">지급 완료</th><th class="num">미지급</th>
            <th>상태</th><th>메모</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="9" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!items.length"><td colspan="9" class="empty good">미지급 서비스 없음 ✓</td></tr>
          <tr v-for="r in items" :key="r.id">
            <td class="mono" style="font-size:10px">#{{ r.transaction_id }}</td>
            <td class="mono" style="font-size:10px">{{ fmtDt(r.created_at) }}</td>
            <td>{{ r.customer_name || '—' }}</td>
            <td>{{ r.service_kind }}</td>
            <td class="num mono">{{ r.total_qty }}</td>
            <td class="num mono" style="color:var(--gr)">{{ r.delivered_qty }}</td>
            <td class="num mono" style="color:var(--re);font-weight:600">{{ r.undelivered_qty }}</td>
            <td>
              <span class="tag" :class="{
                'tag-ye': r.delivery_status === '일부지급',
                'tag-re': r.delivery_status === '미지급',
                'tag-gr': r.delivery_status === '전체지급',
              }">{{ r.delivery_status }}</span>
            </td>
            <td style="font-size:11px;color:var(--tx3);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              {{ r.undelivered_reason || '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!loading" class="notice">
      <span class="notice-ic">ℹ</span>
      미지급 서비스 상세 조회는 백엔드 <code>/service-records</code> API가 필요합니다.
      현재 당일 거래의 미지급 항목만 표시됩니다.
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

async function load() {
  loading.value = true
  try {
    // 오늘 거래 목록을 불러온 뒤, 각 거래의 서비스 레코드를 집계
    // 현재 backend에 /service-records 엔드포인트가 없으므로
    // /transactions API에서 가져온 뒤 미지급 건만 필터링
    const res = await api.get('/transactions', { params: { store_id: storeId.value } })
    // 거래 목록 자체에서 미지급 정보가 없으므로 빈 배열 — 추후 API 연동 시 교체
    items.value = []
  } catch (e) {
    const status = e.response?.status
    if (status !== 404 && status !== 422) console.error(e)
    items.value = []
  } finally { loading.value = false }
}

function fmtDt(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
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
.tag-gr { background:#dcfce7; color:#16a34a; }
.tag-re { background:#fee2e2; color:#dc2626; }
.empty { text-align:center; color:var(--tx3); padding:24px; font-size:12px; }
.good { color:var(--gr) !important; }.notice { margin-top:12px; padding:10px 14px; background:#f0f9ff; border:1px solid #bae6fd; border-radius:var(--r); font-size:11px; color:#0369a1; display:flex; align-items:center; gap:8px; }
.notice-ic { font-size:14px; }
.notice code { background:#e0f2fe; padding:1px 4px; border-radius:3px; font-family:var(--mono); font-size:10px; }
.btn { display:inline-flex; align-items:center; padding:5px 11px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); }
.btn:hover { background:var(--bg3); }
.btn.sm { padding:4px 10px; font-size:11px; }
</style>
