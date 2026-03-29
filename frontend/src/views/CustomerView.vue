<template>
  <div class="page">

    <!-- ── 좌측: 검색 패널 ── -->
    <div class="sp">
      <div class="sp-head">
        <input v-model="q" class="si" placeholder="이름 또는 전화번호 뒷자리…"
          @input="onSearch" @keydown.enter="onSearch" @keydown.esc="q='';results=[]" />
        <button class="btn pr sm" @click="openRegModal">+ 등록</button>
      </div>

      <div class="sp-count">
        {{ searching ? '로딩 중…' : (q ? `검색결과 ${results.length}명` : `전체 ${results.length}명`) }}
      </div>

      <div class="sp-list">
        <div v-for="c in results" :key="c.id"
          class="si-item" :class="{ on: customer?.id === c.id }"
          @click="selectCustomer(c)">
          <div class="si-av" :style="{ background: avatarColor(c.id) }">{{ c.name[0] }}</div>
          <div class="si-body">
            <div class="si-name">{{ c.name }}</div>
            <div class="si-phones">
              <span :class="{ 'si-primary': c.default_phone === 1 }">{{ c.phone }}</span>
              <span v-if="c.phone2"> · </span>
              <span v-if="c.phone2" :class="{ 'si-primary': c.default_phone === 2 }">{{ c.phone2 }}</span>
            </div>
          </div>
          <div class="si-mil mono">{{ (c.mileage_balance ?? 0).toLocaleString() }}P</div>
        </div>
      </div>
    </div>

    <!-- ── 우측: 상세 영역 ── -->
    <div v-if="!customer" class="detail-empty">
      <div class="de-icon">◉</div>
      <div class="de-text">좌측에서 회원을 검색하세요</div>
    </div>

    <template v-else>
      <!-- ── 프로필 카드 ── -->
      <div class="pc">
        <!-- 아바타 + 이름 -->
        <div class="pc-top">
          <div class="pc-av" :style="{ background: avatarColor(customer.id) }">{{ customer.name[0] }}</div>
          <div class="pc-name">{{ customer.name }}</div>
          <div class="pc-joined">가입 {{ fmtDate(customer.created_at) }}</div>
        </div>

        <!-- 방문 통계 -->
        <div class="pc-stats">
          <div class="pc-stat">
            <div class="ps-v mono">{{ customer.visit_count ?? 0 }}</div>
            <div class="ps-k">누적방문</div>
          </div>
          <div class="ps-sep"></div>
          <div class="pc-stat">
            <div class="ps-v mono" :style="daysSince !== null ? '' : 'color:var(--tx3)'">
              {{ daysSince !== null ? daysSince + '일전' : '—' }}
            </div>
            <div class="ps-k">최근방문</div>
          </div>
        </div>

        <!-- 총 구매액 -->
        <div class="pc-total">
          <span class="pt-v mono">{{ (customer.total_purchase ?? 0).toLocaleString() }}원</span>
          <span class="pt-k">총 구매액</span>
        </div>

        <!-- 적립금 카드 -->
        <div class="pc-mile-card">
          <div class="pmc-label">적립금 잔액</div>
          <div class="pmc-balance mono">{{ (customer.mileage_balance ?? 0).toLocaleString() }}원</div>
          <div class="pmc-sub">
            <span>총 적립 <b class="mono">{{ totalEarned.toLocaleString() }}원</b></span>
            <span>사용 <b class="mono">{{ totalUsed.toLocaleString() }}원</b></span>
          </div>
        </div>

        <!-- 액션 버튼 -->
        <div class="pc-actions">
          <router-link :to="`/sale`" class="btn ac w100">+ 판매</router-link>
          <button class="btn w100" @click="showMileAdj=true">적립금 조정</button>
        </div>

        <div class="pc-divider"></div>

        <!-- 휴대폰 번호 -->
        <div class="pc-section">
          <div class="pcs-hd">
            <span>휴대폰 번호</span>
            <button class="ic-btn" @click="editMode.phone=!editMode.phone" title="수정">✎</button>
          </div>
          <template v-if="!editMode.phone">
            <div v-for="(ph, idx) in phonePairs" :key="idx" class="ph-row">
              <span class="ph-lbl">{{ ph.label }}</span>
              <span class="mono ph-num" :class="{ 'ph-primary': ph.isPrimary }">{{ ph.value || '없음' }}</span>
              <button v-if="ph.value" class="star-btn" :class="{ active: ph.isPrimary }"
                @click="setDefaultPhone(idx+1)">{{ ph.isPrimary ? '★' : '☆' }}</button>
            </div>
          </template>
          <div v-else class="pc-edit-form">
            <div class="ef-field"><label>전화번호 1</label><input :value="phoneForm.phone" class="inp" placeholder="010-0000-0000" @input="autoPhone($event, v => phoneForm.phone = v)" /></div>
            <div class="ef-field"><label>전화번호 2</label><input :value="phoneForm.phone2" class="inp" placeholder="선택" @input="autoPhone($event, v => phoneForm.phone2 = v)" /></div>
            <div v-if="saveErr.phone" class="ef-err">{{ saveErr.phone }}</div>
            <div class="ef-actions">
              <button class="btn xs" @click="editMode.phone=false">취소</button>
              <button class="btn pr xs" @click="savePhone">저장</button>
            </div>
          </div>
        </div>

        <!-- 배송 주소 -->
        <div class="pc-section">
          <div class="pcs-hd">
            <span>배송 주소</span>
            <button v-if="!customer.address || !customer.address2" class="ic-btn-txt" @click="openAddAddr">+ 추가</button>
          </div>
          <template v-if="!editMode.addr">
            <div v-if="customer.address" class="addr-card">
              <div class="ac-top">
                <span v-if="customer.default_address===1 || !customer.default_address" class="badge-def">기본배송지</span>
                <button v-else class="badge-set" @click="setDefaultAddr(1)">기본으로</button>
                <button class="ic-btn" @click="startEditAddr(1)">✎</button>
                <button class="ic-btn danger" @click="clearAddr(1)">✕</button>
              </div>
              <div class="ac-text">{{ customer.address }}</div>
            </div>
            <div v-if="customer.address2" class="addr-card">
              <div class="ac-top">
                <span v-if="customer.default_address===2" class="badge-def">기본배송지</span>
                <button v-else class="badge-set" @click="setDefaultAddr(2)">기본으로</button>
                <button class="ic-btn" @click="startEditAddr(2)">✎</button>
                <button class="ic-btn danger" @click="clearAddr(2)">✕</button>
              </div>
              <div class="ac-text">{{ customer.address2 }}</div>
            </div>
            <div v-if="!customer.address && !customer.address2" class="pc-empty">주소 없음</div>
          </template>
          <div v-else class="pc-edit-form">
            <div class="ef-field"><label>주소</label><input v-model="addrEditVal" class="inp" /></div>
            <div class="ef-actions">
              <button class="btn xs" @click="editMode.addr=false">취소</button>
              <button class="btn pr xs" @click="saveAddr">저장</button>
            </div>
          </div>
          <!-- 주소 추가 폼 -->
          <div v-if="showAddAddrForm" class="pc-edit-form" style="margin-top:8px">
            <div class="ef-field"><label>{{ !customer.address ? '주소 1' : '주소 2' }}</label><input v-model="newAddrVal" class="inp" placeholder="새 주소 입력" /></div>
            <div class="ef-actions">
              <button class="btn xs" @click="showAddAddrForm=false;newAddrVal=''">취소</button>
              <button class="btn pr xs" @click="saveNewAddr">추가</button>
            </div>
          </div>
        </div>

        <!-- 직원 메모 -->
        <div class="pc-section">
          <div class="pcs-hd">
            <span>직원 메모</span>
            <button class="ic-btn" @click="editMode.memo=!editMode.memo">✎</button>
          </div>
          <div v-if="!editMode.memo" class="pc-memo">{{ customer.staff_memo || '메모 없음' }}</div>
          <div v-else class="pc-edit-form">
            <textarea v-model="memoForm" class="inp" rows="3" />
            <div class="ef-actions">
              <button class="btn xs" @click="editMode.memo=false">취소</button>
              <button class="btn pr xs" @click="saveMemo">저장</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 콘텐츠 영역 ── -->
      <div class="ca">
        <!-- 탭 바 -->
        <div class="tab-bar">
          <button v-for="t in tabs" :key="t.key"
            class="tab" :class="{ on: tab === t.key }"
            @click="switchTab(t.key)">
            {{ t.label }}
            <span v-if="t.cnt" class="tab-badge">{{ t.cnt }}</span>
          </button>
        </div>

        <!-- ── 구매 이력 ── -->
        <div v-if="tab==='tx'" class="tab-body tab-scroll">

          <!-- 거래 내역 -->
          <div class="sec-hd">
            <span class="sec-title">전체 구매 이력</span>
            <span class="sec-count mono">총 {{ txList.length }}건</span>
          </div>
          <div v-if="loadingTx" class="empty">로딩 중…</div>
          <template v-else>
            <table class="tw">
              <thead>
                <tr>
                  <th>거래번호</th><th>일시</th><th>내용</th>
                  <th>결제</th><th class="num">금액</th><th class="num">적립</th><th>상태</th><th>담당</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!txVisible.length"><td colspan="8" class="empty">거래 내역 없음</td></tr>
                <tr v-for="t in txVisible" :key="t.id" class="clickable-row" @click="openTxDetail(t.id)">
                  <td class="mono" style="font-size:10px;white-space:nowrap">{{ t.tx_number }}</td>
                  <td class="mono" style="font-size:10px;white-space:nowrap">{{ fmtDt(t.created_at) }}</td>
                  <td class="summary-cell">{{ t.summary || '—' }}</td>
                  <td><span class="tag" :class="payClass(t.payment_nature)">{{ payLabel(t.payment_nature) }}</span></td>
                  <td class="num mono">{{ (t.total_amount ?? 0).toLocaleString() }}</td>
                  <td class="num mono" style="color:var(--gr)">
                    {{ t.mileage_earned > 0 ? '+'+t.mileage_earned.toLocaleString() : '0' }}
                  </td>
                  <td><span class="tag" :class="colorClass(t.tx_color)">{{ txLabel(t.tx_color) }}</span></td>
                  <td style="font-size:11px;color:var(--tx2)">{{ t.staff_name || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="txList.length > txShowCount" class="more-btn-wrap">
              <button class="more-btn" @click="txShowCount += 10">
                +{{ txList.length - txShowCount }}건 더보기
              </button>
            </div>
          </template>

          <!-- 기기 구매 이력 -->
          <div class="sec-hd" style="margin-top:48px">
            <span class="sec-title">구매한 기기 이력</span>
            <span class="sec-count mono" style="color:var(--tx3)">거래 내 기기 항목만</span>
          </div>
          <div v-if="loadingDevice" class="empty">로딩 중…</div>
          <template v-else>
            <div v-if="!deviceList.length" class="empty">기기 구매 이력 없음</div>
            <template v-else>
              <div v-for="d in deviceVisible" :key="d.transaction_id+'-'+d.product_id"
                class="device-card clickable" @click="openTxDetail(d.transaction_id)">
                <div class="dc-icon">⊡</div>
                <div class="dc-body">
                  <div class="dc-name">{{ d.product_name }}</div>
                  <div class="dc-meta">
                    <span class="tag tag-ac" style="font-size:9px">{{ d.category }}</span>
                    <span>거래 #{{ d.tx_number }}</span>
                  </div>
                </div>
                <div class="dc-right">
                  <span class="dc-date mono">{{ fmtDate(d.created_at) }}</span>
                  <span class="tag tag-ok">완료</span>
                </div>
              </div>
              <div v-if="deviceList.length > devShowCount" class="more-btn-wrap">
                <button class="more-btn" @click="devShowCount += 5">
                  +{{ deviceList.length - devShowCount }}건 더보기
                </button>
              </div>
              <div v-else class="device-footer">총 {{ deviceList.length }}대 구매</div>
            </template>
          </template>
        </div>

        <!-- ── 적립금 내역 ── -->
        <div v-if="tab==='mile'" class="tab-body">
          <div class="tb-hd"><span class="tb-title">적립금 내역</span><span class="tb-count mono">총 {{ mileList.length }}건</span></div>
          <div class="table-wrap">
            <table class="tw">
              <thead><tr><th>일시</th><th>유형</th><th class="num">변동</th><th class="num">잔액</th><th>메모</th></tr></thead>
              <tbody>
                <tr v-if="loadingMile"><td colspan="5" class="empty">로딩 중…</td></tr>
                <tr v-else-if="!mileList.length"><td colspan="5" class="empty">이력 없음</td></tr>
                <tr v-for="m in mileList" :key="m.id">
                  <td class="mono" style="font-size:10px">{{ fmtDt(m.created_at) }}</td>
                  <td><span class="tag" :class="m.amount>=0?'tag-gr':'tag-re'">{{ m.mileage_type }}</span></td>
                  <td class="num mono" :style="m.amount>=0?'color:var(--gr)':'color:var(--re)'">
                    {{ m.amount >= 0 ? '+' : '' }}{{ m.amount.toLocaleString() }}
                  </td>
                  <td class="num mono">{{ m.balance_after.toLocaleString() }}</td>
                  <td style="font-size:11px;color:var(--tx3)">{{ m.note || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ── A/S 내역 ── -->
        <div v-if="tab==='as'" class="tab-body">
          <div class="tb-hd"><span class="tb-title">A/S 내역</span></div>
          <div class="table-wrap">
            <table class="tw">
              <thead><tr><th>접수일</th><th>증상</th><th>진단</th><th>처리</th><th>상태</th></tr></thead>
              <tbody>
                <tr v-if="loadingAs"><td colspan="5" class="empty">로딩 중…</td></tr>
                <tr v-else-if="!asList.length"><td colspan="5" class="empty">A/S 내역 없음</td></tr>
                <tr v-for="a in asList" :key="a.id">
                  <td class="mono" style="font-size:10px">{{ fmtDt(a.created_at) }}</td>
                  <td style="max-width:180px;white-space:pre-wrap;font-size:11px">{{ a.symptom }}</td>
                  <td style="max-width:180px;white-space:pre-wrap;font-size:11px;color:var(--tx2)">{{ a.diagnosis || '—' }}</td>
                  <td style="font-size:11px;color:var(--tx2)">{{ a.resolution || '—' }}</td>
                  <td><span class="tag tag-ac">{{ a.status }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ── 미수령 ── -->
        <div v-if="tab==='unpaid'" class="tab-body">
          <div class="tb-hd"><span class="tb-title">미수령</span></div>
          <div class="table-wrap">
            <table class="tw">
              <thead><tr><th>발생일</th><th>서비스 종류</th><th class="num">수량</th><th>처리</th><th>메모</th></tr></thead>
              <tbody>
                <tr v-if="loadingUnpaid"><td colspan="5" class="empty">로딩 중…</td></tr>
                <tr v-else-if="!unpaidList.length"><td colspan="5" class="empty good">미수령 없음 ✓</td></tr>
                <tr v-for="u in unpaidList" :key="u.id">
                  <td class="mono" style="font-size:10px">{{ fmtDt(u.created_at) }}</td>
                  <td>{{ u.service_type }}</td>
                  <td class="num mono">{{ u.quantity }}</td>
                  <td><span class="tag" :class="u.is_fulfilled?'tag-gr':'tag-re'">{{ u.is_fulfilled?'지급완료':'미지급' }}</span></td>
                  <td style="font-size:11px;color:var(--tx3)">{{ u.note || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ── 예약 주문 ── -->
        <div v-if="tab==='rsv'" class="tab-body">
          <div class="tb-hd"><span class="tb-title">예약 주문</span></div>
          <div class="table-wrap">
            <table class="tw">
              <thead><tr><th>예약일</th><th>상품</th><th class="num">수량</th><th>상태</th><th>메모</th></tr></thead>
              <tbody>
                <tr v-if="loadingRsv"><td colspan="5" class="empty">로딩 중…</td></tr>
                <tr v-else-if="!rsvList.length"><td colspan="5" class="empty">예약 내역 없음</td></tr>
                <tr v-for="r in rsvList" :key="r.id">
                  <td class="mono" style="font-size:10px">{{ fmtDt(r.created_at) }}</td>
                  <td>상품 #{{ r.product_id }}</td>
                  <td class="num mono">{{ r.quantity }}</td>
                  <td><span class="tag tag-ac">{{ r.status }}</span></td>
                  <td style="font-size:11px;color:var(--tx3)">{{ r.note || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <!-- ── 신규 등록 모달 ── -->
    <div v-if="showRegModal" class="modal-backdrop" @click.self="showRegModal=false">
      <div class="modal">
        <div class="modal-hd">신규 회원 등록</div>
        <div class="ef-field"><label>이름 *</label><input v-model="regForm.name" class="inp" /></div>
        <div class="ef-field"><label>전화번호 1 *</label><input :value="regForm.phone" class="inp" placeholder="010-0000-0000" @input="autoPhone($event, v => regForm.phone = v)" /></div>
        <div class="ef-field"><label>전화번호 2</label><input :value="regForm.phone2" class="inp" placeholder="선택" @input="autoPhone($event, v => regForm.phone2 = v)" /></div>
        <div class="ef-field"><label>주소 1</label><input v-model="regForm.address" class="inp" /></div>
        <div class="ef-field"><label>주소 2</label><input v-model="regForm.address2" class="inp" /></div>
        <div class="ef-field"><label>직원 메모</label><textarea v-model="regForm.staff_memo" class="inp" rows="2" /></div>
        <div v-if="regErr" class="ef-err">{{ regErr }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showRegModal=false">취소</button>
          <button class="btn pr" :disabled="regLoading" @click="submitReg">{{ regLoading?'등록 중…':'등록' }}</button>
        </div>
      </div>
    </div>

    <!-- ── 거래 상세 모달 ── -->
    <div v-if="showTxDetail" class="modal-backdrop" @click.self="showTxDetail=false">
      <div class="modal tx-modal">
        <div class="modal-hd">
          <span>거래 상세</span>
          <button class="ic-btn" @click="showTxDetail=false" style="margin-left:auto;font-size:16px">✕</button>
        </div>
        <div v-if="txDetailLoading" class="empty">로딩 중…</div>
        <template v-else-if="txDetail">
          <!-- 헤더 정보 -->
          <div class="txd-meta">
            <div class="txd-row"><span class="txd-k">거래번호</span><span class="mono">{{ txDetail.tx_number }}</span></div>
            <div class="txd-row"><span class="txd-k">일시</span><span class="mono">{{ fmtDt(txDetail.created_at) }}</span></div>
            <div class="txd-row"><span class="txd-k">채널</span><span>{{ txDetail.channel }}</span></div>
            <div class="txd-row"><span class="txd-k">결제</span><span class="tag" :class="payClass(txDetail.payment_nature)">{{ payLabel(txDetail.payment_nature) }}</span></div>
            <div class="txd-row"><span class="txd-k">상태</span><span class="tag" :class="colorClass(txDetail.tx_color)">{{ txLabel(txDetail.tx_color) }}</span></div>
          </div>

          <!-- 상품 목록 -->
          <div class="txd-sec-hd">상품 목록</div>
          <table class="tw">
            <thead><tr><th>상품명</th><th class="num">수량</th><th class="num">단가</th><th class="num">소계</th></tr></thead>
            <tbody>
              <tr v-for="(l, i) in txDetail.lines" :key="i" :style="l.is_service ? 'color:var(--tx3)' : ''">
                <td>
                  {{ l.product_name }}
                  <span v-if="l.is_service" class="tag tag-ye" style="font-size:9px;margin-left:4px">서비스</span>
                </td>
                <td class="num mono">{{ l.quantity }}</td>
                <td class="num mono">{{ l.unit_price.toLocaleString() }}</td>
                <td class="num mono">{{ l.line_total.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>

          <!-- 결제 요약 -->
          <div class="txd-summary">
            <div class="txd-sum-row"><span>상품 소계</span><span class="mono">{{ txDetail.subtotal.toLocaleString() }}원</span></div>
            <div v-if="txDetail.discount_amount > 0" class="txd-sum-row" style="color:var(--re)">
              <span>할인 <span v-if="txDetail.discount_reason" style="font-size:10px;color:var(--tx3)">({{ txDetail.discount_reason }})</span></span>
              <span class="mono">-{{ txDetail.discount_amount.toLocaleString() }}원</span>
            </div>
            <div v-if="txDetail.mileage_used > 0" class="txd-sum-row" style="color:var(--pu)">
              <span>마일리지 사용</span>
              <span class="mono">-{{ txDetail.mileage_used.toLocaleString() }}원</span>
            </div>
            <div class="txd-sum-row txd-total">
              <span>최종 결제</span>
              <span class="mono">{{ txDetail.total_amount.toLocaleString() }}원</span>
            </div>
            <div v-if="txDetail.mileage_earned > 0" class="txd-sum-row" style="color:var(--gr)">
              <span>적립금</span>
              <span class="mono">+{{ txDetail.mileage_earned.toLocaleString() }}원</span>
            </div>
          </div>

          <!-- 결제 수단 -->
          <div v-if="txDetail.payments?.length" class="txd-payments">
            <span v-for="(p, i) in txDetail.payments" :key="i" class="txd-pay-item">
              <span class="tag" :class="payClass(txDetail.payment_nature)">{{ p.method }}</span>
              <span class="mono">{{ p.amount.toLocaleString() }}원</span>
            </span>
          </div>

          <div v-if="txDetail.staff_memo" class="txd-memo">💬 {{ txDetail.staff_memo }}</div>
        </template>
      </div>
    </div>

    <!-- ── 적립금 조정 모달 ── -->
    <div v-if="showMileAdj" class="modal-backdrop" @click.self="showMileAdj=false">
      <div class="modal" style="width:320px">
        <div class="modal-hd">적립금 조정</div>
        <div class="ef-field">
          <label>변동 금액 (양수=지급, 음수=차감)</label>
          <input v-model.number="mileAdjAmount" class="inp" type="number" step="100" placeholder="예: 1000 또는 -500" />
        </div>
        <div class="ef-field"><label>사유</label><input v-model="mileAdjNote" class="inp" /></div>
        <div v-if="mileAdjErr" class="ef-err">{{ mileAdjErr }}</div>
        <div class="modal-ft">
          <button class="btn" @click="showMileAdj=false">취소</button>
          <button class="btn pr" :disabled="mileAdjLoading" @click="submitMileAdj">{{ mileAdjLoading?'처리 중…':'저장' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/api'

// ── 아바타 색상 팔레트 ─────────────────────────────────────────
const COLORS = ['#f4845f','#4ecdc4','#a78bfa','#f472b6','#60a5fa','#34d399','#fbbf24','#818cf8','#fb7185','#2dd4bf']
const avatarColor = (id) => COLORS[id % COLORS.length]

// ── 검색 ──────────────────────────────────────────────────────
const q         = ref('')
const results   = ref([])
const searching = ref(false)
const customer  = ref(null)
const tab       = ref('tx')

onMounted(loadAll)

async function loadAll() {
  searching.value = true
  try {
    const res = await api.get('/customers')
    results.value = res.data
  } catch { results.value = [] }
  finally { searching.value = false }
}

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  if (!q.value.trim()) { loadAll(); return }
  searchTimer = setTimeout(async () => {
    searching.value = true
    try {
      const res = await api.get('/customers/search', { params: { q: q.value } })
      results.value = res.data
    } catch { results.value = [] }
    finally { searching.value = false }
  }, 300)
}

async function selectCustomer(c) {
  try {
    const res = await api.get(`/customers/${c.id}`)
    customer.value = res.data
  } catch { customer.value = c }
  tab.value = 'tx'
  resetForms()
  loadTx()
  loadMile()
  loadUnpaid()
}

// ── 통계 계산 ─────────────────────────────────────────────────
const daysSince = computed(() => {
  if (!customer.value?.last_visit_at) return null
  const ms = Date.now() - new Date(customer.value.last_visit_at).getTime()
  return Math.floor(ms / (1000 * 60 * 60 * 24))
})

const phonePairs = computed(() => {
  if (!customer.value) return []
  return [
    { label: '기본', value: customer.value.phone,  isPrimary: (customer.value.default_phone ?? 1) === 1 },
    { label: '보조', value: customer.value.phone2, isPrimary: customer.value.default_phone === 2 },
  ]
})

// ── 탭 ────────────────────────────────────────────────────────
const unpaidCount = ref(0)
const rsvCount    = ref(0)

const tabs = computed(() => [
  { key: 'tx',     label: '구매 이력' },
  { key: 'mile',   label: '적립금 내역' },
  { key: 'as',     label: 'A/S 내역' },
  { key: 'unpaid', label: '미수령', cnt: unpaidCount.value || 0 },
  { key: 'rsv',    label: '예약 주문',     cnt: rsvCount.value || 0 },
])

function switchTab(key) {
  tab.value = key
  if (key === 'as')  loadAs()
  if (key === 'rsv') loadRsv()
}

// ── 구매 이력 ─────────────────────────────────────────────────
const txList      = ref([])
const txShowCount = ref(5)
const loadingTx   = ref(false)
const txVisible   = computed(() => txList.value.slice(0, txShowCount.value))

const deviceList    = ref([])
const loadingDevice = ref(false)
const devShowCount  = ref(3)
const deviceVisible = computed(() => deviceList.value.slice(0, devShowCount.value))

async function loadTx() {
  if (!customer.value) return
  loadingTx.value = true
  loadingDevice.value = true
  txShowCount.value = 5
  devShowCount.value = 3
  try {
    const [txRes, devRes] = await Promise.all([
      api.get(`/customers/${customer.value.id}/transactions`),
      api.get(`/customers/${customer.value.id}/devices`),
    ])
    txList.value     = txRes.data
    deviceList.value = devRes.data
  } catch { txList.value = []; deviceList.value = [] }
  finally { loadingTx.value = false; loadingDevice.value = false }
}

// ── 적립금 ────────────────────────────────────────────────────
const mileList    = ref([])
const loadingMile = ref(false)
const totalEarned = computed(() => mileList.value.filter(m => m.amount > 0).reduce((s, m) => s + m.amount, 0))
const totalUsed   = computed(() => mileList.value.filter(m => m.amount < 0).reduce((s, m) => s + Math.abs(m.amount), 0))

async function loadMile() {
  if (!customer.value) return
  loadingMile.value = true
  try {
    const res = await api.get(`/customers/${customer.value.id}/mileage`)
    mileList.value = res.data
  } catch { mileList.value = [] }
  finally { loadingMile.value = false }
}

// ── A/S ───────────────────────────────────────────────────────
const asList    = ref([])
const loadingAs = ref(false)

async function loadAs() {
  if (!customer.value) return
  loadingAs.value = true
  try {
    const res = await api.get(`/customers/${customer.value.id}/as-cases`)
    asList.value = res.data
  } catch { asList.value = [] }
  finally { loadingAs.value = false }
}

// ── 미지급 ────────────────────────────────────────────────────
const unpaidList    = ref([])
const loadingUnpaid = ref(false)

async function loadUnpaid() {
  if (!customer.value) return
  loadingUnpaid.value = true
  try {
    const res = await api.get(`/customers/${customer.value.id}/unpaid`)
    unpaidList.value = res.data
    unpaidCount.value = res.data.filter(u => !u.is_fulfilled).length
  } catch { unpaidList.value = [] }
  finally { loadingUnpaid.value = false }
}

// ── 예약 ──────────────────────────────────────────────────────
const rsvList    = ref([])
const loadingRsv = ref(false)

async function loadRsv() {
  if (!customer.value) return
  loadingRsv.value = true
  try {
    const res = await api.get(`/customers/${customer.value.id}/reservations`)
    rsvList.value = res.data
    rsvCount.value = res.data.filter(r => r.status !== '수령완료' && r.status !== '취소').length
  } catch { rsvList.value = [] }
  finally { loadingRsv.value = false }
}

// ── 수정 폼 ───────────────────────────────────────────────────
const editMode = ref({ phone: false, addr: false, memo: false })
const saveErr  = ref({ phone: '' })
const phoneForm = ref({ phone: '', phone2: '' })
const memoForm  = ref('')
const addrEditIdx = ref(1)
const addrEditVal = ref('')
const showAddAddrForm = ref(false)
const newAddrVal = ref('')

function resetForms() {
  editMode.value = { phone: false, addr: false, memo: false }
  saveErr.value  = { phone: '' }
  showAddAddrForm.value = false
  newAddrVal.value = ''
  if (customer.value) {
    phoneForm.value = { phone: customer.value.phone || '', phone2: customer.value.phone2 || '' }
    memoForm.value  = customer.value.staff_memo || ''
  }
}

watch(customer, resetForms)

async function savePhone() {
  saveErr.value.phone = ''
  try {
    const res = await api.put(`/customers/${customer.value.id}`, {
      phone:  phoneForm.value.phone || undefined,
      phone2: phoneForm.value.phone2 || '',
    })
    customer.value = res.data
    editMode.value.phone = false
  } catch (e) { saveErr.value.phone = e.response?.data?.detail || '저장 실패' }
}

async function setDefaultPhone(n) {
  try {
    const res = await api.put(`/customers/${customer.value.id}`, { default_phone: n })
    customer.value = res.data
  } catch {}
}

function startEditAddr(idx) {
  addrEditIdx.value = idx
  addrEditVal.value = idx === 1 ? (customer.value.address || '') : (customer.value.address2 || '')
  editMode.value.addr = true
}

async function saveAddr() {
  const field = addrEditIdx.value === 1 ? 'address' : 'address2'
  try {
    const res = await api.put(`/customers/${customer.value.id}`, { [field]: addrEditVal.value })
    customer.value = res.data
    editMode.value.addr = false
  } catch (e) { alert(e.response?.data?.detail || '저장 실패') }
}

async function clearAddr(idx) {
  const field = idx === 1 ? 'address' : 'address2'
  try {
    const res = await api.put(`/customers/${customer.value.id}`, { [field]: '' })
    customer.value = res.data
  } catch {}
}

async function setDefaultAddr(n) {
  try {
    const res = await api.put(`/customers/${customer.value.id}`, { default_address: n })
    customer.value = res.data
  } catch {}
}

function openAddAddr() {
  showAddAddrForm.value = true
  newAddrVal.value = ''
}

async function saveNewAddr() {
  const field = !customer.value.address ? 'address' : 'address2'
  try {
    const res = await api.put(`/customers/${customer.value.id}`, { [field]: newAddrVal.value })
    customer.value = res.data
    showAddAddrForm.value = false
    newAddrVal.value = ''
  } catch (e) { alert(e.response?.data?.detail || '저장 실패') }
}

async function saveMemo() {
  try {
    const res = await api.put(`/customers/${customer.value.id}`, { staff_memo: memoForm.value })
    customer.value = res.data
    editMode.value.memo = false
  } catch {}
}

// ── 신규 등록 ─────────────────────────────────────────────────
const showRegModal = ref(false)
const regLoading   = ref(false)
const regErr       = ref('')
const regForm      = ref({ name:'', phone:'', phone2:'', address:'', address2:'', staff_memo:'' })

function openRegModal() {
  regErr.value = ''
  regForm.value = { name:'', phone:'', phone2:'', address:'', address2:'', staff_memo:'' }
  showRegModal.value = true
}

async function submitReg() {
  regErr.value = ''
  if (!regForm.value.name.trim() || !regForm.value.phone.trim()) {
    regErr.value = '이름과 전화번호를 입력하세요'; return
  }
  regLoading.value = true
  try {
    const res = await api.post('/customers', {
      name:       regForm.value.name,
      phone:      regForm.value.phone,
      phone2:     regForm.value.phone2 || undefined,
      address:    regForm.value.address || undefined,
      address2:   regForm.value.address2 || undefined,
      staff_memo: regForm.value.staff_memo || undefined,
    })
    showRegModal.value = false
    customer.value = res.data
    results.value  = [res.data, ...results.value.filter(c => c.id !== res.data.id)]
    tab.value = 'tx'
  } catch (e) { regErr.value = e.response?.data?.detail || '등록 실패' }
  finally { regLoading.value = false }
}

// ── 거래 상세 ────────────────────────────────────────────────
const showTxDetail   = ref(false)
const txDetail       = ref(null)
const txDetailLoading = ref(false)

async function openTxDetail(txId) {
  showTxDetail.value = true
  txDetailLoading.value = true
  txDetail.value = null
  try {
    const res = await api.get(`/transactions/${txId}`)
    txDetail.value = res.data
  } catch { showTxDetail.value = false }
  finally { txDetailLoading.value = false }
}

// ── 적립금 조정 ───────────────────────────────────────────────
const showMileAdj   = ref(false)
const mileAdjAmount = ref(0)
const mileAdjNote   = ref('')
const mileAdjErr    = ref('')
const mileAdjLoading = ref(false)

async function submitMileAdj() {
  mileAdjErr.value = ''
  if (!mileAdjAmount.value) { mileAdjErr.value = '금액을 입력하세요'; return }
  mileAdjLoading.value = true
  try {
    // 적립금 조정 API가 없으므로 직접 mileage_ledger 생성 필요
    // 현재는 PUT customers/{id} 에 mileage 조정 기능 없으므로 alert로 대체
    alert('적립금 조정 기능은 추후 구현 예정입니다')
    showMileAdj.value = false
  } catch (e) { mileAdjErr.value = e.response?.data?.detail || '실패' }
  finally { mileAdjLoading.value = false }
}

// ── 전화번호 자동 포맷 ────────────────────────────────────────
function autoPhone(e, setter) {
  const digits = e.target.value.replace(/\D/g, '').slice(0, 11)
  let fmt = digits
  if (digits.length > 7)      fmt = `${digits.slice(0,3)}-${digits.slice(3,7)}-${digits.slice(7)}`
  else if (digits.length > 3) fmt = `${digits.slice(0,3)}-${digits.slice(3)}`
  e.target.value = fmt
  setter(fmt)
}

// ── 유틸 ──────────────────────────────────────────────────────
function fmtDate(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}
function fmtDt(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${String(d.getFullYear()).slice(2)}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function payLabel(nature) {
  const map = { '현금이체': '이체', '현금이체_카드20이하': '혼합', '카드': '카드', '마일리지전액': '마일리지' }
  return map[nature] || nature || '—'
}
function payClass(nature) {
  return {
    'tag-ac': nature === '현금이체' || nature === '현금이체_카드20이하',
    'tag-pu': nature === '카드',
    'tag-ye': nature === '마일리지전액',
    'tag-gr': !nature,
  }
}
function txLabel(color) {
  if (!color || color === '정상') return '완료'
  if (color === '미지급') return '미지급'
  return color
}
function colorClass(color) {
  return {
    'tag-ok':  !color || color === '정상',
    'tag-re':  color === '환불' || color === '미지급',
    'tag-ye':  color === '단골추가' || color === '할인',
    'tag-pu':  color === '마일리지전액',
    'tag-ac':  color === '고가팟',
  }
}
</script>

<style scoped>
/* ── 전체 레이아웃 ────────────────────────────────────────── */
.page { display:flex; height:100%; overflow:hidden; font-size:13px; }

/* ── 검색 패널 ────────────────────────────────────────────── */
.sp { width:280px; flex-shrink:0; border-right:1px solid var(--bd); display:flex; flex-direction:column; background:var(--bg2); }
.sp-head { display:flex; gap:6px; padding:10px; border-bottom:1px solid var(--bd); }
.si { flex:1; min-width:0; padding:6px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg); font-size:12px; color:var(--tx); outline:none; }
.si:focus { border-color:var(--ac); }
.sp-count { padding:6px 12px; font-size:11px; color:var(--tx3); font-family:var(--mono); border-bottom:1px solid var(--bd); }
.sp-hint { padding:16px 12px; font-size:11px; color:var(--tx3); text-align:center; }
.sp-list { flex:1; overflow-y:auto; }

.si-item { display:flex; align-items:center; gap:10px; padding:10px 12px; cursor:pointer; border-bottom:1px solid var(--bd); border-left:3px solid transparent; transition:all .1s; }
.si-item:hover { background:var(--bg3); }
.si-item.on { border-left-color:var(--ac); background:#fff7f3; }
.si-av { width:34px; height:34px; border-radius:50%; color:#fff; font-size:14px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.si-body { flex:1; min-width:0; }
.si-name { font-size:13px; font-weight:600; }
.si-phones { font-size:10px; color:var(--tx3); font-family:var(--mono); margin-top:2px; }
.si-primary { color:var(--ac); font-weight:600; }
.si-mil { font-size:11px; color:var(--ac); font-weight:600; flex-shrink:0; }

/* ── 빈 상태 ──────────────────────────────────────────────── */
.detail-empty { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px; }
.de-icon { font-size:36px; color:var(--tx3); }
.de-text { font-size:13px; color:var(--tx3); }

/* ── 프로필 카드 ──────────────────────────────────────────── */
.pc { width:236px; flex-shrink:0; border-right:1px solid var(--bd); display:flex; flex-direction:column; overflow-y:auto; background:var(--bg2); }
.pc-top { padding:20px 16px 12px; text-align:center; border-bottom:1px solid var(--bd); }
.pc-av { width:56px; height:56px; border-radius:50%; color:#fff; font-size:22px; font-weight:700; display:flex; align-items:center; justify-content:center; margin:0 auto 10px; }
.pc-name { font-size:17px; font-weight:700; }
.pc-joined { font-size:10px; color:var(--tx3); font-family:var(--mono); margin-top:3px; }

.pc-stats { display:flex; align-items:stretch; border-bottom:1px solid var(--bd); }
.pc-stat { flex:1; text-align:center; padding:12px 8px; }
.ps-sep { width:1px; background:var(--bd); flex-shrink:0; }
.ps-v { font-size:18px; font-weight:700; }
.ps-k { font-size:9px; color:var(--tx3); margin-top:2px; font-family:var(--mono); text-transform:uppercase; letter-spacing:.5px; }

.pc-total { display:flex; align-items:center; justify-content:space-between; padding:10px 16px; border-bottom:1px solid var(--bd); }
.pt-v { font-size:14px; font-weight:700; }
.pt-k { font-size:10px; color:var(--tx3); font-family:var(--mono); }

.pc-mile-card { margin:12px; border-radius:8px; background:#edf4ff; border:1px solid #c8deff; color:#1a3a6b; padding:12px 14px; }
.pmc-label { font-size:10px; color:#5a7fba; font-family:var(--mono); margin-bottom:4px; }
.pmc-balance { font-size:22px; font-weight:700; margin-bottom:6px; color:#1a3a6b; }
.pmc-sub { display:flex; gap:12px; font-size:10px; color:#5a7fba; }
.pmc-sub b { font-family:var(--mono); font-weight:600; color:#2f5ea8; }

.pc-actions { display:flex; flex-direction:column; gap:6px; padding:0 12px 12px; }
.w100 { width:100%; justify-content:center; }
.btn.ac { background:var(--re); color:#fff; border-color:var(--re); }

.pc-divider { height:1px; background:var(--bd); margin:4px 0; }

/* ── 프로필 섹션 (전화/주소/메모) ────────────────────────── */
.pc-section { padding:12px 14px; border-bottom:1px solid var(--bd); }
.pcs-hd { display:flex; align-items:center; gap:6px; margin-bottom:8px; font-size:10px; font-weight:600; color:var(--tx3); font-family:var(--mono); text-transform:uppercase; letter-spacing:.5px; }
.pcs-hd span { flex:1; }
.ic-btn { background:none; border:none; cursor:pointer; color:var(--tx3); font-size:13px; padding:2px 4px; border-radius:4px; line-height:1; }
.ic-btn:hover { background:var(--bg3); color:var(--tx); }
.ic-btn.danger:hover { color:var(--re); }
.ic-btn-txt { background:none; border:none; cursor:pointer; color:var(--ac); font-size:11px; padding:0; font-family:var(--sans); }
.ic-btn-txt:hover { text-decoration:underline; }

.ph-row { display:flex; align-items:center; gap:8px; padding:5px 0; font-size:12px; }
.ph-lbl { font-size:10px; color:var(--tx3); font-family:var(--mono); width:24px; }
.ph-num { flex:1; }
.ph-primary { color:var(--ac); font-weight:600; }
.star-btn { background:none; border:none; cursor:pointer; font-size:14px; color:var(--tx3); padding:0 2px; line-height:1; }
.star-btn.active { color:#f59e0b; }
.star-btn:hover { color:#f59e0b; }

.addr-card { background:var(--bg3); border:1px solid var(--bd); border-radius:6px; padding:8px 10px; margin-bottom:6px; }
.ac-top { display:flex; align-items:center; gap:4px; margin-bottom:5px; }
.badge-def { font-size:10px; background:var(--ac); color:#fff; padding:1px 6px; border-radius:20px; font-family:var(--mono); font-weight:600; }
.badge-set { font-size:10px; color:var(--tx3); border:1px solid var(--bd2); border-radius:20px; padding:0 6px; background:none; cursor:pointer; font-family:var(--sans); }
.badge-set:hover { color:var(--ac); border-color:var(--ac); }
.ac-text { font-size:11px; color:var(--tx2); line-height:1.5; }

.pc-memo { font-size:12px; color:var(--tx2); line-height:1.6; white-space:pre-wrap; }
.pc-empty { font-size:11px; color:var(--tx3); }

.pc-edit-form { display:flex; flex-direction:column; gap:8px; }
.ef-field { display:flex; flex-direction:column; gap:3px; }
.ef-field label { font-size:10px; color:var(--tx3); }
.ef-actions { display:flex; gap:6px; justify-content:flex-end; }
.ef-err { font-size:11px; color:var(--re); }

/* ── 콘텐츠 영역 ──────────────────────────────────────────── */
.ca { flex:1; display:flex; flex-direction:column; overflow:hidden; }
.tab-bar { display:flex; border-bottom:2px solid var(--bd); flex-shrink:0; background:var(--bg); padding:0 12px; gap:2px; }
.tab { padding:9px 14px; border:none; background:transparent; cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx3); border-bottom:2px solid transparent; margin-bottom:-2px; display:flex; align-items:center; gap:5px; transition:all .1s; }
.tab:hover { color:var(--tx); }
.tab.on { color:var(--ac); border-bottom-color:var(--ac); font-weight:600; }
.tab-badge { background:var(--re); color:#fff; font-size:9px; padding:1px 5px; border-radius:20px; font-family:var(--mono); font-weight:700; }

.tab-body { flex:1; overflow:hidden; display:flex; flex-direction:column; }
.tab-scroll { overflow-y:auto; padding:16px; display:block; }

.sec-hd { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.sec-title { font-size:13px; font-weight:700; }
.sec-count { font-size:11px; color:var(--tx3); }

/* 더보기 버튼 */
.more-btn-wrap { text-align:center; padding:10px 0; }
.more-btn { background:none; border:1px solid var(--bd2); border-radius:20px; padding:5px 16px; font-size:11px; color:var(--tx2); cursor:pointer; font-family:var(--sans); transition:all .1s; }
.more-btn:hover { border-color:var(--ac); color:var(--ac); background:#fff7f4; }
.tw { width:100%; border-collapse:collapse; font-size:12px; }
.tw th { padding:7px 12px; text-align:left; font-size:10px; color:var(--tx3); font-family:var(--mono); font-weight:500; border-bottom:1px solid var(--bd); background:var(--bg2); position:sticky; top:0; }
.tw td { padding:8px 12px; border-bottom:1px solid var(--bd); vertical-align:middle; }
.tw tr:last-child td { border-bottom:none; }
.tw tr:hover td { background:var(--bg3); }
.summary-cell { max-width:240px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:var(--tx2); }
.num { text-align:right; }
.mono { font-family:var(--mono); }

/* 다른 탭 공통 (적립금/A/S/미지급/예약) */
.tb-hd { display:flex; align-items:center; gap:10px; padding:12px 16px; border-bottom:1px solid var(--bd); flex-shrink:0; }
.tb-title { font-size:13px; font-weight:700; }
.tb-count { font-size:11px; color:var(--tx3); }
.table-wrap { flex:1; overflow-y:auto; }

/* 기기 이력 카드 */
.device-card { display:flex; align-items:center; gap:14px; padding:12px 14px; border:1px solid var(--bd); border-radius:8px; margin-bottom:8px; background:var(--bg2); }
.dc-icon { width:36px; height:36px; border-radius:8px; background:var(--bg3); display:flex; align-items:center; justify-content:center; font-size:18px; color:var(--tx3); flex-shrink:0; }
.dc-body { flex:1; min-width:0; }
.dc-name { font-size:13px; font-weight:600; margin-bottom:5px; }
.dc-meta { display:flex; align-items:center; gap:8px; font-size:11px; color:var(--tx3); flex-wrap:wrap; }
.dc-right { flex-shrink:0; display:flex; flex-direction:column; align-items:flex-end; gap:5px; }
.dc-date { font-size:12px; color:var(--tx); font-family:var(--mono); }
.device-footer { text-align:center; font-size:11px; color:var(--tx3); font-family:var(--mono); padding:8px 0 0; }

/* 클릭 효과 */
.clickable { cursor:pointer; transition:all .1s; }
.clickable:hover { background:var(--bg3) !important; border-color:var(--ac) !important; }
.clickable-row { cursor:pointer; }
.clickable-row:hover td { background:var(--bg3); }

/* 거래 상세 모달 */
.tx-modal { width:560px; gap:14px; }
.txd-meta { background:var(--bg3); border-radius:var(--r); padding:12px 14px; display:flex; flex-direction:column; gap:7px; }
.txd-row { display:flex; align-items:center; gap:10px; font-size:12px; }
.txd-k { width:72px; color:var(--tx3); font-size:11px; flex-shrink:0; }
.txd-sec-hd { font-size:11px; font-weight:600; color:var(--tx3); font-family:var(--mono); text-transform:uppercase; letter-spacing:.5px; margin-top:4px; }
.txd-summary { background:var(--bg3); border-radius:var(--r); padding:12px 14px; display:flex; flex-direction:column; gap:6px; }
.txd-sum-row { display:flex; justify-content:space-between; font-size:12px; }
.txd-total { font-weight:700; font-size:14px; border-top:1px solid var(--bd); padding-top:8px; margin-top:2px; }
.txd-payments { display:flex; gap:10px; flex-wrap:wrap; }
.txd-pay-item { display:flex; align-items:center; gap:6px; background:var(--bg3); border-radius:var(--r); padding:6px 10px; font-size:12px; }
.txd-memo { font-size:12px; color:var(--tx2); background:var(--bg3); border-radius:var(--r); padding:8px 12px; }
.empty { text-align:center; color:var(--tx3); padding:32px; font-size:12px; }
.good { color:var(--gr) !important; }

/* ── 태그 ─────────────────────────────────────────────────── */
.tag { display:inline-flex; padding:1px 7px; border-radius:20px; font-size:10px; font-weight:600; font-family:var(--mono); }
.tag-ok  { background:#f1f0ec; color:#6b6b67; }
.tag-gr  { background:#d4f0e3; color:#1f8a5e; }
.tag-re  { background:#fde8e8; color:#c44b4b; }
.tag-ye  { background:#fef3d4; color:#9a6c1a; }
.tag-pu  { background:#ebe6f8; color:#6d57bb; }
.tag-ac  { background:#ddeeff; color:#2f6bbf; }

/* ── 공통 버튼 ────────────────────────────────────────────── */
.btn { display:inline-flex; align-items:center; justify-content:center; padding:6px 12px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); cursor:pointer; font-size:12px; font-family:var(--sans); color:var(--tx2); transition:all .1s; }
.btn:hover { background:var(--bg3); }
.btn.pr { background:var(--ac); color:#fff; border-color:var(--ac); }
.btn.sm { padding:4px 10px; font-size:11px; }
.btn.xs { padding:3px 8px; font-size:10px; }
.inp { padding:7px 10px; border:1px solid var(--bd2); border-radius:var(--r); background:var(--bg2); font-size:12px; font-family:var(--sans); color:var(--tx); outline:none; resize:vertical; width:100%; box-sizing:border-box; }
.inp:focus { border-color:var(--ac); }

/* ── 모달 ─────────────────────────────────────────────────── */
.modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { background:var(--bg2); border-radius:10px; padding:22px; width:380px; display:flex; flex-direction:column; gap:13px; max-height:90vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,.3); }
.modal-hd { font-size:15px; font-weight:700; }
.modal-ft { display:flex; justify-content:flex-end; gap:8px; }
</style>
