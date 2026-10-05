import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/auth/protected-route'
import { PublicOnlyRoute } from '@/auth/public-only-route'
import { HomePage } from '@/pages/home-page'
import { LoginPage } from '@/pages/login-page'
import { SignupPage } from '@/pages/signup-page'

function App() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<HomePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
