# 매장 전환 기능 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Top Bar에 매장 선택 드롭다운을 추가하여 시니어 이상 직원이 접근 가능한 매장 간 컨텍스트를 전환할 수 있게 한다.

**Architecture:** Pinia auth store에 `currentStoreId`와 `accessibleStores` 상태를 추가하고, 백엔드에 접근 가능 매장 목록 API를 만든다. MainLayout Top Bar에 드롭다운을 추가하여 매장 전환 시 대시보드로 이동한다. 직원 관리에서 사장/관리자가 시니어/총괄의 접근 매장을 지정할 수 있게 한다.

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, Pinia, vue-router

---

## 파일 구조

| 동작 | 파일 | 역할 |
|------|------|------|
| Modify | `backend/app/routers/auth.py` | 접근 가능 매장 목록 API 추가, 직원 수정 API에 매장 접근 설정 추가 |
| Modify | `frontend/src/stores/auth.js` | `currentStoreId`, `accessibleStores` 상태 + `switchStore` 액션 추가 |
| Modify | `frontend/src/layouts/MainLayout.vue` | Top Bar에 매장 선택 드롭다운 추가 |
| Modify | `frontend/src/views/StaffView.vue` | 직원 편집 시 접근 매장 체크박스 UI 추가 |

---

### Task 1: 백엔드 — 접근 가능 매장 목록 API

**Files:**
- Modify: `backend/app/routers/auth.py`

- [ ] **Step 1: 접근 가능 매장 목록 엔드포인트 추가**

`backend/app/routers/auth.py`의 `get_stores` 함수 아래에 다음 엔드포인트를 추가한다:

```python
@router.get("/stores/accessible", summary="현재 직원이 접근 가능한 매장 목록")
async def get_accessible_stores(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[Staff, RequireAny],
):
    """
    - 매니저: 소속 매장 1개
    - 시니어/총괄: StaffStoreAccess에 등록된 매장
    - 사장/관리자: 전체 활성 매장
    """
    if current.can_access_all:
        rows = await db.scalars(
            select(Store).where(Store.is_active == True).order_by(Store.id)
        )
        stores = rows.all()
    elif current.role == StaffRole.매니저:
        store = await db.scalar(select(Store).where(Store.id == current.store_id))
        stores = [store] if store else []
    else:
        store_ids = [a.store_id for a in current.store_accesses]
        if store_ids:
            rows = await db.scalars(
                select(Store).where(Store.id.in_(store_ids), Store.is_active == True).order_by(Store.id)
            )
            stores = rows.all()
        else:
            stores = []
    return [{"id": s.id, "name": s.name} for s in stores]
```

`RequireAny`는 이미 `deps.py`에서 임포트되어 있다. `Store`는 이미 `from app.models.staff import Staff, StaffRole, Store`로 임포트되어야 하므로, 기존 임포트에 `Store`가 없으면 추가한다.

- [ ] **Step 2: 서버 실행 및 API 확인**

Run: `cd /Users/ai.hong/Projects/erp/backend && python -m uvicorn app.main:app --reload --port 8000`

브라우저에서 `http://localhost:8000/docs`에 접속하여 `/stores/accessible` 엔드포인트가 표시되는지 확인.

- [ ] **Step 3: 커밋**

```bash
git add backend/app/routers/auth.py
git commit -m "feat: 접근 가능 매장 목록 API 추가"
```

---

### Task 2: 백엔드 — 직원 수정 API에 접근 매장 설정 추가

**Files:**
- Modify: `backend/app/routers/auth.py`

- [ ] **Step 1: StaffUpdateBody에 accessible_store_ids 필드 추가**

`backend/app/routers/auth.py`에서 `StaffUpdateBody` 클래스를 수정한다:

```python
class StaffUpdateBody(BaseModel):
    name:     Optional[str] = None
    role:     Optional[str] = None
    store_id: Optional[int] = None
    accessible_store_ids: Optional[list[int]] = None
```

- [ ] **Step 2: update_staff 함수에 접근 매장 저장 로직 추가**

`update_staff` 함수의 `await db.commit()` 직전에 다음 코드를 추가한다:

```python
    if body.accessible_store_ids is not None:
        # 사장 이상만 접근 매장 설정 가능
        if ROLE_LEVEL.get(current.role, 0) < ROLE_LEVEL[StaffRole.사장]:
            raise HTTPException(403, "접근 매장 설정은 사장 이상만 가능합니다.")
        # 시니어/총괄만 대상
        if target.role not in (StaffRole.시니어, StaffRole.총괄):
            raise HTTPException(400, "접근 매장 설정은 시니어/총괄 직원에게만 적용됩니다.")
        # 기존 접근 매장 삭제 후 새로 추가
        await db.execute(
            delete(StaffStoreAccess).where(StaffStoreAccess.staff_id == target.id)
        )
        for sid in body.accessible_store_ids:
            db.add(StaffStoreAccess(staff_id=target.id, store_id=sid))
```

필요한 임포트를 파일 상단에 추가한다:

```python
from sqlalchemy import delete  # 기존 select 임포트 줄에 추가
from app.models.staff import StaffStoreAccess  # 기존 Staff, StaffRole 임포트 줄에 추가
```

`ROLE_LEVEL`은 `deps.py`에서 임포트한다:

```python
from app.core.deps import ROLE_LEVEL  # 이미 임포트된 것 중에 없으면 추가
```

- [ ] **Step 3: list_staff에 접근 매장 정보 포함**

`list_staff` 함수에서 `selectinload`에 `store_accesses`를 추가하고, 응답에 접근 매장 목록을 포함한다:

기존:
```python
    rows = await db.scalars(
        select(Staff)
        .where(Staff.is_active == True)
        .options(selectinload(Staff.store))
        .order_by(Staff.name)
    )
```

변경:
```python
    rows = await db.scalars(
        select(Staff)
        .where(Staff.is_active == True)
        .options(selectinload(Staff.store), selectinload(Staff.store_accesses))
        .order_by(Staff.name)
    )
```

응답 딕셔너리에 추가:
```python
    return [
        {
            "id":       s.id,
            "name":     s.name,
            "login_id": s.login_id,
            "role":     s.role,
            "store_id": s.store_id,
            "store_name": s.store.name if s.store else None,
            "is_active": s.is_active,
            "accessible_store_ids": [a.store_id for a in s.store_accesses],
        }
        for s in rows.all()
    ]
```

- [ ] **Step 4: 커밋**

```bash
git add backend/app/routers/auth.py
git commit -m "feat: 직원 수정 시 접근 매장 설정 기능 추가"
```

---

### Task 3: 프론트엔드 — auth store에 매장 전환 상태 추가

**Files:**
- Modify: `frontend/src/stores/auth.js`

- [ ] **Step 1: auth store 전체 교체**

`frontend/src/stores/auth.js` 파일을 다음으로 교체한다:

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  function safeParse(str) {
    try { return JSON.parse(str) } catch { return null }
  }

  const token = ref(localStorage.getItem('access_token') || '')
  const staff = ref(safeParse(localStorage.getItem('staff')))
  const accessibleStores = ref([])
  const currentStoreId = ref(
    Number(localStorage.getItem('currentStoreId')) || staff.value?.store_id || null
  )

  const storeId  = computed(() => currentStoreId.value)
  const isLoggedIn = computed(() => !!token.value)
  const canSwitchStore = computed(() =>
    accessibleStores.value.length > 1
  )
  const currentStoreName = computed(() => {
    const s = accessibleStores.value.find(s => s.id === currentStoreId.value)
    return s?.name || ''
  })

  async function login(loginId, password) {
    const res = await api.post('/auth/login', { login_id: loginId, password })
    token.value = res.data.access_token
    staff.value = {
      id:       res.data.id,
      name:     res.data.name,
      role:     res.data.role,
      store_id: res.data.store_id,
      store_name: res.data.store_name,
    }
    localStorage.setItem('access_token', token.value)
    localStorage.setItem('staff', JSON.stringify(staff.value))

    // 로그인 시 소속 매장을 기본으로 설정
    currentStoreId.value = res.data.store_id
    localStorage.setItem('currentStoreId', String(res.data.store_id))

    await fetchAccessibleStores()
  }

  async function fetchAccessibleStores() {
    try {
      const res = await api.get('/stores/accessible')
      accessibleStores.value = res.data
      // currentStoreId가 접근 불가한 매장이면 첫 번째 매장으로 리셋
      if (accessibleStores.value.length > 0) {
        const valid = accessibleStores.value.some(s => s.id === currentStoreId.value)
        if (!valid) {
          currentStoreId.value = accessibleStores.value[0].id
          localStorage.setItem('currentStoreId', String(currentStoreId.value))
        }
      }
    } catch {
      accessibleStores.value = []
    }
  }

  function switchStore(storeId) {
    currentStoreId.value = storeId
    localStorage.setItem('currentStoreId', String(storeId))
    router.push('/dashboard')
  }

  function logout() {
    token.value = ''
    staff.value = null
    accessibleStores.value = []
    currentStoreId.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('staff')
    localStorage.removeItem('currentStoreId')
  }

  return {
    token, staff, storeId, isLoggedIn,
    accessibleStores, currentStoreId, canSwitchStore, currentStoreName,
    login, logout, fetchAccessibleStores, switchStore,
  }
})
```

**주요 변경사항:**
- `currentStoreId` — localStorage 연동, 매장 전환 상태
- `accessibleStores` — 접근 가능 매장 목록
- `canSwitchStore` — 2개 이상 매장 접근 가능 시 true
- `currentStoreName` — 현재 선택된 매장명
- `fetchAccessibleStores()` — API 호출로 접근 가능 매장 조회
- `switchStore(storeId)` — 매장 전환 + 대시보드 이동
- `storeId` computed가 `currentStoreId`를 참조하도록 변경 (기존 코드 호환)

- [ ] **Step 2: 커밋**

```bash
git add frontend/src/stores/auth.js
git commit -m "feat: auth store에 매장 전환 상태 및 액션 추가"
```

---

### Task 4: 프론트엔드 — MainLayout Top Bar에 매장 드롭다운 추가

**Files:**
- Modify: `frontend/src/layouts/MainLayout.vue`

- [ ] **Step 1: onMounted에서 접근 가능 매장 조회**

`<script setup>` 블록의 `onMounted`가 없으면 추가하고, 있으면 내부에 다음을 추가한다:

```javascript
const showStoreDropdown = ref(false)

onMounted(async () => {
  if (auth.isLoggedIn) {
    await auth.fetchAccessibleStores()
  }
})
```

- [ ] **Step 2: 사이드바 로고 영역의 매장명을 currentStoreName으로 변경**

기존 (line 8):
```html
<div class="sub">{{ auth.staff?.store_name || '' }} · {{ today }}</div>
```

변경:
```html
<div class="sub">{{ auth.currentStoreName || auth.staff?.store_name || '' }} · {{ today }}</div>
```

- [ ] **Step 3: Top Bar에 매장 선택 드롭다운 추가**

기존 topbar (line 105-112):
```html
<div class="topbar">
  <div class="tb-ttl">{{ pageTitle }}</div>
  <span v-if="!todayClosed" class="bx wn">일마감 미완료</span>
  <span class="tb-dt">{{ today }}</span>
  <router-link to="/sale">
    <button class="btn pr">+ 판매 등록</button>
  </router-link>
</div>
```

변경:
```html
<div class="topbar">
  <div class="tb-ttl">{{ pageTitle }}</div>
  <span v-if="!todayClosed" class="bx wn">일마감 미완료</span>

  <!-- 매장 전환 드롭다운 -->
  <div v-if="auth.canSwitchStore" class="store-sw" @click="showStoreDropdown = !showStoreDropdown" @mouseleave="showStoreDropdown = false">
    <span class="store-cur">{{ auth.currentStoreName }}</span>
    <span class="store-arrow">&#9662;</span>
    <div v-if="showStoreDropdown" class="store-dd">
      <div
        v-for="s in auth.accessibleStores" :key="s.id"
        class="store-opt" :class="{ active: s.id === auth.currentStoreId }"
        @click.stop="auth.switchStore(s.id); showStoreDropdown = false"
      >{{ s.name }}</div>
    </div>
  </div>
  <span v-else class="store-label">{{ auth.currentStoreName }}</span>

  <span class="tb-dt">{{ today }}</span>
  <router-link to="/sale">
    <button class="btn pr">+ 판매 등록</button>
  </router-link>
</div>
```

- [ ] **Step 4: 드롭다운 스타일 추가**

`<style scoped>` 블록 맨 아래에 다음 스타일을 추가한다:

```css
.store-sw {
  position:relative;cursor:pointer;display:flex;align-items:center;gap:4px;
  padding:3px 10px;border-radius:var(--r);background:var(--bg);border:1px solid var(--bd2);
  font-size:12px;font-weight:600;user-select:none
}
.store-sw:hover { border-color:var(--ac) }
.store-cur { color:var(--tx) }
.store-arrow { font-size:9px;color:var(--tx3) }
.store-dd {
  position:absolute;top:100%;left:0;margin-top:4px;min-width:140px;
  background:var(--bg2);border:1px solid var(--bd2);border-radius:var(--r);
  box-shadow:0 4px 12px rgba(0,0,0,.15);z-index:100;overflow:hidden
}
.store-opt {
  padding:7px 12px;font-size:12px;cursor:pointer;transition:background .1s
}
.store-opt:hover { background:var(--bg) }
.store-opt.active { color:var(--ac);font-weight:600 }
.store-label { font-size:12px;color:var(--tx3);font-weight:500 }
```

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/layouts/MainLayout.vue
git commit -m "feat: Top Bar에 매장 전환 드롭다운 추가"
```

---

### Task 5: 프론트엔드 — 직원 관리에서 접근 매장 설정 UI

**Files:**
- Modify: `frontend/src/views/StaffView.vue`

- [ ] **Step 1: StaffView.vue 현재 구조 파악**

먼저 `frontend/src/views/StaffView.vue`를 읽어서 현재 직원 편집 모달/폼이 어떻게 구성되어 있는지 확인한다.

- [ ] **Step 2: 매장 목록 로드**

컴포넌트 `<script setup>` 블록에 매장 목록 로드 로직을 추가한다:

```javascript
const allStores = ref([])

onMounted(async () => {
  // 기존 로직 유지...
  const storeRes = await api.get('/stores')
  allStores.value = storeRes.data
})
```

- [ ] **Step 3: 직원 편집 폼에 접근 매장 체크박스 추가**

직원 편집 모달/폼 내부에서, 대상 직원의 역할이 시니어 또는 총괄일 때만 표시되는 접근 매장 체크박스를 추가한다:

```html
<!-- 접근 매장 설정 (시니어/총괄만) -->
<div v-if="editForm.role === '시니어' || editForm.role === '총괄'" style="margin-top:12px">
  <label style="font-size:12px;font-weight:600;color:var(--tx2)">접근 매장</label>
  <div style="display:flex;gap:12px;margin-top:6px">
    <label v-for="s in allStores" :key="s.id" style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer">
      <input type="checkbox" :value="s.id" v-model="editForm.accessible_store_ids" />
      {{ s.name }}
    </label>
  </div>
</div>
```

- [ ] **Step 4: editForm에 accessible_store_ids 필드 추가**

편집 폼 초기화 부분에서 `accessible_store_ids`를 추가한다. 직원 목록에서 편집 버튼 클릭 시:

```javascript
editForm.accessible_store_ids = staffItem.accessible_store_ids || []
```

- [ ] **Step 5: 저장 시 accessible_store_ids 전송**

직원 수정 API 호출 부분에서 `accessible_store_ids`를 함께 보낸다:

```javascript
await api.put(`/admin/staff/${editForm.id}`, {
  name: editForm.name,
  role: editForm.role,
  store_id: editForm.store_id,
  accessible_store_ids: editForm.accessible_store_ids,
})
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/views/StaffView.vue
git commit -m "feat: 직원 관리에서 접근 매장 설정 UI 추가"
```

---

### Task 6: 로그인 API 응답에 store_name 포함

**Files:**
- Modify: `backend/app/routers/auth.py`

- [ ] **Step 1: 로그인 응답에 id와 store_name 추가**

`auth.py`의 로그인 엔드포인트 응답에서 `store_name`이 포함되어 있는지 확인한다. 없으면 로그인 시 staff의 store를 조회하여 응답에 포함시킨다:

```python
# 로그인 응답에 추가
store = await db.scalar(select(Store).where(Store.id == staff.store_id))
return {
    "access_token": access_token,
    "id":         staff.id,
    "name":       staff.name,
    "role":       staff.role,
    "store_id":   staff.store_id,
    "store_name": store.name if store else "",
}
```

기존 로그인 응답을 확인하고, 이미 `store_name`이 있으면 이 단계는 건너뛴다.

- [ ] **Step 2: 커밋**

```bash
git add backend/app/routers/auth.py
git commit -m "feat: 로그인 응답에 store_name 포함"
```
