import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { calcPrice } from '@/engines/priceEngine'
import { calcService } from '@/engines/serviceEngine'
import { calcPayment } from '@/engines/paymentEngine'

export const useCartStore = defineStore('cart', () => {
  // ── 상태 ──────────────────────────────────────────
  const items    = ref([])   // 장바구니 상품 목록
  const channel  = ref('매장') // 매장 | 배달 | 택배
  const customer = ref(null)  // 선택된 고객
  const discount = ref(0)
  const discountReason = ref('')
  const payMethod = ref('이체') // 이체 | 현금 | 카드
  const milesUsed = ref(0)

  // ── 계산 결과 ──────────────────────────────────────
  const priceResult = computed(() => calcPrice(items.value))

  const svcEligible = computed(() => {
    // 카드 결제 비중이 20% 이하일 때만 서비스 가능
    if (payMethod.value === '카드') return false
    return true
  })

  const serviceResult = computed(() =>
    calcService(priceResult.value, channel.value, svcEligible.value)
  )

  const milesBalance = computed(() => customer.value?.mileage_balance || 0)

  const payResult = computed(() => {
    if (!priceResult.value.subtotal) return null
    const cash = payMethod.value === '현금' ? totalAfterDiscount.value - milesUsed.value : 0
    const card = payMethod.value === '카드' ? totalAfterDiscount.value - milesUsed.value : 0
    const transfer = payMethod.value === '이체' ? totalAfterDiscount.value - milesUsed.value : 0
    return calcPayment({
      cash: cash + transfer,
      card,
      milesUsed: milesUsed.value,
      milesBalance: milesBalance.value,
      priceResult: priceResult.value,
      discount: discount.value,
      channel: channel.value,
    })
  })

  const totalAfterDiscount = computed(() =>
    Math.max(0, priceResult.value.subtotal - discount.value)
  )

  // ── 장바구니 조작 ──────────────────────────────────
  function addItem(product) {
    const existing = items.value.find(i => i.id === product.id)
    if (existing) {
      existing.qty++
    } else {
      items.value.push({ ...product, qty: 1 })
    }
  }

  function removeItem(productId) {
    items.value = items.value.filter(i => i.id !== productId)
  }

  function updateQty(productId, delta) {
    const item = items.value.find(i => i.id === productId)
    if (!item) return
    item.qty = Math.max(0, item.qty + delta)
    if (item.qty === 0) removeItem(productId)
  }

  function clearCart() {
    items.value = []
    customer.value = null
    discount.value = 0
    discountReason.value = ''
    milesUsed.value = 0
    payMethod.value = '이체'
  }

  return {
    items, channel, customer, discount, discountReason,
    payMethod, milesUsed, milesBalance,
    priceResult, serviceResult, payResult,
    totalAfterDiscount, svcEligible,
    addItem, removeItem, updateQty, clearCart,
  }
})
