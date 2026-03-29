<template>
  <div class="pos-wrap">

    <!-- ── 왼쪽: 고객 검색 + 상품 그리드 ── -->
    <div class="pos-left">

      <!-- 고객 검색 바 -->
      <div class="cust-bar">
        <div class="cust-row">
          <span class="cust-lbl">고객</span>
          <input
            class="cust-inp"
            v-model="custQ"
            placeholder="전화번호 또는 이름"
            @keydown.enter="searchCustomer"
          />
          <button class="btn sm" @click="searchCustomer">조회</button>
          <button class="btn sm">신규</button>
        </div>
        <div class="cust-info" :class="{ show: customer }">
          <div class="cust-av">{{ customer?.name?.[0] || '?' }}</div>
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:6px">
              <span style="font-size:13px;font-weight:700">{{ customer?.name }}</span>
              <span style="font-size:10px;color:var(--tx2);font-family:var(--mono)">{{ customer?.phone }}</span>
            </div>
            <div style="font-size:10px;color:var(--tx2);margin-top:1px">{{ customer?.memo || '메모 없음' }}</div>
          </div>
          <div style="text-align:right;flex-shrink:0">
            <div style="font-size:9px;color:var(--tx3);font-family:var(--mono)">적립금</div>
            <div style="font-family:var(--mono);font-size:13px;font-weight:600;color:var(--ac2)">
              {{ (customer?.mileage_balance || 0).toLocaleString() }}원
            </div>
          </div>
          <span class="cust-clear" @click="clearCustomer">×</span>
        </div>
      </div>

      <!-- 상품 선택 영역 -->
      <div class="prod-area">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
          <div class="cat-tabs">
            <div
              v-for="t in TABS" :key="t.key"
              class="ctab" :class="{ on: activeTab === t.key }"
              @click="activeTab = t.key"
            >{{ t.label }}</div>
          </div>
          <input class="prod-search" v-model="prodSearch" placeholder="상품 검색" />
        </div>

        <div class="prod-grid">
          <div
            v-for="p in filteredProducts" :key="p.id"
            class="pb" :class="{ 'pb-active': cartQtyMap[p.id] }"
            @click="addToCart(p)"
          >
            <div class="pn">{{ p.name }}</div>
            <div class="pt">{{ p.category }}</div>
            <div class="pp">
              <span>{{ p.normal_price.toLocaleString() }}원</span>
              <span v-if="isEventCat(p.category)"   class="badge ev">이벤트</span>
              <span v-if="isHighPodCat(p.category)" class="badge hp">고가팟</span>
              <span v-if="isExclCat(p.category)"    class="badge ex">할인제외</span>
              <span v-if="cartQtyMap[p.id]"          class="badge cart-b">×{{ cartQtyMap[p.id] }}</span>
            </div>
            <div v-if="p.stock" class="pp" style="margin-top:2px">
              <span :style="{ color: stockColor(p.stock) }">재고 {{ p.stock.qty_available }}</span>
            </div>
          </div>
          <div v-if="!filteredProducts.length" class="prod-empty">상품이 없습니다</div>
        </div>
      </div>
    </div>

    <!-- ── 오른쪽 패널 ── -->
    <div class="pos-right">

      <!-- 채널 바 -->
      <div class="ch-bar">
        <span class="ch-lbl">채널</span>
        <div style="display:flex;gap:3px">
          <div
            v-for="ch in ['매장','배달','택배']" :key="ch"
            class="tab" :class="{ on: cart.channel === ch }"
            @click="cart.channel = ch"
          >{{ ch }}</div>
        </div>
      </div>

      <!-- 장바구니 + 서비스 -->
      <div class="pos-body">

        <!-- 장바구니 -->
        <div class="cart-section">
          <div class="cart-hd">
            <span class="cart-hd-title">장바구니</span>
            <span class="bx gy">
              {{ cart.items.length ? `${cart.items.reduce((s,i)=>s+i.qty,0)}개` : '비어있음' }}
            </span>
          </div>
          <div v-if="!cart.items.length" class="cart-empty">상품을 선택해주세요</div>
          <div v-for="item in cart.items" :key="item.id" class="ci">
            <div style="flex:1;min-width:0">
              <div class="ci-nm">{{ item.name }}</div>
              <span class="ci-tg">{{ item.category }}</span>
            </div>
            <div class="qc">
              <div class="qb" @click="cart.updateQty(item.id, -1)">−</div>
              <div class="qn">{{ item.qty }}</div>
              <div class="qb" @click="cart.updateQty(item.id, 1)">+</div>
            </div>
            <div class="cp">{{ (lineAmounts.get(item.id) || 0).toLocaleString() }}원</div>
            <span class="cdl" @click="cart.removeItem(item.id)">×</span>
          </div>
        </div>

        <!-- 서비스 선택 -->
        <div class="svc-section">
          <div class="svc-hd">
            <span class="svc-hd-title">서비스 선택</span>
            <span v-if="svcBundles.length" class="svc-badge">
              {{ svcBundles.map(s => s.kind).join(' · ') }}
            </span>
          </div>

          <div v-if="!svcBundles.length" class="svc-empty">
            <div style="font-size:20px;opacity:.2">◎</div>
            <div>상품을 담으면 서비스 선택이 표시됩니다</div>
          </div>

          <div v-for="(svc, si) in svcBundles" :key="si">
            <div style="font-size:11px;font-weight:600;color:var(--tx);margin:6px 0 2px">
              {{ svc.kind }} — 총 {{ svc.qty }}개
            </div>
            <div style="font-size:10px;color:var(--tx2);margin-bottom:6px">{{ svc.note }}</div>

            <div v-for="(bundle, bi) in svc.bundles" :key="bi" class="svc-bundle">
              <div class="sb-head">
                <span class="sb-tag" :class="bundle.bundleType === 'SET3' ? 'st-set3' : 'st-rem'">
                  {{ bundle.bundleType === 'SET3' ? `묶음${bundle.bundleIndex} (3개단위)` : `나머지${bundle.bundleIndex}` }}
                </span>
              </div>

              <!-- SET3 그룹 선택 -->
              <div v-if="bundle.bundleType === 'SET3'" class="choice-row">
                <div class="c-btn" :class="{ on: bundle.chosenGroup === 'set1' }" @click="chooseGroup(si, bi, 'set1')">
                  묶음1<br><span style="font-size:9px">코일·팟·악세사리 3개</span>
                </div>
                <div class="c-btn" :class="{ on: bundle.chosenGroup === 'set2' }" @click="chooseGroup(si, bi, 'set2')">
                  묶음2<br><span style="font-size:9px">입호흡 이벤트 1병</span>
                </div>
              </div>

              <!-- 슬롯 -->
              <div class="svc-prod-list">
                <div
                  v-for="(slot, sloti) in bundle.slots" :key="sloti"
                  class="svc-prod-row" :class="slot.selectedProduct ? 'sg' : 'szero'"
                >
                  <div style="flex:1;min-width:0">
                    <div v-if="slot.selectedProduct" style="display:flex;align-items:center;gap:5px">
                      <span class="sp-nm">{{ slot.selectedProduct.name }}</span>
                      <span class="sp-cat">{{ slot.selectedProduct.category }}</span>
                      <span style="margin-left:auto;cursor:pointer;color:var(--tx3);font-size:12px"
                            @click="clearSlotProduct(si, bi, sloti)">×</span>
                    </div>
                    <div v-else style="position:relative">
                      <input
                        class="slot-search"
                        :placeholder="slot.categories.join(' / ') + ' 검색'"
                        v-model="slotQueries[`${si}-${bi}-${sloti}`]"
                        @focus="activeSlot = `${si}-${bi}-${sloti}`"
                        @blur="onSlotBlur"
                      />
                      <div
                        v-if="activeSlot === `${si}-${bi}-${sloti}` && slotFilteredProducts(slot, si, bi, sloti).length"
                        class="slot-dropdown"
                      >
                        <div
                          v-for="sp in slotFilteredProducts(slot, si, bi, sloti)" :key="sp.id"
                          class="slot-opt"
                          @mousedown.prevent="selectSlotProduct(si, bi, sloti, sp)"
                        >
                          <span style="flex:1">{{ sp.name }}</span>
                          <span style="font-size:9px;color:var(--tx3)">재고 {{ sp.stock?.qty_available ?? '?' }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 서비스 액션 -->
            <div class="svc-action">
              <div class="svc-chips">
                <span v-for="(chip, chi) in svcChips(svc)" :key="chi" class="schip" :class="chip.cls">
                  {{ chip.label }}
                </span>
              </div>
              <button class="svc-confirm-btn" :class="svcBtnClass(svc)" @click="openSvcModal(svc)">
                서비스 확정
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 하단 고정 바 ── -->
      <div class="pos-bottom">

        <!-- 가격 계산 요약 -->
        <div class="calc-bar" :class="{ show: cart.items.length }">
          <div class="cb-seg">
            <span class="cb-lbl">규칙</span>
            <span class="cb-rule">{{ priceResult.ruleLabel || '—' }}</span>
          </div>
          <div class="cb-seg">
            <span class="cb-lbl">액상</span>
            <span class="cb-val">{{ priceResult.liquidPrice ? priceResult.liquidPrice.toLocaleString()+'원' : '—' }}</span>
          </div>
          <div class="cb-seg">
            <span class="cb-lbl">기기</span>
            <span class="cb-val">{{ priceResult.devicePrice ? priceResult.devicePrice.toLocaleString()+'원' : '—' }}</span>
          </div>
          <div class="cb-seg">
            <span class="cb-lbl">코일/기타</span>
            <span class="cb-val">{{ priceResult.othersPrice ? priceResult.othersPrice.toLocaleString()+'원' : '—' }}</span>
          </div>
        </div>

        <!-- 결제 수단 + 적립금 -->
        <div class="pay-row">
          <div class="pm-btns">
            <div
              v-for="pm in availablePayMethods" :key="pm"
              class="pm-btn" :class="{ on: payMethod === pm }"
              @click="payMethod = pm"
            >{{ pm }}</div>
          </div>
          <span class="pts-lbl">적립금</span>
          <input
            class="pts-inp" type="number" v-model.number="milesUsed"
            placeholder="0" step="10"
            :disabled="!customer || cart.channel !== '매장'"
          />
          <span style="font-size:10px;color:var(--tx2)">원</span>
          <button class="btn sm" @click="useAllMiles" :disabled="!customer">전액</button>
        </div>

        <!-- 판정 -->
        <div class="judge-row">
          <span class="jitem">결제 <span class="bl">{{ payResult?.nature || '—' }}</span></span>
          <span class="jitem">서비스 <span :class="payResult?.svcEligible ? 'ok' : 'no'">
            {{ payResult?.svcEligible ? '✓ 가능' : '✗ 불가' }}
          </span></span>
          <span class="jitem">적립 <span :class="payResult?.earnEligible ? 'ok' : 'no'">
            {{ payResult?.earnEligible ? `+${payResult.earnAmt.toLocaleString()}원` : '없음' }}
          </span></span>
          <span class="jitem" style="margin-left:auto">카드 <span>{{ payResult?.cardPct ?? 0 }}%</span></span>
        </div>

        <!-- 저장 -->
        <div class="save-row">
          <div>
            <div class="save-total-lbl">최종 결제금액</div>
            <div class="save-total-amt">{{ totalAfterDiscount.toLocaleString() }}원</div>
            <div v-if="payResult?.earnEligible" class="save-total-sub">
              적립 +{{ payResult.earnAmt.toLocaleString() }}원
            </div>
          </div>
          <button class="save-btn" :disabled="!cart.items.length || saving" @click="openSaveModal">
            저장 확정
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- ── 저장 확정 모달 ── -->
  <div class="mo" :class="{ open: showSaveModal }" @click.self="showSaveModal = false">
    <div class="mo-box">
      <div class="mo-ttl">판매를 저장할까요?</div>
      <div class="mo-sub">저장하면 재고·적립금·서비스가 자동 반영됩니다.</div>
      <div class="mo-sum">
        <div class="mo-sec"><span>채널</span><span class="mo-cnt">{{ cart.channel }}</span></div>
        <div class="mo-sec"><span>고객</span><span class="mo-cnt">{{ customer?.name || '비회원' }}</span></div>
        <div class="mo-item" v-for="item in cart.items" :key="item.id">
          <span>{{ item.name }} ×{{ item.qty }}</span>
          <span class="mo-qty">{{ (lineAmounts.get(item.id) || 0).toLocaleString() }}원</span>
        </div>
        <div class="mo-sec"><span>소계</span><span class="mo-cnt">{{ priceResult.subtotal.toLocaleString() }}원</span></div>
        <div class="mo-sec"><span>결제</span><span class="mo-cnt">{{ payMethod }} {{ totalAfterDiscount.toLocaleString() }}원</span></div>
        <div v-if="milesUsed" class="mo-sec">
          <span>마일리지 사용</span><span class="mo-cnt">{{ milesUsed.toLocaleString() }}원</span>
        </div>
        <div v-if="payResult?.earnEligible" class="mo-sec">
          <span>적립</span><span class="mo-cnt">+{{ payResult.earnAmt.toLocaleString() }}원</span>
        </div>
        <template v-if="svcBundles.length">
          <div class="mo-sec"><span>서비스</span></div>
          <div v-for="svc in svcBundles" :key="svc.kind" class="mo-item give">
            <span>{{ svc.kind }}</span>
            <span class="mo-qty g">{{ svcSelectedCount(svc) }}/{{ svc.qty }}</span>
          </div>
        </template>
      </div>
      <div class="mo-acts">
        <button class="mo-btn" @click="showSaveModal = false">취소</button>
        <button class="mo-btn pr" @click="confirmSave" :disabled="saving">
          {{ saving ? '저장 중...' : '저장 확정' }}
        </button>
      </div>
    </div>
  </div>

  <!-- ── 서비스 확정 모달 ── -->
  <div class="mo" :class="{ open: showSvcModal }" @click.self="showSvcModal = false">
    <div class="mo-box">
      <div class="mo-ttl">서비스 확정</div>
      <div class="mo-sub">선택한 내용대로 확정합니다.</div>
      <div class="mo-sum" v-if="svcModalTarget">
        <div v-for="(bundle, bi) in svcModalTarget.bundles" :key="bi">
          <div class="mo-sec">
            <span>{{ bundle.bundleType === 'SET3' ? `묶음${bundle.bundleIndex}` : `나머지${bundle.bundleIndex}` }}</span>
            <span class="mo-cnt">{{ bundle.chosenGroup === 'set2' ? '입호흡 이벤트 1병' : `코일/악세사리 ${bundle.slots.length}개` }}</span>
          </div>
          <div v-for="(slot, si) in bundle.slots" :key="si"
               class="mo-item" :class="slot.selectedProduct ? 'give' : 'unpaid'">
            <span>{{ slot.selectedProduct?.name || '미선택' }}</span>
            <span class="mo-qty" :class="slot.selectedProduct ? 'g' : 'u'">
              {{ slot.selectedProduct ? '지급' : '미지급' }}
            </span>
          </div>
        </div>
      </div>
      <div class="mo-acts">
        <button class="mo-btn" @click="showSvcModal = false">다시 선택</button>
        <button class="mo-btn bl" @click="showSvcModal = false">확인</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { calcPrice } from '@/engines/priceEngine'
import { calcService, applyGroupChoice } from '@/engines/serviceEngine'
import { calcPayment } from '@/engines/paymentEngine'
import api from '@/api'

const auth = useAuthStore()
const cart = useCartStore()

// ── 상품 ─────────────────────────────────────
const products  = ref([])
const activeTab = ref('all')
const prodSearch = ref('')

const TABS = [
  { key: 'all',                   label: '전체'    },
  { key: '입호흡 이벤트',         label: '입이벤트' },
  { key: '입호흡 일반',           label: '입일반'   },
  { key: '입호흡 일반(할인제외)', label: '입제외'   },
  { key: '폐호흡 이벤트',         label: '폐이벤트' },
  { key: '폐호흡 일반',           label: '폐일반'   },
  { key: 'dev',                   label: '기기'    },
  { key: 'coil',                  label: '코일'    },
  { key: '악세사리',              label: '악세사리' },
]
const DEV_CATS  = ['입호흡 기기','폐호흡 기기','입호흡 기기(단일가)','폐호흡 기기(단일가)']
const COIL_CATS = ['입호흡 코일','입호흡 코일(고가)','폐호흡 코일','폐호흡 코일(고가)']
const isEventCat   = (c) => c.includes('이벤트')
const isHighPodCat = (c) => c.includes('(고가)')
const isExclCat    = (c) => c.includes('(할인제외)')

function matchesTab(p, tab) {
  if (tab === 'all')  return true
  if (tab === 'dev')  return DEV_CATS.includes(p.category)
  if (tab === 'coil') return COIL_CATS.includes(p.category)
  return p.category === tab
}

const filteredProducts = computed(() => {
  const q = prodSearch.value.toLowerCase()
  return products.value.filter(p =>
    matchesTab(p, activeTab.value) && (!q || p.name.toLowerCase().includes(q))
  )
})

const cartQtyMap = computed(() => {
  const m = {}
  for (const i of cart.items) m[i.id] = i.qty
  return m
})

const stockColor = (stock) => {
  if (!stock || stock.qty_available <= 0) return 'var(--re)'
  if (stock.qty_available <= 3)           return 'var(--ye)'
  return 'var(--gr)'
}

// ── 고객 ─────────────────────────────────────
const custQ    = ref('')
const customer = ref(null)

async function searchCustomer() {
  if (!custQ.value.trim()) return
  try {
    const res = await api.get('/customers/search', { params: { q: custQ.value.trim() } })
    customer.value = res.data?.length ? res.data[0] : null
    if (!customer.value) alert('고객을 찾을 수 없습니다')
  } catch (e) { console.error(e) }
}

function clearCustomer() {
  customer.value = null
  custQ.value = ''
  milesUsed.value = 0
}

// ── 장바구니 ──────────────────────────────────
function addToCart(product) {
  cart.addItem({
    id: product.id,
    category: product.category,
    name: product.name,
    normalPrice: product.normal_price,
    deviceDiscountPrice: product.device_discount_price,
    qty: 1,
  })
}

// ── 가격 계산 ─────────────────────────────────
const priceResult = computed(() =>
  calcPrice(cart.items.map(i => ({
    id: i.id, category: i.category, name: i.name,
    normalPrice: i.normalPrice, deviceDiscountPrice: i.deviceDiscountPrice, qty: i.qty,
  })))
)
const lineAmounts = computed(() => priceResult.value.lineAmounts)
const totalAfterDiscount = computed(() => Math.max(0, priceResult.value.subtotal - (cart.discount || 0)))

// ── 결제 ─────────────────────────────────────
const payMethod = ref('이체')
const milesUsed = ref(0)

const availablePayMethods = computed(() =>
  cart.channel === '매장' ? ['이체', '현금', '카드'] : ['이체', '현금']
)

watch(() => cart.channel, (ch) => {
  if (ch !== '매장' && payMethod.value === '카드') payMethod.value = '이체'
  milesUsed.value = 0
})

function useAllMiles() {
  if (!customer.value) return
  milesUsed.value = Math.floor(
    Math.min(customer.value.mileage_balance, totalAfterDiscount.value) / 10
  ) * 10
}

const payResult = computed(() => {
  if (!priceResult.value.subtotal) return null
  const total = totalAfterDiscount.value
  const miles = milesUsed.value || 0
  return calcPayment({
    cash:          payMethod.value !== '카드' ? total - miles : 0,
    card:          payMethod.value === '카드' ? total - miles : 0,
    milesUsed:     miles,
    milesBalance:  customer.value?.mileage_balance || 0,
    priceResult:   priceResult.value,
    services:      svcBundles.value,
    channel:       cart.channel,
  })
})

// ── 서비스 ────────────────────────────────────
const svcBundles = ref([])
const svcEligible = computed(() => payResult.value?.svcEligible ?? true)
const serviceResult = computed(() =>
  calcService(priceResult.value, cart.channel, svcEligible.value)
)

const cartKey = computed(() =>
  cart.items.map(i => `${i.id}:${i.qty}`).join(',') + '|' + cart.channel
)
watch(cartKey, () => {
  svcBundles.value = JSON.parse(JSON.stringify(serviceResult.value))
}, { immediate: true })

// 슬롯 검색
const slotQueries = ref({})
const activeSlot  = ref(null)

function slotFilteredProducts(slot, si, bi, sloti) {
  const q = (slotQueries.value[`${si}-${bi}-${sloti}`] || '').toLowerCase()
  return products.value.filter(p =>
    slot.categories.includes(p.category) && (!q || p.name.toLowerCase().includes(q))
  )
}
function onSlotBlur() { setTimeout(() => { activeSlot.value = null }, 150) }

function selectSlotProduct(si, bi, sloti, product) {
  svcBundles.value[si].bundles[bi].slots[sloti].selectedProduct = {
    id: product.id, name: product.name,
    category: product.category, normalPrice: product.normal_price,
  }
  slotQueries.value[`${si}-${bi}-${sloti}`] = ''
  activeSlot.value = null
}
function clearSlotProduct(si, bi, sloti) {
  svcBundles.value[si].bundles[bi].slots[sloti].selectedProduct = null
}
function chooseGroup(si, bi, group) {
  svcBundles.value[si].bundles[bi] = applyGroupChoice(svcBundles.value[si].bundles[bi], group)
}

// 서비스 UI 헬퍼
function svcSelectedCount(svc) {
  let n = 0
  for (const b of svc.bundles) for (const s of b.slots) if (s.selectedProduct) n++
  return n
}
function svcTotalSlots(svc) {
  return svc.bundles.reduce((s, b) => s + b.slots.length, 0)
}
function svcChips(svc) {
  const sel = svcSelectedCount(svc), total = svcTotalSlots(svc)
  const chips = []
  if (sel > 0)       chips.push({ label: `지급 ${sel}`, cls: 'g' })
  if (sel < total)   chips.push({ label: `미선택 ${total - sel}`, cls: 'u' })
  return chips
}
function svcBtnClass(svc) {
  if (!svcEligible.value) return 'blocked'
  const sel = svcSelectedCount(svc), total = svcTotalSlots(svc)
  if (total === 0) return 'zero'
  return sel === total ? 'full' : sel > 0 ? 'partial' : 'zero'
}

// ── 모달 ─────────────────────────────────────
const showSaveModal  = ref(false)
const showSvcModal   = ref(false)
const svcModalTarget = ref(null)
const saving         = ref(false)

function openSaveModal() {
  if (!cart.items.length) return
  showSaveModal.value = true
}
function openSvcModal(svc) {
  svcModalTarget.value = svc
  showSvcModal.value = true
}

// ── 저장 ─────────────────────────────────────
async function confirmSave() {
  saving.value = true
  try {
    const pr = priceResult.value
    const lm = lineAmounts.value
    const total = totalAfterDiscount.value
    const miles = milesUsed.value || 0
    const pr2 = payResult.value

    const lines = cart.items.map(i => ({
      product_id:    i.id,
      qty:           i.qty,
      normal_price:  i.normalPrice,
      applied_price: lm.get(i.id) ?? i.normalPrice * i.qty,
      line_type:     '판매',
      service_type:  '해당없음',
    }))

    const payments = [{ method: payMethod.value, amount: total - miles }]
    if (miles > 0) payments.push({ method: '마일리지', amount: miles })

    const services = svcBundles.value.map(svc => {
      const names = []
      for (const b of svc.bundles) for (const s of b.slots) if (s.selectedProduct) names.push(s.selectedProduct.name)
      const delivered = names.length
      return {
        service_kind:    svc.kind,
        total_qty:       svc.qty,
        delivered_qty:   delivered,
        undelivered_qty: svc.qty - delivered,
        selected_item:   names.join(', ') || null,
        delivery_status: delivered === 0 ? '미지급' : delivered < svc.qty ? '부분지급' : '전체지급',
      }
    })

    await api.post('/transactions', {
      store_id:         auth.staff?.store_id || 1,
      channel:          cart.channel,
      customer_id:      customer.value?.id || null,
      subtotal:         pr.subtotal,
      discount_amount:  cart.discount || 0,
      total_amount:     total,
      mileage_used:     miles,
      mileage_earned:   pr2?.earnAmt || 0,
      payment_nature:   pr2?.nature || '현금/이체',
      card_ratio_pct:   pr2?.cardPct || 0,
      service_eligible: pr2?.svcEligible ?? true,
      earn_eligible:    pr2?.earnEligible ?? false,
      tx_color:         '정상',
      lines,
      payments,
      services,
    })

    showSaveModal.value = false
    cart.clearCart()
    customer.value   = null
    custQ.value      = ''
    milesUsed.value  = 0
    payMethod.value  = '이체'
    svcBundles.value = []
    alert('저장 완료!')
  } catch (e) {
    console.error(e)
    alert('저장 실패: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

// ── 초기 로드 ─────────────────────────────────
onMounted(async () => {
  try {
    const res = await api.get('/products', { params: { store_id: auth.staff?.store_id || 1 } })
    products.value = res.data
  } catch (e) { console.error('상품 로드 실패:', e) }
})
</script>

<style scoped>
.pos-wrap { display:flex; flex:1; height:100%; overflow:hidden; }

/* 왼쪽 */
.pos-left { display:flex; flex-direction:column; flex:1; min-width:0; overflow:hidden; border-right:1px solid var(--bd); }

/* 고객 바 */
.cust-bar { padding:8px 12px; border-bottom:1px solid var(--bd); background:var(--bg2); flex-shrink:0; }
.cust-row { display:flex; align-items:center; gap:6px; }
.cust-lbl { font-size:10px; color:var(--tx2); font-weight:600; font-family:var(--mono); min-width:38px; }
.cust-inp { flex:1; border:1px solid var(--bd2); border-radius:6px; padding:5px 9px; font-size:12px; font-family:var(--sans); color:var(--tx); background:var(--bg); outline:none; }
.cust-inp:focus { border-color:var(--ac2); }
.cust-info { margin-top:6px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px; padding:7px 10px; display:none; }
.cust-info.show { display:flex; align-items:center; gap:8px; }
.cust-av { width:28px; height:28px; border-radius:50%; background:var(--ac2); display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:#fff; flex-shrink:0; }
.cust-clear { cursor:pointer; color:var(--tx3); font-size:14px; line-height:1; padding:2px; }

/* 상품 */
.prod-area { flex:1; overflow-y:auto; padding:8px 10px; }
.cat-tabs { display:flex; gap:3px; flex-wrap:wrap; }
.ctab { padding:3px 9px; border-radius:20px; border:1px solid var(--bd2); background:var(--bg); cursor:pointer; font-size:11px; color:var(--tx2); }
.ctab.on { background:var(--ac2); color:#fff; border-color:var(--ac2); }
.prod-search { border:1px solid var(--bd2); border-radius:6px; padding:4px 8px; font-size:11px; font-family:var(--sans); color:var(--tx); background:var(--bg); outline:none; width:110px; flex-shrink:0; margin-left:6px; }
.prod-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:5px; }
.pb { background:var(--bg); border:1px solid var(--bd); border-radius:5px; padding:5px; cursor:pointer; text-align:left; transition:all .12s; }
.pb:hover { border-color:var(--ac); background:#fff8f6; }
.pb.pb-active { border-color:var(--ac2); background:#eff6ff; }
.pn { font-size:11px; font-weight:600; line-height:1.25; margin-bottom:1px; }
.pt { font-size:9px; color:var(--tx3); }
.pp { font-family:var(--mono); font-size:9px; color:var(--tx2); margin-top:2px; display:flex; align-items:center; gap:3px; flex-wrap:wrap; }
.badge { font-size:8px; padding:1px 3px; border-radius:2px; font-family:var(--mono); font-weight:600; white-space:nowrap; }
.badge.ev { background:var(--ac); color:#fff; }
.badge.hp { background:var(--pu); color:#fff; }
.badge.ex { background:var(--ye); color:#fff; }
.badge.cart-b { background:var(--ac2); color:#fff; }
.prod-empty { grid-column:1/-1; text-align:center; padding:24px 0; color:var(--tx3); font-size:12px; }

/* 오른쪽 */
.pos-right { width:580px; flex-shrink:0; display:flex; flex-direction:column; overflow:hidden; }
.ch-bar { padding:6px 10px; border-bottom:1px solid var(--bd); background:var(--bg2); flex-shrink:0; display:flex; align-items:center; gap:6px; }
.ch-lbl { font-size:10px; color:var(--tx2); font-weight:600; font-family:var(--mono); }
.tab { padding:3px 9px; border-radius:20px; border:1px solid var(--bd2); background:var(--bg); cursor:pointer; font-size:11px; color:var(--tx2); }
.tab.on { background:var(--ac); color:#fff; border-color:var(--ac); }

/* 바디 */
.pos-body { display:flex; flex-direction:column; flex:1; min-height:0; overflow:hidden; }

/* 장바구니 */
.cart-section { flex-shrink:0; max-height:200px; overflow-y:auto; border-bottom:1px solid var(--bd); padding:0 10px 4px; }
.cart-hd { display:flex; align-items:center; justify-content:space-between; padding:6px 0 4px; position:sticky; top:0; background:var(--bg2); }
.cart-hd-title { font-size:12px; font-weight:600; }
.cart-empty { text-align:center; padding:14px 0; color:var(--tx3); font-size:12px; }
.ci { display:flex; align-items:center; gap:6px; padding:6px 0; border-bottom:1px solid var(--bd); }
.ci:last-child { border-bottom:none; }
.ci-nm { font-size:12px; font-weight:500; }
.ci-tg { font-size:9px; color:var(--tx3); font-family:var(--mono); display:block; margin-top:1px; }
.qc { display:flex; align-items:center; gap:3px; }
.qb { width:20px; height:20px; border:1px solid var(--bd2); border-radius:4px; background:var(--bg); cursor:pointer; font-size:12px; display:flex; align-items:center; justify-content:center; }
.qb:hover { border-color:var(--ac); color:var(--ac); }
.qn { font-family:var(--mono); font-size:12px; font-weight:600; min-width:16px; text-align:center; }
.cp { font-family:var(--mono); font-size:12px; font-weight:600; min-width:60px; text-align:right; }
.cdl { color:var(--tx3); cursor:pointer; font-size:13px; padding:2px; }
.cdl:hover { color:var(--re); }

/* 서비스 */
.svc-section { flex:1; min-height:0; overflow-y:auto; padding:0 10px 4px; }
.svc-hd { display:flex; align-items:center; justify-content:space-between; padding:6px 0 4px; position:sticky; top:0; background:var(--bg2); }
.svc-hd-title { font-size:12px; font-weight:600; }
.svc-badge { font-size:10px; padding:2px 7px; border-radius:4px; background:#ffedd5; color:#9a3412; }
.svc-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:24px 0; color:var(--tx3); font-size:11px; text-align:center; gap:5px; }
.svc-bundle { border:0.5px solid #ffd5c4; border-radius:7px; background:#fff8f6; padding:8px 10px; margin-bottom:6px; }
.sb-head { display:flex; align-items:center; gap:6px; margin-bottom:6px; }
.sb-tag { font-size:10px; padding:1px 5px; border-radius:3px; }
.st-set3 { background:#E6F1FB; color:#0C447C; }
.st-rem  { background:#F1EFE8; color:#5F5E5A; }
.choice-row { display:flex; gap:4px; margin-bottom:6px; }
.c-btn { flex:1; padding:5px; border-radius:5px; border:0.5px solid var(--bd2); background:var(--bg3); font-size:10px; cursor:pointer; color:var(--tx2); text-align:center; line-height:1.4; }
.c-btn.on { border-color:var(--ac2); background:#eff6ff; color:var(--ac2); font-weight:500; }
.svc-prod-list { display:flex; flex-direction:column; gap:3px; }
.svc-prod-row { display:flex; align-items:center; gap:5px; padding:5px 7px; border:0.5px solid var(--bd); border-radius:5px; background:var(--bg2); }
.svc-prod-row.sg    { border-color:#1D9E75; background:#F0FDF4; }
.svc-prod-row.szero { background:#FAFAF8; }
.sp-nm  { font-size:11px; font-weight:500; }
.sp-cat { font-size:9px; color:var(--tx3); }
.slot-search { width:100%; border:0.5px solid var(--bd2); border-radius:4px; padding:3px 6px; font-size:11px; font-family:var(--sans); color:var(--tx); background:var(--bg); outline:none; }
.slot-search:focus { border-color:var(--ac2); }
.slot-dropdown { position:absolute; top:100%; left:0; right:0; z-index:50; background:var(--bg2); border:1px solid var(--bd2); border-radius:5px; box-shadow:0 4px 12px rgba(0,0,0,.12); max-height:160px; overflow-y:auto; }
.slot-opt { display:flex; align-items:center; gap:6px; padding:5px 8px; font-size:11px; cursor:pointer; border-bottom:0.5px solid var(--bd); }
.slot-opt:last-child { border-bottom:none; }
.slot-opt:hover { background:var(--bg3); }
.svc-action { display:flex; align-items:center; justify-content:space-between; padding:6px 0 2px; margin-top:4px; }
.svc-chips { display:flex; gap:4px; flex-wrap:wrap; }
.schip { font-size:9px; padding:1px 5px; border-radius:3px; font-weight:500; font-family:var(--mono); }
.schip.g { background:#E1F5EE; color:#085041; }
.schip.u { background:#FCEBEB; color:#A32D2D; }
.svc-confirm-btn { padding:6px 14px; border-radius:6px; border:none; font-size:11px; font-weight:600; cursor:pointer; color:#fff; }
.svc-confirm-btn.full    { background:var(--gr); }
.svc-confirm-btn.partial { background:var(--ac2); }
.svc-confirm-btn.zero    { background:#888780; }
.svc-confirm-btn.blocked { background:var(--bd2); color:var(--tx3); cursor:not-allowed; }

/* 하단 */
.pos-bottom { flex-shrink:0; border-top:2px solid var(--bd2); background:var(--bg2); }
.calc-bar { padding:5px 10px; border-bottom:1px solid var(--bd); background:var(--bg); display:none; align-items:center; flex-wrap:nowrap; }
.calc-bar.show { display:flex; }
.cb-seg { display:flex; align-items:baseline; gap:3px; padding:0 8px; border-right:1px solid var(--bd); }
.cb-seg:first-child { padding-left:0; }
.cb-seg:last-child  { border-right:none; }
.cb-lbl  { font-size:9px; color:var(--tx3); font-family:var(--mono); }
.cb-val  { font-family:var(--mono); font-size:11px; font-weight:600; }
.cb-rule { font-size:9px; font-family:var(--mono); color:var(--tx2); }
.pay-row { padding:6px 10px; display:flex; align-items:center; gap:7px; border-bottom:0.5px solid var(--bd); }
.pm-btns { display:flex; gap:3px; }
.pm-btn { padding:5px 10px; border:1.5px solid var(--bd); border-radius:5px; cursor:pointer; font-size:11px; font-weight:600; background:var(--bg); color:var(--tx2); }
.pm-btn.on { border-color:var(--ac2); background:#eff6ff; color:var(--ac2); }
.pts-lbl { font-size:10px; color:var(--tx3); font-family:var(--mono); margin-left:8px; }
.pts-inp { border:1px solid var(--bd2); border-radius:5px; padding:4px 6px; font-size:11px; font-family:var(--mono); color:var(--tx); background:var(--bg); outline:none; width:80px; }
.pts-inp:focus    { border-color:var(--ac2); }
.pts-inp:disabled { opacity:.4; }
.judge-row { padding:3px 10px; display:flex; gap:8px; flex-wrap:wrap; border-bottom:0.5px solid var(--bd); }
.jitem { font-size:10px; font-family:var(--mono); color:var(--tx2); }
.jitem .ok { color:var(--gr); font-weight:600; }
.jitem .no { color:var(--re); font-weight:600; }
.jitem .bl { color:var(--ac2); font-weight:600; }
.save-row { padding:8px 10px; display:flex; align-items:center; justify-content:space-between; gap:10px; }
.save-total-lbl { font-size:10px; color:var(--tx3); font-family:var(--mono); }
.save-total-amt { font-family:var(--mono); font-size:22px; font-weight:700; color:var(--ac); line-height:1.1; }
.save-total-sub { font-size:10px; color:var(--gr); font-family:var(--mono); margin-top:1px; }
.save-btn { padding:10px 22px; background:var(--ac); color:#fff; border:none; border-radius:var(--r); font-size:13px; font-weight:700; cursor:pointer; }
.save-btn:hover:not(:disabled) { background:#d4481a; }
.save-btn:disabled { opacity:.4; cursor:not-allowed; }

/* 모달 */
.mo { position:fixed; inset:0; background:rgba(0,0,0,.42); z-index:100; display:none; align-items:center; justify-content:center; }
.mo.open { display:flex; }
.mo-box { background:var(--bg2); border-radius:12px; padding:20px 22px; min-width:360px; max-width:420px; }
.mo-ttl { font-size:14px; font-weight:700; margin-bottom:4px; }
.mo-sub { font-size:12px; color:var(--tx2); margin-bottom:12px; line-height:1.6; }
.mo-sum { background:var(--bg); border-radius:7px; padding:10px 12px; margin-bottom:12px; max-height:300px; overflow-y:auto; }
.mo-sec { font-size:11px; font-weight:500; padding:5px 0 3px; border-top:0.5px solid var(--bd); margin-top:3px; display:flex; align-items:center; justify-content:space-between; }
.mo-sec:first-child { border-top:none; padding-top:0; margin-top:0; }
.mo-cnt { font-family:var(--mono); font-size:11px; }
.mo-item { display:flex; align-items:center; justify-content:space-between; padding:3px 7px; border-radius:4px; margin-bottom:2px; font-size:12px; }
.mo-item.give   { background:#F0FDF4; }
.mo-item.unpaid { background:#FFF5F5; }
.mo-qty   { font-family:var(--mono); font-size:12px; font-weight:500; }
.mo-qty.g { color:var(--gr); }
.mo-qty.u { color:var(--re); }
.mo-acts { display:flex; gap:6px; justify-content:flex-end; margin-top:12px; }
.mo-btn    { padding:7px 14px; border-radius:6px; border:1px solid var(--bd2); background:var(--bg); cursor:pointer; font-size:12px; font-family:var(--sans); }
.mo-btn.pr { background:var(--ac);  color:#fff; border-color:var(--ac);  }
.mo-btn.bl { background:var(--ac2); color:#fff; border-color:var(--ac2); }

::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--bd2); border-radius:10px; }
</style>
