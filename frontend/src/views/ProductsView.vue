<template>
  <div class="page">

    <!-- ── 툴바 ── -->
    <div class="toolbar">
      <div class="tl-left">
        <select v-model="filterCat" class="sel" @change="loadProducts">
          <option value="">전체 분류</option>
          <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="filterStatus" class="sel" @change="loadProducts">
          <option value="">전체 상태</option>
          <option value="판매중">판매중</option>
          <option value="품절">품절</option>
          <option value="단종">단종</option>
        </select>
        <button class="btn sm" @click="loadProducts">새로고침</button>
        <span class="cnt-label">{{ products.length }}개</span>
      </div>
      <div class="tl-right">
        <button class="btn sm" @click="downloadTemplate">양식 다운로드</button>
        <label class="btn sm pr upload-btn">
          엑셀 업로드
          <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="onFileChange" />
        </label>
      </div>
    </div>

    <!-- ── 업로드 결과 ── -->
    <div v-if="uploadResult" class="result-bar" :class="uploadResult.skipped ? 'res-warn' : 'res-ok'">
      <span>신규 <b>{{ uploadResult.inserted }}</b>개</span>
      <span>업데이트 <b>{{ uploadResult.updated }}</b>개</span>
      <span v-if="uploadResult.skipped">건너뜀 <b class="warn">{{ uploadResult.skipped }}</b>개</span>
      <button class="res-close" @click="uploadResult=null">✕</button>
      <div v-if="uploadResult.errors?.length" class="err-list">
        <div v-for="e in uploadResult.errors" :key="e" class="err-item">{{ e }}</div>
      </div>
    </div>
    <div v-if="uploadErr" class="result-bar res-err">
      {{ uploadErr }}
      <button class="res-close" @click="uploadErr=''">✕</button>
    </div>

    <!-- ── 품목 테이블 ── -->
    <div class="card">
      <table class="tw">
        <thead>
          <tr>
            <th>분류</th>
            <th>상품명</th>
            <th class="num">정상가</th>
            <th class="num">기기할인가</th>
            <th>판매상태</th>
            <th>메모</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="6" class="empty">로딩 중…</td></tr>
          <tr v-else-if="!products.length"><td colspan="6" class="empty">품목이 없습니다</td></tr>
          <tr v-for="p in products" :key="p.id">
            <td><span class="cat-tag">{{ p.category }}</span></td>
            <td class="nm">{{ p.name }}</td>
            <td class="num">{{ p.normal_price?.toLocaleString() }}원</td>
            <td class="num">{{ p.device_discount_price ? p.device_discount_price.toLocaleString() + '원' : '—' }}</td>
            <td>
              <span class="tag" :class="statusClass(p.sale_status)">{{ p.sale_status }}</span>
            </td>
            <td class="memo">{{ p.memo || '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const CATEGORIES = [
  '입호흡 이벤트', '입호흡 일반', '입호흡 일반(할인제외)',
  '폐호흡 이벤트', '폐호흡 일반', '폐호흡 일반(할인제외)',
  '입호흡 기기', '폐호흡 기기', '입호흡 기기(단일가)', '폐호흡 기기(단일가)',
  '입호흡 코일', '입호흡 코일(고가)', '폐호흡 코일', '폐호흡 코일(고가)',
  '악세사리',
]

const products     = ref([])
const loading      = ref(false)
const filterCat    = ref('')
const filterStatus = ref('')

const fileInput    = ref(null)
const uploading    = ref(false)
const uploadResult = ref(null)
const uploadErr    = ref('')

async function loadProducts() {
  loading.value = true
  try {
    const params = { store_id: auth.staff?.store_id || 1 }
    if (filterCat.value)    params.category    = filterCat.value
    if (filterStatus.value) params.sale_status = filterStatus.value
    const res = await api.get('/products', { params })
    products.value = res.data
  } catch { products.value = [] }
  finally { loading.value = false }
}

async function onFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''   // 같은 파일 재업로드 허용

  uploadResult.value = null
  uploadErr.value    = ''
  uploading.value    = true

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await api.post('/products/upload-excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    uploadResult.value = res.data
    await loadProducts()
  } catch (err) {
    const d = err.response?.data?.detail
    uploadErr.value = typeof d === 'string' ? d : `업로드 실패 (${err.response?.status ?? 'network'})`
  } finally { uploading.value = false }
}

async function downloadTemplate() {
  try {
    const res = await api.get('/products/excel-template', { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = '품목_업로드_양식.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    alert('양식 다운로드 실패')
  }
}

function statusClass(s) {
  return { 'tag-gr': s === '판매중', 'tag-ye': s === '품절', 'tag-re': s === '단종' }
}

onMounted(loadProducts)
</script>

<style scoped>
.page { padding: 16px; height: 100%; overflow-y: auto; box-sizing: border-box; }

.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.tl-left, .tl-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sel { padding: 6px 10px; border: 1px solid var(--bd2); border-radius: var(--r); background: var(--bg2); font-size: 12px; color: var(--tx); outline: none; cursor: pointer; }
.cnt-label { font-size: 11px; color: var(--tx3); }

.btn { display: inline-flex; align-items: center; padding: 5px 11px; border: 1px solid var(--bd2); border-radius: var(--r); background: var(--bg2); cursor: pointer; font-size: 12px; font-family: var(--sans); color: var(--tx2); }
.btn:hover { background: var(--bg3); }
.btn.sm { padding: 4px 10px; font-size: 11px; }
.btn.pr { background: var(--ac); color: #fff; border-color: var(--ac); }
.btn.pr:hover { opacity: .88; }
.upload-btn { cursor: pointer; }

/* 업로드 결과 */
.result-bar { display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px; border-radius: var(--r); font-size: 12px; flex-wrap: wrap; position: relative; margin-bottom: 12px; }
.res-ok   { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
.res-warn { background: #fef9c3; color: #713f12; border: 1px solid #fde047; }
.res-err  { background: #fee2e2; color: #7f1d1d; border: 1px solid #fca5a5; }
.warn { color: #dc2626; }
.res-close { margin-left: auto; background: none; border: none; cursor: pointer; font-size: 13px; color: inherit; }
.err-list { width: 100%; display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
.err-item { font-size: 11px; opacity: .8; }

/* 테이블 */
.card { background: var(--bg2); border: 1px solid var(--bd); border-radius: var(--r); overflow: hidden; }
.tw { width: 100%; border-collapse: collapse; font-size: 12px; }
.tw th { padding: 7px 12px; text-align: left; font-size: 10px; color: var(--tx3); font-family: var(--mono); font-weight: 500; border-bottom: 1px solid var(--bd); background: var(--bg); }
.tw td { padding: 7px 12px; border-bottom: 1px solid var(--bd); vertical-align: middle; }
.tw tr:last-child td { border-bottom: none; }
.tw tr:hover td { background: var(--bg3); }
.num { text-align: right; font-family: var(--mono); font-size: 11px; }
.nm { font-weight: 500; }
.memo { font-size: 11px; color: var(--tx3); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.cat-tag { font-size: 10px; background: var(--bg3); border: 1px solid var(--bd2); border-radius: 4px; padding: 1px 5px; color: var(--tx2); white-space: nowrap; }

.tag { display: inline-flex; padding: 1px 6px; border-radius: 20px; font-size: 10px; font-weight: 600; font-family: var(--mono); }
.tag-gr { background: #dcfce7; color: #16a34a; }
.tag-ye { background: #fef9c3; color: #854d0e; }
.tag-re { background: #fee2e2; color: #dc2626; }

.empty { text-align: center; color: var(--tx3); padding: 32px; font-size: 12px; }
</style>
