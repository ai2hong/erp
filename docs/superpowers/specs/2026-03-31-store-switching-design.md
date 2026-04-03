# 매장 전환 기능 설계

## 개요

ERP Top Bar에 매장 선택 드롭다운을 추가하여, 시니어 이상 등급의 직원이 접근 가능한 매장 간 컨텍스트를 전환할 수 있게 한다. 매장 전환 시 대시보드로 이동하며, 이후 모든 API 호출은 선택된 매장 기준으로 동작한다.

## 대상 매장

- 증산점, 양산점, 범어점 (Store 테이블에 등록된 활성 매장)

## 권한 규칙

| 역할 | 매장 전환 | 접근 가능 매장 |
|------|----------|---------------|
| 매니저 | 불가 | 소속 매장 1개만 |
| 시니어 | 가능 | StaffStoreAccess에 등록된 매장 |
| 총괄 | 가능 | StaffStoreAccess에 등록된 매장 |
| 사장 | 가능 | 전체 활성 매장 |
| 관리자 | 가능 | 전체 활성 매장 |

- 시니어/총괄의 접근 가능 매장은 직원 관리 탭에서 사장/관리자가 지정

## 백엔드

### 1. 접근 가능 매장 목록 API

```
GET /stores/accessible
```

- 현재 로그인한 직원의 역할에 따라 접근 가능한 매장 목록 반환
- 매니저: `[staff.store_id]`
- 시니어/총괄: StaffStoreAccess 테이블에서 조회
- 사장/관리자: Store 테이블에서 `is_active=True`인 전체 매장
- 응답: `[{id, name, address, phone}]`

### 2. 직원 관리 API 수정

```
PUT /staff/{id}
```

- 요청 body에 `accessible_store_ids: [int]` 필드 추가
- 사장/관리자만 수정 가능
- StaffStoreAccess 테이블을 해당 직원에 대해 전체 교체 (delete + insert)
- 시니어/총괄 역할 직원에게만 적용 가능

### 3. 매장 검증 미들웨어

- 각 API에서 `store_id` 파라미터를 받을 때, 해당 직원이 접근 가능한 매장인지 검증
- 기존 API들이 이미 store_id를 받고 있으므로, 권한 체크 로직만 추가

## 프론트엔드

### 1. Pinia auth store 수정

```javascript
// 새로 추가할 상태
currentStoreId: localStorage.getItem('currentStoreId') || staff.store_id
accessibleStores: []

// 새로 추가할 액션
async fetchAccessibleStores()  // GET /stores/accessible 호출
switchStore(storeId)           // currentStoreId 변경 + localStorage 저장 + 대시보드 이동
```

- 로그인 시 `fetchAccessibleStores()` 호출하여 목록 저장
- `currentStoreId`의 기본값은 소속 매장 (`staff.store_id`)
- 모든 API 호출에서 `auth.staff.store_id` 대신 `auth.currentStoreId` 사용

### 2. MainLayout.vue Top Bar 수정

- 매장 드롭다운 컴포넌트 추가
  - 시니어 이상(매장이 2개 이상 접근 가능)일 때만 드롭다운 표시
  - 매니저 또는 매장 1개만 접근 가능하면 매장명만 텍스트로 표시
- 현재 선택된 매장명 표시
- 클릭 시 접근 가능 매장 목록 드롭다운 노출
- 매장 선택 시:
  1. `auth.switchStore(storeId)` 호출
  2. 대시보드(`/dashboard`)로 라우터 이동

### 3. 기존 코드 변경

- `auth.staff.store_id`를 참조하는 모든 API 호출을 `auth.currentStoreId`로 교체
- 영향 범위: ProductsView, StockView, SaleView, TxHistoryView, DashboardView 등 store_id를 사용하는 모든 뷰

### 4. 직원 관리 뷰 수정

- 시니어/총괄 직원 편집 시 접근 가능 매장을 체크박스로 선택할 수 있는 UI 추가
- 사장/관리자 역할로 로그인한 경우에만 해당 설정 표시

## 매장 전환 흐름

```
1. 사용자가 Top Bar의 매장 드롭다운 클릭
2. 접근 가능한 매장 목록 표시 (현재 매장 강조)
3. 다른 매장 선택
4. currentStoreId 업데이트 + localStorage 저장
5. /dashboard로 리다이렉트
6. 대시보드가 새 store_id로 데이터 로드
```

## 범위 외 (추후 구현)

- 매장 간 재고 이동 (StoreTransfer 기능) — 별도 기획
- 매장별 매출 비교 대시보드
