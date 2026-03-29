import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  function safeParse(str) {
    try { return JSON.parse(str) } catch { return null }
  }

  const token = ref(localStorage.getItem('access_token') || '')
  const staff = ref(safeParse(localStorage.getItem('staff')))
  const storeId  = computed(() => staff.value?.store_id || null)
  const isLoggedIn = computed(() => !!token.value)

  async function login(loginId, password) {
    const res = await api.post('/auth/login', { login_id: loginId, password })
    token.value = res.data.access_token
    staff.value = {
      name:     res.data.name,
      role:     res.data.role,
      store_id: res.data.store_id,
    }
    localStorage.setItem('access_token', token.value)
    localStorage.setItem('staff', JSON.stringify(staff.value))
  }

  function logout() {
    token.value = ''
    staff.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('staff')
  }

  return { token, staff, storeId, isLoggedIn, login, logout }
})
