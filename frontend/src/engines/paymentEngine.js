/**
 * paymentEngine.js — VapeERP 결제 성격 판정 & 적립 엔진 v4
 *
 * ── 채널별 확정 정책 ────────────────────────────────────
 * 매장:       현금·이체·카드·마일리지 모두 가능
 * 배달·택배:  현금·이체만 가능. 카드·마일리지 불가
 *
 * ── 결제 성격 판정 ──────────────────────────────────────
 * 카드 비중 = 카드금액 ÷ (현금+이체+카드+마일리지) × 100
 *   0%     → 현금/이체
 *   1~20%  → 현금/이체 성격 (서비스 가능)
 *   >20%   → 카드 (서비스 불가)
 *   전액마일리지 → 현금/이체 성격 (서비스 가능, 적립 없음, 매장만)
 *
 * ── 적립 조건 (AND) ─────────────────────────────────────
 * ① 채널 = 매장
 * ② 마일리지 사용 = 0
 * ③ 고가팟 특수 서비스 거래 아님 (earnBlock)
 * ④ 적립 대상 품목(액상·기기) 포함
 *
 * ── 적립 계산 (10원 단위 버림) ──────────────────────────
 * 현금/이체: floor(최종결제금액 × 0.05 / 10) × 10
 * 카드:      floor((액상금액+기기금액) × 0.05 / 10) × 10
 */

const CHANNEL_POLICY = {
  '매장': { cardOk: true,  milesOk: true,  earnOk: true  },
  '배달': { cardOk: false, milesOk: false, earnOk: false },
  '택배': { cardOk: false, milesOk: false, earnOk: false },
};

/**
 * calcPayment({ cash, card, milesUsed, milesBalance,
 *               priceResult, services, channel })
 */
export function calcPayment({ cash = 0, card = 0, milesUsed = 0, milesBalance = 0,
                               priceResult, services, channel }) {
  const { subtotal, liquidPrice, devicePrice } = priceResult;
  const policy = CHANNEL_POLICY[channel] ?? CHANNEL_POLICY['매장'];

  // ── 채널별 차단 ─────────────────────────────────────
  const cardBlocked  = !policy.cardOk  && card > 0;
  const milesBlocked = !policy.milesOk && milesUsed > 0;

  // 실제 적용 금액 (차단된 수단은 0 처리)
  const cardFinal  = policy.cardOk  ? (card  ?? 0) : 0;
  const maxMiles   = policy.milesOk ? Math.min(milesBalance, subtotal) : 0;
  const milesFloor = Math.floor(maxMiles / 10) * 10;
  const milesFinal = Math.min(Math.floor((milesUsed ?? 0) / 10) * 10, milesFloor);
  const cashFinal  = cash ?? 0;

  const totalToPay = subtotal - milesFinal;

  // ── 카드 비중 ────────────────────────────────────────
  const totalInput = cashFinal + cardFinal + milesFinal;
  const cardPct    = totalInput > 0 ? cardFinal / totalInput * 100 : 0;

  // ── 결제 성격 판정 ───────────────────────────────────
  let nature;
  if (cardFinal === 0 && milesFinal === 0) {
    nature = '현금/이체';
  } else if (cardFinal === 0) {
    nature = milesFinal >= subtotal ? '마일리지 전액' : '현금/이체+마일리지';
  } else if (cardPct <= 20) {
    nature = '현금/이체 성격 (카드 20% 이하)';
  } else {
    nature = '카드';
  }

  // ── 서비스 자격 ─────────────────────────────────────
  // 배달·택배는 카드 없으므로 항상 현금/이체 성격 → 서비스 가능
  const svcEligible = !nature.startsWith('카드');

  // ── 결제 합산 검증 ───────────────────────────────────
  const isBalanceOk = Math.abs((cashFinal + cardFinal + milesFinal) - subtotal) <= 10;

  // ── 적립 판정 ────────────────────────────────────────
  let earnEligible = false, earnReason = '', earnAmt = 0;
  const hasEarnBlock = (services ?? []).some(s => s.earnBlock);
  const earnBase     = liquidPrice + devicePrice;

  if (!policy.earnOk) {
    earnReason = `${channel} 채널 → 적립 없음`;
  } else if (milesFinal > 0) {
    earnReason = '마일리지 사용 → 적립 없음';
  } else if (hasEarnBlock) {
    earnReason = '고가팟 특수 서비스 거래 → 적립 없음';
  } else if (earnBase <= 0) {
    earnReason = '적립 대상 품목 없음 (코일·악세사리만)';
  } else {
    earnEligible = true;
    if (nature === '카드') {
      earnAmt    = Math.floor(earnBase * 0.05 / 10) * 10;
      earnReason = `카드 결제 · 액상+기기 기준 5% = ${earnAmt.toLocaleString()}원`;
    } else {
      earnAmt    = Math.floor(totalToPay * 0.05 / 10) * 10;
      earnReason = `현금/이체 기준 5% = ${earnAmt.toLocaleString()}원`;
    }
  }

  return {
    nature,
    cardPct:        Math.round(cardPct),
    svcEligible,
    earnEligible,
    earnReason,
    earnAmt,
    totalToPay,
    milesFinal,
    isBalanceOk,
    cardBlocked,    // UI에서 카드 입력란 비활성화 신호
    milesBlocked,   // UI에서 마일리지 입력란 비활성화 신호
  };
}
