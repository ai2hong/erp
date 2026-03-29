/**
 * priceEngine.js — VapeERP 가격 계산 엔진 v6
 *
 * ── 분류 15종 ──────────────────────────────────────────
 * 액상 6종 / 기기 4종 / 코일 4종 / 악세사리 1종
 *
 * ── 할인제외 처리 규칙 (최종 확정) ─────────────────────
 * 할인제외는 완전히 분리 계산 후 합산.
 * 나머지 액상은 할인제외가 없는 것처럼 그대로 계산 (세트가 유지).
 *
 * 예: 입이벤트2 + 입할인제외1 = 40,000 + 25,000 = 65,000  ✓
 *     입이벤트3 + 입할인제외1 = 50,000 + 25,000 = 75,000  ✓
 *     입이벤트2+입일반1 + 입할인제외1 = 55,000 + 25,000 = 80,000  ✓
 *
 * ── 이벤트+일반 혼합 공식 ──────────────────────────────
 * 총병수 2~3: SET[이벤트][총병수] + 일반qty × 5,000
 * 총병수 4+:  낱개단가
 *
 * ── 기기 연동 할인 ─────────────────────────────────────
 * 연동 할인 가능 대수 = floor(자격병수 / 3) × 2
 */

export const CAT = {
  IN_EV:        '입호흡 이벤트',
  IN_NE:        '입호흡 일반',
  IN_EX:        '입호흡 일반(할인제외)',
  OUT_EV:       '폐호흡 이벤트',
  OUT_NE:       '폐호흡 일반',
  OUT_EX:       '폐호흡 일반(할인제외)',
  IN_DEV:       '입호흡 기기',
  OUT_DEV:      '폐호흡 기기',
  IN_DEV_FIXED: '입호흡 기기(단일가)',
  OUT_DEV_FIXED:'폐호흡 기기(단일가)',
  IN_COIL:      '입호흡 코일',
  IN_COIL_HI:   '입호흡 코일(고가)',
  OUT_COIL:     '폐호흡 코일',
  OUT_COIL_HI:  '폐호흡 코일(고가)',
  ACC:          '악세사리',
};

export const LIQUID_ALL    = new Set([CAT.IN_EV, CAT.IN_NE, CAT.IN_EX, CAT.OUT_EV, CAT.OUT_NE, CAT.OUT_EX]);
export const LIQUID_EXCL   = new Set([CAT.IN_EX, CAT.OUT_EX]);
export const DEVICE_LINKED = new Set([CAT.IN_DEV, CAT.OUT_DEV]);
export const DEVICE_FIXED  = new Set([CAT.IN_DEV_FIXED, CAT.OUT_DEV_FIXED]);
export const DEVICE_ALL    = new Set([...DEVICE_LINKED, ...DEVICE_FIXED]);
export const HIGH_POD_ALL  = new Set([CAT.IN_COIL_HI, CAT.OUT_COIL_HI]);
export const EARN_TARGET   = new Set([...LIQUID_ALL, ...DEVICE_ALL]);

const SET_PRICE = {
  [CAT.IN_EV]:  { 1: 20000, 2: 40000, 3: 50000 },
  [CAT.IN_NE]:  { 1: 25000, 2: 50000, 3: 65000 },
  [CAT.OUT_EV]: { 1: 25000, 2: 45000 },
  [CAT.OUT_NE]: { 1: 30000, 2: 55000 },
};
const UNIT = {
  [CAT.IN_EV]:  { n: 16500, b: 16000 },
  [CAT.IN_NE]:  { n: 21500, b: 21000 },
  [CAT.OUT_EV]: { n: 22500, b: 22000 },
  [CAT.OUT_NE]: { n: 27500, b: 27000 },
};
const MIX_EXTRA = 5000;

const unitKey = (n) => n >= 10 ? 'b' : 'n';

function singleSetPrice(cat, qty) {
  const t = SET_PRICE[cat];
  if (!t) return 0;
  if (t[qty] !== undefined) return t[qty];
  const r = unitKey(qty);
  return (UNIT[cat]?.[r] ?? 0) * qty;
}
function sumQty(items, cat) {
  return items.filter(c => c.category === cat).reduce((s, c) => s + c.qty, 0);
}
function sumQtySet(items, catSet) {
  return items.filter(c => catSet.has(c.category)).reduce((s, c) => s + c.qty, 0);
}
function safeDevicePrice(item) {
  const d = item.deviceDiscountPrice;
  return (d && d > 0 && d < item.normalPrice) ? d : item.normalPrice;
}
function calcUnitSum(qInEv, qInNe, qOutEv, qOutNe, total) {
  const r = unitKey(total);
  return qInEv  * (UNIT[CAT.IN_EV]?.[r]  ?? 0)
       + qInNe  * (UNIT[CAT.IN_NE]?.[r]  ?? 0)
       + qOutEv * (UNIT[CAT.OUT_EV]?.[r] ?? 0)
       + qOutNe * (UNIT[CAT.OUT_NE]?.[r] ?? 0);
}
function linkedDiscountMax(qualifyQty) {
  return Math.floor(qualifyQty / 3) * 2;
}
function fmt(n) { return n.toLocaleString() + '원'; }


export function calcPrice(cartItems) {
  const liquids     = cartItems.filter(c => LIQUID_ALL.has(c.category));
  const devLinked   = cartItems.filter(c => DEVICE_LINKED.has(c.category));
  const devFixed    = cartItems.filter(c => DEVICE_FIXED.has(c.category));
  const others      = cartItems.filter(c => !LIQUID_ALL.has(c.category) && !DEVICE_ALL.has(c.category));

  // ── 할인제외 분리 ─────────────────────────────────────
  const exclItems   = liquids.filter(c => LIQUID_EXCL.has(c.category));
  const normalItems = liquids.filter(c => !LIQUID_EXCL.has(c.category));

  // 할인제외 가격: 항상 정상가×수량
  const exclPrice = exclItems.reduce((s, c) => s + c.normalPrice * c.qty, 0);

  // 일반 액상 수량 (할인제외 제외)
  const qInEv  = sumQty(cartItems, CAT.IN_EV);
  const qInNe  = sumQty(cartItems, CAT.IN_NE);
  const qOutEv = sumQty(cartItems, CAT.OUT_EV);
  const qOutNe = sumQty(cartItems, CAT.OUT_NE);
  const qExcl  = exclItems.reduce((s, c) => s + c.qty, 0);
  const qIn    = qInEv + qInNe;
  const qOut   = qOutEv + qOutNe;
  const qNormal = qIn + qOut;   // 할인제외 제외한 일반 액상
  const qTotal  = qNormal + qExcl; // 전체 액상 (기기 자격 병수)

  const steps = [];
  let ruleLabel = '';
  let normalPrice = 0;

  if (qExcl > 0) steps.push({ label: '할인제외 (정상가 고정)', value: fmt(exclPrice) });

  // ── 일반 액상 가격 계산 (할인제외와 완전히 독립) ──────
  // 규칙: 할인제외가 있어도 나머지는 세트가/낱개단가 그대로 적용
  if (qNormal > 0) {
    if (qIn > 0 && qOut > 0) {
      // 입+폐 혼합
      if (qNormal <= 2) {
        normalPrice = (SET_PRICE[CAT.IN_EV]?.[1]  ?? 0) * qInEv
                    + (SET_PRICE[CAT.IN_NE]?.[1]  ?? 0) * qInNe
                    + (SET_PRICE[CAT.OUT_EV]?.[1] ?? 0) * qOutEv
                    + (SET_PRICE[CAT.OUT_NE]?.[1] ?? 0) * qOutNe;
        ruleLabel = `입+폐 혼합 2병 → 정상가 합산`;
        steps.push({ label: ruleLabel, value: fmt(normalPrice) });
      } else {
        normalPrice = calcUnitSum(qInEv, qInNe, qOutEv, qOutNe, qNormal);
        ruleLabel = `입+폐 혼합 ${qNormal}병 → 낱개단가`;
        const r = unitKey(qNormal);
        const parts = [];
        if (qInEv)  parts.push(`입이벤트 ${qInEv}×${UNIT[CAT.IN_EV][r].toLocaleString()}`);
        if (qInNe)  parts.push(`입일반 ${qInNe}×${UNIT[CAT.IN_NE][r].toLocaleString()}`);
        if (qOutEv) parts.push(`폐이벤트 ${qOutEv}×${UNIT[CAT.OUT_EV][r].toLocaleString()}`);
        if (qOutNe) parts.push(`폐일반 ${qOutNe}×${UNIT[CAT.OUT_NE][r].toLocaleString()}`);
        steps.push({ label: ruleLabel, value: parts.join(' + ') });
      }
    } else if (qIn > 0) {
      if (qInEv > 0 && qInNe > 0) {
        if (qIn <= 3) {
          const base = singleSetPrice(CAT.IN_EV, qIn);
          normalPrice = base + qInNe * MIX_EXTRA;
          ruleLabel = `입이벤트+일반 혼합 ${qIn}병 → 기준가+추가금`;
          steps.push({ label: ruleLabel, value: `${base.toLocaleString()} + ${qInNe}×5,000` });
        } else {
          normalPrice = calcUnitSum(qInEv, qInNe, 0, 0, qIn);
          ruleLabel = `입이벤트+일반 혼합 ${qIn}병 → 낱개단가`;
          const r = unitKey(qIn);
          steps.push({ label: ruleLabel,
            value: `입이벤트 ${qInEv}×${UNIT[CAT.IN_EV][r].toLocaleString()} + 입일반 ${qInNe}×${UNIT[CAT.IN_NE][r].toLocaleString()}` });
        }
      } else {
        const cat = qInEv > 0 ? CAT.IN_EV : CAT.IN_NE;
        normalPrice = singleSetPrice(cat, qIn);
        ruleLabel = `${cat} ${qIn}병`;
        steps.push({ label: ruleLabel, value: fmt(normalPrice) });
      }
    } else {
      if (qOutEv > 0 && qOutNe > 0) {
        if (qOut <= 3) {
          const base = singleSetPrice(CAT.OUT_EV, qOut);
          normalPrice = base + qOutNe * MIX_EXTRA;
          ruleLabel = `폐이벤트+일반 혼합 ${qOut}병 → 기준가+추가금`;
          steps.push({ label: ruleLabel, value: `${base.toLocaleString()} + ${qOutNe}×5,000` });
        } else {
          normalPrice = calcUnitSum(0, 0, qOutEv, qOutNe, qOut);
          ruleLabel = `폐이벤트+일반 혼합 ${qOut}병 → 낱개단가`;
          const r = unitKey(qOut);
          steps.push({ label: ruleLabel,
            value: `폐이벤트 ${qOutEv}×${UNIT[CAT.OUT_EV][r].toLocaleString()} + 폐일반 ${qOutNe}×${UNIT[CAT.OUT_NE][r].toLocaleString()}` });
        }
      } else {
        const cat = qOutEv > 0 ? CAT.OUT_EV : CAT.OUT_NE;
        normalPrice = singleSetPrice(cat, qOut);
        ruleLabel = `${cat} ${qOut}병`;
        steps.push({ label: ruleLabel, value: fmt(normalPrice) });
      }
    }
  }

  const liquidPrice = normalPrice + exclPrice;

  // ── 기기 가격 ──────────────────────────────────────────
  const qualifyQty  = qTotal;
  const discountMax = linkedDiscountMax(qualifyQty);
  let devicePrice = 0, deviceDiscount = 0, fixedDevicePrice = 0;

  if (devLinked.length > 0) {
    let discRemain = discountMax;
    const totalLinkedQty = devLinked.reduce((s, c) => s + c.qty, 0);
    for (const d of devLinked) {
      const discQty = Math.min(d.qty, discRemain);
      const normQty = d.qty - discQty;
      const dp = safeDevicePrice(d);
      devicePrice    += discQty * dp + normQty * d.normalPrice;
      deviceDiscount += discQty * (d.normalPrice - dp);
      discRemain -= discQty;
    }
    steps.push({ label: `연동할인 기기 ${totalLinkedQty}대`, value: fmt(devicePrice) });
    if (deviceDiscount > 0)
      steps.push({ label: '└ 연동 할인', value: `-${fmt(deviceDiscount)}` });
  }

  if (devFixed.length > 0) {
    const totalFixedQty = devFixed.reduce((s, c) => s + c.qty, 0);
    fixedDevicePrice = devFixed.reduce((s, d) => s + d.qty * d.normalPrice, 0);
    devicePrice += fixedDevicePrice;
    steps.push({ label: `단일가 기기 ${totalFixedQty}대`, value: fmt(fixedDevicePrice) });
  }

  // ── 코일 + 악세사리 ────────────────────────────────────
  const othersPrice = others.reduce((s, c) => s + c.qty * c.normalPrice, 0);
  if (othersPrice > 0) steps.push({ label: '코일 / 악세사리', value: fmt(othersPrice) });

  const subtotal = liquidPrice + devicePrice + othersPrice;
  steps.push({ label: '합계', value: fmt(subtotal) });

  const lineAmounts = buildLineAmounts(cartItems, qualifyQty, discountMax, qTotal, {
    qInEv, qInNe, qOutEv, qOutNe, qIn, qOut, ruleLabel,
  });

  return {
    liquidPrice, devicePrice, deviceDiscount, fixedDevicePrice,
    othersPrice, subtotal, qualifyQty, discountMax, ruleLabel, steps, lineAmounts,
    qInEv, qInNe, qOutEv, qOutNe, qExcl, qNormal, qTotal,
    hasHighPod: cartItems.some(c => HIGH_POD_ALL.has(c.category)),
    highPodQty: sumQtySet(cartItems, HIGH_POD_ALL),
    devQty: cartItems.filter(c => DEVICE_ALL.has(c.category)).reduce((s,c)=>s+c.qty,0),
  };
}

function buildLineAmounts(cartItems, qualifyQty, discountMax, qTotal, ctx) {
  const map = new Map();
  const r   = unitKey(qTotal);
  let discRemain = discountMax;

  for (const c of cartItems) {
    const cat = c.category;

    if (DEVICE_FIXED.has(cat)) {
      map.set(c.id, c.qty * c.normalPrice);
      continue;
    }
    if (DEVICE_LINKED.has(cat)) {
      const discQty = Math.min(c.qty, discRemain);
      map.set(c.id, discQty * safeDevicePrice(c) + (c.qty - discQty) * c.normalPrice);
      discRemain -= discQty;
      continue;
    }
    if (!LIQUID_ALL.has(cat)) {
      map.set(c.id, c.qty * c.normalPrice);
      continue;
    }

    // 할인제외: 정상가 그대로
    if (LIQUID_EXCL.has(cat)) {
      map.set(c.id, c.qty * c.normalPrice);
      continue;
    }

    // 일반 액상: 규칙에 따라
    if (ctx.ruleLabel.includes('기준가+추가금')) {
      if (cat === CAT.IN_EV || cat === CAT.OUT_EV) {
        const evCat  = cat;
        const total  = cat === CAT.IN_EV ? ctx.qIn : ctx.qOut;
        const neQty  = cat === CAT.IN_EV ? ctx.qInNe : ctx.qOutNe;
        const base   = singleSetPrice(evCat, total);
        const evBase = base - neQty * MIX_EXTRA;
        const evQty  = total - neQty;
        map.set(c.id, evQty > 0 ? Math.round(evBase / evQty * c.qty) : 0);
      } else {
        map.set(c.id, MIX_EXTRA * c.qty);
      }
    } else if (ctx.ruleLabel.includes('낱개단가')) {
      map.set(c.id, (UNIT[cat]?.[r] ?? c.normalPrice) * c.qty);
    } else if (ctx.ruleLabel.includes('정상가 합산')) {
      map.set(c.id, (SET_PRICE[cat]?.[1] ?? c.normalPrice) * c.qty);
    } else {
      map.set(c.id, singleSetPrice(cat, c.qty));
    }
  }
  return map;
}
