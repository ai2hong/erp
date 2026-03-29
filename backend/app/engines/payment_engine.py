"""
payment_engine.py — VapeERP 결제/적립 엔진 v4 (Python)
paymentEngine.js v4와 동일한 로직.

채널별 확정 정책:
  매장:       현금·이체·카드·마일리지 모두 가능 / 적립 가능
  배달·택배:  현금·이체만 / 카드·마일리지 불가 / 적립 없음
"""

from dataclasses import dataclass
from typing import Optional
import math


CHANNEL_POLICY = {
    '매장': {'card_ok': True,  'miles_ok': True,  'earn_ok': True},
    '배달': {'card_ok': False, 'miles_ok': False, 'earn_ok': False},
    '택배': {'card_ok': False, 'miles_ok': False, 'earn_ok': False},
}


@dataclass
class PaymentResult:
    nature:          str  = ''
    card_pct:        int  = 0
    svc_eligible:    bool = False
    earn_eligible:   bool = False
    earn_reason:     str  = ''
    earn_amt:        int  = 0
    total_to_pay:    int  = 0
    miles_final:     int  = 0
    is_balance_ok:   bool = False
    card_blocked:    bool = False
    miles_blocked:   bool = False


def calc_payment(
    cash: int, card: int, miles_used: int, miles_balance: int,
    subtotal: int, liquid_price: int, device_price: int,
    services: list, channel: str,
) -> PaymentResult:

    res = PaymentResult()
    policy = CHANNEL_POLICY.get(channel, CHANNEL_POLICY['매장'])

    # 채널별 차단
    res.card_blocked  = not policy['card_ok']  and card > 0
    res.miles_blocked = not policy['miles_ok'] and miles_used > 0

    card_final  = card  if policy['card_ok']  else 0
    max_miles   = math.floor(min(miles_balance, subtotal) / 10) * 10 if policy['miles_ok'] else 0
    miles_final = math.floor(min(miles_used, max_miles) / 10) * 10  if policy['miles_ok'] else 0
    res.miles_final = miles_final

    total_to_pay = subtotal - miles_final
    res.total_to_pay = total_to_pay

    # 카드 비중
    total_input = cash + card_final + miles_final
    card_pct    = round(card_final / total_input * 100) if total_input > 0 else 0
    res.card_pct = card_pct

    # 결제 성격
    if card_final == 0 and miles_final == 0:
        nature = '현금/이체'
    elif card_final == 0:
        nature = '마일리지 전액' if miles_final >= subtotal else '현금/이체+마일리지'
    elif card_pct <= 20:
        nature = '현금/이체 성격 (카드 20% 이하)'
    else:
        nature = '카드'
    res.nature = nature

    # 서비스 자격 (배달·택배는 카드 없으므로 항상 가능)
    res.svc_eligible = not nature.startswith('카드')

    # 결제 합산 검증
    res.is_balance_ok = abs((cash + card_final + miles_final) - subtotal) <= 10

    # 적립
    has_earn_block = any(
        s.get('earnBlock', False) if isinstance(s, dict) else getattr(s, 'earn_block', False)
        for s in services
    )
    earn_base = liquid_price + device_price

    if not policy['earn_ok']:
        res.earn_reason = f'{channel} 채널 → 적립 없음'
    elif miles_final > 0:
        res.earn_reason = '마일리지 사용 → 적립 없음'
    elif has_earn_block:
        res.earn_reason = '고가팟 특수 서비스 거래 → 적립 없음'
    elif earn_base <= 0:
        res.earn_reason = '적립 대상 품목 없음 (코일·악세사리만)'
    else:
        res.earn_eligible = True
        if nature == '카드':
            res.earn_amt    = math.floor(earn_base * 0.05 / 10) * 10
            res.earn_reason = f'카드 결제 · 액상+기기 기준 5% = {res.earn_amt:,}원'
        else:
            res.earn_amt    = math.floor(total_to_pay * 0.05 / 10) * 10
            res.earn_reason = f'현금/이체 기준 5% = {res.earn_amt:,}원'

    return res
