import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/auth/use-auth'

export function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <main className="grid min-h-svh place-items-center">Loading…</main>
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <Outlet />
}
