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
