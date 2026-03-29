"""
price_engine.py — VapeERP 가격 계산 엔진 v6 (Python)

할인제외 처리 규칙 최종 확정:
  할인제외는 완전히 분리 계산 후 합산.
  나머지 액상은 할인제외가 없는 것처럼 세트가/낱개단가 그대로 적용.

  입이벤트2 + 입할인제외1 = 40,000 + 25,000 = 65,000  ✓
  입이벤트3 + 입할인제외1 = 50,000 + 25,000 = 75,000  ✓
"""

from dataclasses import dataclass, field
from typing import Optional
import math

CAT_IN_EV        = "입호흡 이벤트"
CAT_IN_NE        = "입호흡 일반"
CAT_IN_EX        = "입호흡 일반(할인제외)"
CAT_OUT_EV       = "폐호흡 이벤트"
CAT_OUT_NE       = "폐호흡 일반"
CAT_OUT_EX       = "폐호흡 일반(할인제외)"
CAT_IN_DEV       = "입호흡 기기"
CAT_OUT_DEV      = "폐호흡 기기"
CAT_IN_DEV_FIXED = "입호흡 기기(단일가)"
CAT_OUT_DEV_FIXED= "폐호흡 기기(단일가)"
CAT_IN_COIL_HI   = "입호흡 코일(고가)"
CAT_OUT_COIL_HI  = "폐호흡 코일(고가)"

LIQUID_ALL    = {CAT_IN_EV, CAT_IN_NE, CAT_IN_EX, CAT_OUT_EV, CAT_OUT_NE, CAT_OUT_EX}
LIQUID_EXCL   = {CAT_IN_EX, CAT_OUT_EX}
DEVICE_LINKED = {CAT_IN_DEV, CAT_OUT_DEV}
DEVICE_FIXED  = {CAT_IN_DEV_FIXED, CAT_OUT_DEV_FIXED}
DEVICE_ALL    = DEVICE_LINKED | DEVICE_FIXED
HIGH_POD      = {CAT_IN_COIL_HI, CAT_OUT_COIL_HI}
EARN_TARGET   = LIQUID_ALL | DEVICE_ALL

SET_PRICE = {
    CAT_IN_EV:  {1: 20000, 2: 40000, 3: 50000},
    CAT_IN_NE:  {1: 25000, 2: 50000, 3: 65000},
    CAT_OUT_EV: {1: 25000, 2: 45000},
    CAT_OUT_NE: {1: 30000, 2: 55000},
}
UNIT = {
    CAT_IN_EV:  {'n': 16500, 'b': 16000},
    CAT_IN_NE:  {'n': 21500, 'b': 21000},
    CAT_OUT_EV: {'n': 22500, 'b': 22000},
    CAT_OUT_NE: {'n': 27500, 'b': 27000},
}
MIX_EXTRA = 5000


@dataclass
class CartItem:
    id: int
    category: str
    name: str
    qty: int
    normal_price: int
    device_discount_price: Optional[int] = None


@dataclass
class PriceResult:
    liquid_price:      int = 0
    device_price:      int = 0
    device_discount:   int = 0
    fixed_device_price:int = 0
    others_price:      int = 0
    subtotal:          int = 0
    qualify_qty:       int = 0
    discount_max:      int = 0
    rule_label:        str = ''
    q_in_ev:  int = 0; q_in_ne:  int = 0
    q_out_ev: int = 0; q_out_ne: int = 0
    q_excl:   int = 0; q_normal: int = 0; q_total: int = 0
    has_high_pod: bool = False
    high_pod_qty: int  = 0
    dev_qty:      int  = 0


def _uk(n): return 'b' if n >= 10 else 'n'

def _sdp(item):
    d = item.device_discount_price
    return d if (d and 0 < d < item.normal_price) else item.normal_price

def _sp(cat, qty):
    t = SET_PRICE.get(cat, {})
    if qty in t: return t[qty]
    return UNIT.get(cat, {}).get(_uk(qty), 0) * qty

def _sq(items, cat):  return sum(c.qty for c in items if c.category == cat)
def _sqs(items, cs):  return sum(c.qty for c in items if c.category in cs)

def _cu(q_in_ev, q_in_ne, q_out_ev, q_out_ne, total):
    r = _uk(total)
    return (q_in_ev  * UNIT.get(CAT_IN_EV,  {}).get(r, 0)
          + q_in_ne  * UNIT.get(CAT_IN_NE,  {}).get(r, 0)
          + q_out_ev * UNIT.get(CAT_OUT_EV, {}).get(r, 0)
          + q_out_ne * UNIT.get(CAT_OUT_NE, {}).get(r, 0))

def linked_discount_max(q): return math.floor(q / 3) * 2


def calc_price(cart_items: list) -> PriceResult:
    res = PriceResult()

    liquids    = [c for c in cart_items if c.category in LIQUID_ALL]
    dev_linked = [c for c in cart_items if c.category in DEVICE_LINKED]
    dev_fixed  = [c for c in cart_items if c.category in DEVICE_FIXED]
    others     = [c for c in cart_items if c.category not in LIQUID_ALL and c.category not in DEVICE_ALL]

    excl_items = [c for c in liquids if c.category in LIQUID_EXCL]

    # ── 할인제외: 정상가×수량, 완전 분리 ────────────────────
    excl_price = sum(c.normal_price * c.qty for c in excl_items)

    q_in_ev  = _sq(cart_items, CAT_IN_EV)
    q_in_ne  = _sq(cart_items, CAT_IN_NE)
    q_out_ev = _sq(cart_items, CAT_OUT_EV)
    q_out_ne = _sq(cart_items, CAT_OUT_NE)
    q_excl   = sum(c.qty for c in excl_items)
    q_in     = q_in_ev + q_in_ne
    q_out    = q_out_ev + q_out_ne
    q_normal = q_in + q_out
    q_total  = q_normal + q_excl

    res.q_in_ev=q_in_ev; res.q_in_ne=q_in_ne
    res.q_out_ev=q_out_ev; res.q_out_ne=q_out_ne
    res.q_excl=q_excl; res.q_normal=q_normal; res.q_total=q_total

    # ── 일반 액상: 할인제외와 독립, 세트가/낱개단가 그대로 ──
    normal_price = 0
    if q_normal > 0:
        if q_in > 0 and q_out > 0:
            if q_normal <= 2:
                normal_price = (SET_PRICE.get(CAT_IN_EV,{}).get(1,0)*q_in_ev
                              + SET_PRICE.get(CAT_IN_NE,{}).get(1,0)*q_in_ne
                              + SET_PRICE.get(CAT_OUT_EV,{}).get(1,0)*q_out_ev
                              + SET_PRICE.get(CAT_OUT_NE,{}).get(1,0)*q_out_ne)
                res.rule_label = '입+폐 혼합 2병 → 정상가 합산'
            else:
                normal_price = _cu(q_in_ev,q_in_ne,q_out_ev,q_out_ne,q_normal)
                res.rule_label = f'입+폐 혼합 {q_normal}병 → 낱개단가'
        elif q_in > 0:
            if q_in_ev > 0 and q_in_ne > 0:
                if q_in <= 3:
                    base = _sp(CAT_IN_EV, q_in)
                    normal_price = base + q_in_ne * MIX_EXTRA
                    res.rule_label = f'입이벤트+일반 혼합 {q_in}병 → 기준가+추가금'
                else:
                    normal_price = _cu(q_in_ev,q_in_ne,0,0,q_in)
                    res.rule_label = f'입이벤트+일반 혼합 {q_in}병 → 낱개단가'
            else:
                cat = CAT_IN_EV if q_in_ev > 0 else CAT_IN_NE
                normal_price = _sp(cat, q_in)
                res.rule_label = f'{cat} {q_in}병'
        else:
            if q_out_ev > 0 and q_out_ne > 0:
                if q_out <= 3:
                    base = _sp(CAT_OUT_EV, q_out)
                    normal_price = base + q_out_ne * MIX_EXTRA
                    res.rule_label = f'폐이벤트+일반 혼합 {q_out}병 → 기준가+추가금'
                else:
                    normal_price = _cu(0,0,q_out_ev,q_out_ne,q_out)
                    res.rule_label = f'폐이벤트+일반 혼합 {q_out}병 → 낱개단가'
            else:
                cat = CAT_OUT_EV if q_out_ev > 0 else CAT_OUT_NE
                normal_price = _sp(cat, q_out)
                res.rule_label = f'{cat} {q_out}병'

    res.liquid_price = normal_price + excl_price

    # ── 기기 ────────────────────────────────────────────────
    qualify_qty  = q_total
    discount_max = linked_discount_max(qualify_qty)
    res.qualify_qty = qualify_qty; res.discount_max = discount_max

    if dev_linked:
        disc_remain = discount_max
        for d in dev_linked:
            dq = min(d.qty, disc_remain)
            nq = d.qty - dq
            dp = _sdp(d)
            res.device_price    += dq * dp + nq * d.normal_price
            res.device_discount += dq * (d.normal_price - dp)
            disc_remain -= dq

    if dev_fixed:
        res.fixed_device_price = sum(d.qty * d.normal_price for d in dev_fixed)
        res.device_price += res.fixed_device_price

    res.dev_qty      = _sqs(cart_items, DEVICE_ALL)
    res.others_price = sum(c.qty * c.normal_price for c in others)
    res.subtotal     = res.liquid_price + res.device_price + res.others_price
    res.has_high_pod = _sqs(cart_items, HIGH_POD) > 0
    res.high_pod_qty = _sqs(cart_items, HIGH_POD)
    return res
