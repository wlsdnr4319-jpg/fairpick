import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth'
import { refreshAccessToken } from '../api/client'
import { onAccessTokenChange, setAccessToken } from './auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false) // 앱 시작 때 로그인 복구를 끝냈는지

  // 새로고침하면 메모리의 토큰이 사라지므로 /auth/refresh 를 한 번 호출해 로그인 상태를 복구한다
  useEffect(() => {
    refreshAccessToken()
      .then((data) => {
        setUser(data.user)
        // 복구가 끝나기 전에 화면이 비로그인으로 받아 둔 데이터(북마크 여부 등)를 다시 받는다.
        // 이게 없으면 새로고침 직후 북마크한 박람회가 북마크 안 된 것처럼 보인다 (E2E 로 발견)
        queryClient.invalidateQueries()
      })
      .catch(() => setUser(null))
      .finally(() => setReady(true))
  }, [queryClient])

  // 재발급이 실패해 토큰이 지워지면 로그아웃 상태로 바꾼다
  useEffect(() => onAccessTokenChange((token) => !token && setUser(null)), [])

  const login = useCallback(
    async (email, password) => {
      const data = await authApi.login({ email, password })
      setAccessToken(data.access_token)
      setUser(data.user)
      queryClient.invalidateQueries() // 북마크 여부가 바뀐다
      return data.user
    },
    [queryClient],
  )

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setAccessToken(null)
      setUser(null)
      queryClient.clear()
    }
  }, [queryClient])

  const value = useMemo(() => ({ user, ready, login, logout, setUser }), [user, ready, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
