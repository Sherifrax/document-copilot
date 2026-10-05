import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/auth/protected-route'
import { PublicOnlyRoute } from '@/auth/public-only-route'
import { ChatLayout } from '@/components/chat/chat-layout'
import { ChatListPage } from '@/pages/chat-list-page'
import { ChatThreadPage } from '@/pages/chat-thread-page'
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
        <Route path="/chat" element={<ChatLayout />}>
          <Route index element={<ChatListPage />} />
          <Route path=":threadId" element={<ChatThreadPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  )
}

export default App
