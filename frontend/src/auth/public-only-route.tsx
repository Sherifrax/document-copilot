import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/use-auth'

export function PublicOnlyRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <main className="grid min-h-svh place-items-center">Loading…</main>
  }
  return user ? <Navigate to="/" replace /> : <Outlet />
}
