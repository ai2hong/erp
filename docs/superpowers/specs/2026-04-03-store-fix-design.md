# 매장별 데이터 분리 및 매장 선택 UI 이동

## 개요

1. 각 뷰에서 `auth.staff?.store_id`를 `auth.storeId`로 교체하여 매장 전환 시 해당 매장 데이터가 로드되도록 수정
2. 매장 선택 드롭다운을 Top Bar에서 사이드바 VapeERP 로고 영역으로 이동

## 1. 매장별 데이터 분리

### 대상 파일 및 변경

| 파일 | 현재 코드 | 변경 후 |
|------|----------|---------|
| `StockView.vue:98` | `auth.staff?.store_id \|\| 1` | `auth.storeId` |
| `DashboardView.vue:108` | `auth.staff?.store_id \|\| 1` | `auth.storeId` |
| `DashboardView.vue:94` | `auth.staff?.store_id` (표시용) | `auth.storeId` |
| `DayCloseView.vue:93` | `auth.staff?.store_id \|\| 1` | `auth.storeId` |
| `TxHistoryView.vue:125` | `auth.staff?.store_id \|\| 1` | `auth.storeId` |

`auth.storeId`는 이미 `currentStoreId`를 반환하는 computed로 구현되어 있음.

## 2. 매장 선택 UI 이동

### 변경 내용

**MainLayout.vue:**

- Top Bar에서 매장 드롭다운(`.store-sw`) 및 매장 라벨(`.store-label`) 제거
- 사이드바 `.sb-logo` 영역에 매장 드롭다운 배치:

```
┌──────────────────┐
│ VapeERP          │
│ 증산점 ▾ · 날짜  │  ← 매장명이 드롭다운, 클릭 시 목록 표시
├──────────────────┤
```

- 시니어 이상(canSwitchStore)일 때 매장명을 클릭 가능한 드롭다운으로 표시
- 매니저 또는 단일 매장일 때 기존처럼 텍스트만 표시
- 드롭다운 스타일은 사이드바 다크 테마에 맞게 조정
