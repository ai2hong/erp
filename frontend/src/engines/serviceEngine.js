/**
 * serviceEngine.js — VapeERP 서비스 계산 엔진 v6
 *
 * ── 서비스 선택 구조 ────────────────────────────────────
 * 서비스 포인트 N개 발생 시:
 *   3의 배수 단위: 묶음(SET3)
 *     묶음1 — 코일·팟·악세사리 분류에서 각각 1개씩 총 3개 개별 선택
 *     묶음2 — 입호흡 이벤트 분류에서 1병 선택
 *   나머지(REMAIN):
 *     묶음1에서만 각각 1개씩 N개 개별 선택
 *
 * ── 검색 카테고리 ──────────────────────────────────────
 * 묶음1 대상 분류: 입호흡 코일 / 입호흡 코일(고가) / 폐호흡 코일 / 폐호흡 코일(고가) / 악세사리
 * 묶음2 대상 분류: 입호흡 이벤트
 *
 * ── 용어 정의 ──────────────────────────────────────────
 * 기존 "팟1개", "베이프독1병" 같은 상품명/브랜드명 사용 금지
 * → 분류명 기준으로 표기
 */

export const SVC_CAT_COIL_ACC = [
  '입호흡 코일',
  '입호흡 코일(고가)',
  '폐호흡 코일',
  '폐호흡 코일(고가)',
  '악세사리',
];
export const SVC_CAT_EVENT = ['입호흡 이벤트'];


/**
 * calcService(priceResult, channel, svcEligible)
 *
 * returns: Array<ServiceItem>
 *
 * ServiceItem: {
 *   kind:      string,
 *   qty:       number,          // 총 서비스 포인트 수
 *   bundles:   Bundle[],
 *   note:      string,
 *   earnBlock: boolean,
 * }
 *
 * Bundle: {
 *   bundleType:    'SET3' | 'REMAIN',
 *   bundleIndex:   number,        // 묶음 순번 (1부터)
 *   slots:         Slot[],        // 개별 선택 슬롯 목록
 *   canChooseSet2: boolean,       // 묶음2(입호흡 이벤트) 선택 가능 여부
 *   chosenGroup:   'set1'|'set2'|null,  // 묶음1 or 묶음2 선택 여부
 * }
 *
 * Slot: {
 *   slotIndex:       number,      // 슬롯 순번 (1부터)
 *   categories:      string[],    // 검색 대상 분류 목록
 *   selectedProduct: null | { id, name, category, normalPrice },
 *   qty:             1,           // 슬롯당 항상 1개
 * }
 *
 * 묶음2 선택 시: slots = [{ categories: SVC_CAT_EVENT, qty: 1 }] 1개
 * 묶음1 선택 시: slots = [{ categories: SVC_CAT_COIL_ACC }] × 3개 (각각 개별 선택)
 */
export function calcService(priceResult, channel, svcEligible) {
  const { hasHighPod, highPodQty, qTotal, devQty } = priceResult;
  const services = [];
  if (!svcEligible) return services;

  // ── 우선순위 1: 고가팟 특수 서비스 ─────────────────────
  if (hasHighPod) {
    const svcQty = channel === '매장'
      ? highPodQty
      : Math.floor(highPodQty * 2 / 3);

    services.push({
      kind: '고가팟특수서비스',
      qty:  svcQty,
      bundles: svcQty > 0 ? [makeRemainBundle(1, svcQty)] : [],
      note: channel === '매장'
        ? `매장: ${highPodQty}개 구매 → 코일·팟·악세사리 분류 ${svcQty}개 선택`
        : `${channel}: floor(${highPodQty}×2/3) = ${svcQty}개 선택`,
      earnBlock: true,
    });
    return services;
  }

  // ── 우선순위 2: 기기 단독 증정 ──────────────────────────
  if (devQty > 0 && qTotal === 0) {
    services.push({
      kind: '기기단독증정',
      qty:  1,
      bundles: [{
        bundleType:    'REMAIN',
        bundleIndex:   1,
        canChooseSet2: false,
        chosenGroup:   null,
        slots: [makeSlot(1, SVC_CAT_EVENT)],
      }],
      note:      '입호흡 이벤트 분류 1병. 다른 분류 변경 불가',
      earnBlock: false,
    });
    return services;
  }

  // ── 우선순위 3: 기본 액상 서비스 ────────────────────────
  if (qTotal >= 1) {
    const sets3  = Math.floor(qTotal / 3);
    const remain = qTotal % 3;
    const bundles = [];

    // 3개 단위 묶음
    for (let i = 0; i < sets3; i++) {
      bundles.push({
        bundleType:    'SET3',
        bundleIndex:   i + 1,
        canChooseSet2: true,
        chosenGroup:   null,  // null = 선택 안함 (디폴트)
        // 묶음1 선택 시 slots 3개, 묶음2 선택 시 slots 1개 (UI에서 chosenGroup 변경 시 재생성)
        slots: [],  // 디폴트: 선택 안함이므로 빈 배열
      });
    }

    // 나머지
    if (remain > 0) {
      bundles.push(makeRemainBundle(sets3 + 1, remain));
    }

    const noteParts = [];
    if (sets3 > 0) {
      noteParts.push(
        `3개 단위 묶음 ${sets3}개` +
        ` (각 묶음: 코일·팟·악세사리 3개 개별선택 또는 입호흡 이벤트 1병 선택)`
      );
    }
    if (remain > 0) {
      noteParts.push(`코일·팟·악세사리 분류에서 ${remain}개 개별 선택`);
    }

    services.push({
      kind:     '기본액상서비스',
      qty:      qTotal,
      bundles,
      note:     `총 ${qTotal}병 → ` + noteParts.join(' + '),
      earnBlock: false,
    });
  }

  return services;
}


// ── 내부 헬퍼 ──────────────────────────────────────────

/** 나머지 묶음 생성 (묶음1에서만, N개 개별 슬롯) */
function makeRemainBundle(bundleIndex, qty) {
  return {
    bundleType:    'REMAIN',
    bundleIndex,
    canChooseSet2: false,
    chosenGroup:   'set1',  // REMAIN은 항상 묶음1
    slots: Array.from({ length: qty }, (_, i) => makeSlot(i + 1, SVC_CAT_COIL_ACC)),
  };
}

/** 개별 선택 슬롯 1개 */
function makeSlot(slotIndex, categories) {
  return {
    slotIndex,
    categories,          // 검색 대상 분류 목록
    selectedProduct: null,  // 검색 후 선택: { id, name, category, normalPrice }
    qty: 1,
  };
}


/**
 * UI 헬퍼: 묶음에서 그룹 선택 시 slots 재생성
 * chosenGroup: 'set1' → 슬롯 3개 (SVC_CAT_COIL_ACC 각 1개씩)
 *              'set2' → 슬롯 1개 (SVC_CAT_EVENT)
 *              null   → 빈 배열 (선택 안함)
 */
export function applyGroupChoice(bundle, chosenGroup) {
  if (bundle.bundleType !== 'SET3') return bundle;
  const slots = chosenGroup === 'set1'
    ? [makeSlot(1, SVC_CAT_COIL_ACC), makeSlot(2, SVC_CAT_COIL_ACC), makeSlot(3, SVC_CAT_COIL_ACC)]
    : chosenGroup === 'set2'
      ? [makeSlot(1, SVC_CAT_EVENT)]
      : [];
  return { ...bundle, chosenGroup, slots };
}
