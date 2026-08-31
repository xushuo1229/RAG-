import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')

  function setSession({ access_token, username: name, role: r }) {
    token.value = access_token
    username.value = name
    role.value = r
    localStorage.setItem('token', access_token)
    localStorage.setItem('username', name)
    localStorage.setItem('role', r)
  }

  function clearSession() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
  }

  async function refreshMe() {
    const user = await fetchMe()
    username.value = user.username
    role.value = user.role
    localStorage.setItem('username', user.username)
    localStorage.setItem('role', user.role)
    return user
  }

  return { token, username, role, setSession, clearSession, refreshMe }
})
