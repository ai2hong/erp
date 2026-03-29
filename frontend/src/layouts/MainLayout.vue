<template>
  <div style="display:flex;height:100vh;overflow:hidden;font-family:var(--sans);background:var(--bg);color:var(--tx);font-size:13px">

    <!-- ── 사이드바 ── -->
    <aside class="sb">
      <div class="sb-logo">
        <div class="name">Vape<span style="color:var(--ac)">ERP</span></div>
        <div class="sub">{{ auth.staff?.store_name || '' }} · {{ today }}</div>
      </div>

      <div class="sb-sec">판매</div>
      <router-link to="/dashboard" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">◈</span>대시보드
        </div>
      </router-link>
      <router-link to="/sale" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">✦</span>판매 등록
        </div>
      </router-link>

      <div class="sb-sec">고객</div>
      <router-link to="/customer" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">◉</span>회원목록
        </div>
      </router-link>
      <router-link to="/unpaid" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">◌</span>미지급 서비스
          <span v-if="badges.unpaid" class="nb">{{ badges.unpaid }}</span>
        </div>
      </router-link>
      <router-link to="/reserve" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">◎</span>예약 주문
        </div>
      </router-link>

      <div class="sb-sec">재고</div>
      <router-link to="/stock" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">▣</span>재고 현황
          <span v-if="badges.stock" class="nb">{{ badges.stock }}</span>
        </div>
      </router-link>

      <div class="sb-sec">정산</div>
      <router-link to="/dayclose" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">▦</span>일마감
        </div>
      </router-link>
      <router-link to="/approval" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">▧</span>승인 로그
          <span v-if="badges.approval" class="nb">{{ badges.approval }}</span>
        </div>
      </router-link>

      <div class="sb-sec">관리</div>
      <router-link to="/staff" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">⊞</span>직원 관리
        </div>
      </router-link>

      <router-link to="/transfers" custom v-slot="{ navigate, isActive }">
        <div class="ni" :class="{ on: isActive }" @click="navigate">
          <span class="ni-ic">⊡</span>택배 / 배달
          <span v-if="badges.transfers" class="nb">{{ badges.transfers }}</span>
        </div>
      </router-link>

      <!-- 하단 사용자 정보 -->
      <div class="sb-bot">
        <div class="av-row">
          <div class="av">{{ auth.staff?.name?.[0] || '?' }}</div>
          <div>
            <div class="av-nm">{{ auth.staff?.name || '' }}</div>
            <div class="av-rl">{{ auth.staff?.role || '' }}</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- ── 메인 영역 ── -->
    <div style="flex:1;display:flex;flex-direction:column;height:100vh;overflow:hidden;min-width:0">

      <!-- 상단 바 -->
      <div class="topbar">
        <div class="tb-ttl">{{ pageTitle }}</div>
        <span v-if="!todayClosed" class="bx wn">일마감 미완료</span>
        <span class="tb-dt">{{ today }}</span>
        <router-link to="/sale">
          <button class="btn pr">+ 판매 등록</button>
        </router-link>
      </div>

      <!-- 페이지 콘텐츠 -->
      <div style="flex:1;overflow:hidden;min-height:0">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const todayClosed = ref(false)
const badges = ref({ unpaid: 0, stock: 0, approval: 0, transfers: 0 })

const today = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
})

const PAGE_TITLES = {
  '/dashboard': '대시보드',
  '/sale':      '판매 등록',
  '/customer':  '회원목록',
  '/unpaid':    '미지급 서비스',
  '/reserve':   '예약 주문',
  '/stock':     '재고 현황',
  '/dayclose':  '일마감',
  '/approval':  '승인 로그',
  '/staff':     '직원 관리',
  '/transfers': '택배 / 배달',
}

const pageTitle = computed(() => PAGE_TITLES[route.path] || 'VapeERP')
</script>

<style scoped>
.sb {
  width:196px;background:var(--sb);display:flex;flex-direction:column;
  flex-shrink:0;height:100vh;overflow-y:auto;
}
.sb-logo { padding:14px 14px 10px;border-bottom:1px solid rgba(255,255,255,.07) }
.sb-logo .name { font-family:var(--mono);font-size:14px;font-weight:600;color:#fff }
.sub { font-size:10px;color:rgba(255,255,255,.3);font-family:var(--mono);margin-top:2px }
.sb-sec {
  padding:10px 12px 2px;font-size:9px;font-family:var(--mono);
  color:rgba(255,255,255,.25);letter-spacing:1.5px;text-transform:uppercase
}
.ni {
  display:flex;align-items:center;gap:8px;padding:7px 10px;margin:1px 8px;
  border-radius:6px;cursor:pointer;transition:all .12s;
  color:rgba(255,255,255,.45);font-size:12px;position:relative
}
.ni:hover { background:rgba(255,255,255,.06);color:rgba(255,255,255,.8) }
.ni.on { background:var(--ac);color:#fff;font-weight:500 }
.ni-ic { width:14px;text-align:center;font-size:12px;flex-shrink:0 }
.nb {
  margin-left:auto;background:rgba(220,38,38,.9);color:#fff;
  font-size:10px;font-family:var(--mono);padding:1px 5px;
  border-radius:20px;font-weight:600
}
.sb-bot { margin-top:auto;padding:10px;border-top:1px solid rgba(255,255,255,.07) }
.av-row {
  display:flex;align-items:center;gap:8px;padding:8px;
  border-radius:6px;background:rgba(255,255,255,.05)
}
.av {
  width:28px;height:28px;border-radius:50%;background:var(--ac);
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;color:#fff;flex-shrink:0
}
.av-nm { font-size:12px;color:rgba(255,255,255,.75);font-weight:500 }
.av-rl { font-size:10px;color:rgba(255,255,255,.3);font-family:var(--mono) }
.topbar {
  height:46px;background:var(--bg2);border-bottom:1px solid var(--bd);
  display:flex;align-items:center;padding:0 16px;gap:8px;flex-shrink:0
}
.tb-ttl { font-size:14px;font-weight:700 }
.tb-dt { font-family:var(--mono);font-size:11px;color:var(--tx3);margin-left:auto }
.btn { display:inline-flex;align-items:center;gap:4px;padding:5px 11px;border:1px solid var(--bd2);border-radius:var(--r);background:var(--bg2);cursor:pointer;font-size:12px;font-family:var(--sans);color:var(--tx2);transition:all .12s;text-decoration:none }
.btn.pr { background:var(--ac);color:#fff;border-color:var(--ac) }
.bx { display:inline-flex;align-items:center;padding:2px 7px;border-radius:20px;font-size:10px;font-weight:600;font-family:var(--mono) }
.bx.wn { background:#fef9c3;color:#854d0e }
</style>
