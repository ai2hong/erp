<template>
  <div class="login-wrap">
    <div class="login-box">

      <!-- 로고 -->
      <div class="login-logo">Vape<span>ERP</span></div>
      <div class="login-sub">베이프독 매장 관리 시스템</div>

      <!-- 탭 -->
      <div class="tabs">
        <button :class="['tab-btn', { on: mode === 'login' }]" @click="mode = 'login'; clearMsg()">로그인</button>
        <button :class="['tab-btn', { on: mode === 'register' }]" @click="mode = 'register'; clearMsg()">회원가입 신청</button>
        <button :class="['tab-btn', { on: mode === 'forgot' }]" @click="mode = 'forgot'; clearMsg()">비밀번호 찾기</button>
      </div>

      <!-- ── 로그인 ── -->
      <div v-if="mode === 'login'">
        <div class="field">
          <label>아이디</label>
          <input v-model="form.loginId" type="text" placeholder="아이디 입력" @keydown.enter="doLogin" />
        </div>
        <div class="field">
          <label>비밀번호</label>
          <input v-model="form.password" type="password" placeholder="비밀번호 입력" @keydown.enter="doLogin" />
        </div>
        <div v-if="msg.text" :class="['msg', msg.type]">{{ msg.text }}</div>
        <button class="action-btn" :disabled="loading" @click="doLogin">
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>
      </div>

      <!-- ── 회원가입 신청 ── -->
      <div v-if="mode === 'register'">
        <div class="field">
          <label>이름</label>
          <input v-model="form.name" type="text" placeholder="실명 입력" />
        </div>
        <div class="field">
          <label>소속 매장</label>
          <select v-model="form.storeId" class="select-input">
            <option value="">매장 선택</option>
            <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="field">
          <label>아이디</label>
          <input v-model="form.loginId" type="text" placeholder="영문·숫자·밑줄 4자 이상" />
        </div>
        <div class="field">
          <label>비밀번호</label>
          <input v-model="form.password" type="password" placeholder="비밀번호 입력" />
        </div>
        <div class="field">
          <label>비밀번호 확인</label>
          <input v-model="form.passwordConfirm" type="password" placeholder="비밀번호 재입력" />
        </div>
        <div class="info-box">
          가입 신청 후 관리자 승인이 완료되면 로그인할 수 있습니다.
        </div>
        <div v-if="msg.text" :class="['msg', msg.type]">{{ msg.text }}</div>
        <button class="action-btn" :disabled="loading" @click="doRegister">
          {{ loading ? '신청 중...' : '가입 신청' }}
        </button>
      </div>

      <!-- ── 비밀번호 찾기 ── -->
      <div v-if="mode === 'forgot'">
        <div class="info-box" style="margin-bottom:16px">
          비밀번호를 잊으셨나요?<br>
          매장 관리자 또는 사장님께 비밀번호 초기화를 요청해 주세요.<br><br>
          관리자는 <strong>직원 관리</strong> 메뉴에서 초기화할 수 있습니다.
        </div>
        <div style="text-align:center;font-size:12px;color:var(--tx3)">
          관리자 문의 후 로그인 화면으로 돌아가세요.
        </div>
        <button class="action-btn secondary" @click="mode = 'login'; clearMsg()">
          로그인 화면으로
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth = useAuthStore()
const router = useRouter()

const mode = ref('login')
const loading = ref(false)
const stores = ref([])
const msg = ref({ text: '', type: '' })

const form = ref({
  name: '',
  loginId: '',
  password: '',
  passwordConfirm: '',
  storeId: '',
})

function clearMsg() {
  msg.value = { text: '', type: '' }
}

function setMsg(text, type = 'err') {
  msg.value = { text, type }
}

// 매장 목록 로드
onMounted(async () => {
  try {
    const res = await api.get('/auth/stores')
    stores.value = res.data
  } catch {
    stores.value = [
      { id: 1, name: '증산점' },
      { id: 2, name: '양산점' },
      { id: 3, name: '범어점' },
      { id: 4, name: '서면점' },
    ]
  }
})

// 로그인
async function doLogin() {
  if (!form.value.loginId || !form.value.password) {
    return setMsg('아이디와 비밀번호를 입력해주세요')
  }
  loading.value = true
  clearMsg()
  try {
    await auth.login(form.value.loginId, form.value.password)
    router.push('/dashboard')
  } catch (e) {
    setMsg(e.response?.data?.detail || '아이디 또는 비밀번호가 올바르지 않습니다')
  } finally {
    loading.value = false
  }
}

// 회원가입 신청
async function doRegister() {
  const { name, loginId, password, passwordConfirm, storeId } = form.value

  if (!name)          return setMsg('이름을 입력해주세요')
  if (!storeId)       return setMsg('소속 매장을 선택해주세요')
  if (!loginId)       return setMsg('아이디를 입력해주세요')
  if (loginId.length < 4) return setMsg('아이디는 4자 이상이어야 합니다')
  if (!password)      return setMsg('비밀번호를 입력해주세요')
  if (password.length < 6) return setMsg('비밀번호는 6자 이상이어야 합니다')
  if (password !== passwordConfirm) return setMsg('비밀번호가 일치하지 않습니다')

  loading.value = true
  clearMsg()
  try {
    await api.post('/auth/register', {
      name,
      login_id: loginId,
      password,
      store_id: storeId,
    })
    setMsg('가입 신청이 완료됐습니다. 관리자 승인 후 로그인 가능합니다.', 'ok')
    // 폼 초기화
    form.value = { name: '', loginId: '', password: '', passwordConfirm: '', storeId: '' }
  } catch (e) {
    setMsg(e.response?.data?.detail || '가입 신청 중 오류가 발생했습니다')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  background: #f5f4f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Sans KR', sans-serif;
}
.login-box {
  background: #fff;
  border: 1px solid #e2e0da;
  border-radius: 12px;
  padding: 36px 36px 32px;
  width: 360px;
}
.login-logo {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  color: #1a1a18;
  margin-bottom: 4px;
}
.login-logo span { color: #e8521a }
.login-sub {
  font-size: 12px;
  color: #a8a8a4;
  margin-bottom: 20px;
}
.tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 20px;
  background: #f5f4f0;
  border-radius: 8px;
  padding: 3px;
}
.tab-btn {
  flex: 1;
  padding: 6px 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #6b6b67;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: all .12s;
}
.tab-btn.on {
  background: #fff;
  color: #1a1a18;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.field { margin-bottom: 12px }
.field label {
  display: block;
  font-size: 11px;
  color: #6b6b67;
  margin-bottom: 4px;
  font-weight: 500;
}
.field input, .select-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d0cec8;
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 13px;
  font-family: inherit;
  color: #1a1a18;
  background: #f5f4f0;
  outline: none;
  transition: border .12s;
  appearance: none;
}
.field input:focus, .select-input:focus { border-color: #2563eb; background: #fff }
.info-box {
  font-size: 12px;
  color: #6b6b67;
  background: #f5f4f0;
  border-radius: 8px;
  padding: 10px 12px;
  line-height: 1.6;
  margin-bottom: 12px;
}
.msg {
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 6px;
  margin-bottom: 10px;
}
.msg.err { color: #dc2626; background: #fef2f2; border: 1px solid #fecaca }
.msg.ok  { color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0 }
.action-btn {
  width: 100%;
  padding: 11px;
  background: #e8521a;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: background .12s;
  margin-top: 4px;
  font-family: inherit;
}
.action-btn:hover { background: #d4481a }
.action-btn:disabled { background: #d0cec8; cursor: not-allowed }
.action-btn.secondary {
  background: transparent;
  color: #6b6b67;
  border: 1px solid #d0cec8;
}
.action-btn.secondary:hover { border-color: #e8521a; color: #e8521a; background: transparent }
</style>
