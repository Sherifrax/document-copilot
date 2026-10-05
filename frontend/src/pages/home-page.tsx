import { useEffect, useState } from 'react'

import { useAuth } from '@/auth/use-auth'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

type AuthenticatedUser = { id: string; email: string }

export function HomePage() {
  const { user, signOut } = useAuth()
  const [backendUser, setBackendUser] = useState<AuthenticatedUser | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void api
      .get<AuthenticatedUser>('/auth/me')
      .then(setBackendUser)
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Request failed')
      })
  }, [])

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-4xl flex-col px-6 py-8">
      <header className="flex items-center justify-between border-b pb-5">
        <span className="font-semibold">Document Copilot</span>
        <Button variant="outline" onClick={() => void signOut()}>
          Sign out
        </Button>
      </header>
      <section className="flex flex-1 items-center justify-center py-16">
        <div className="w-full max-w-xl rounded-2xl border bg-card p-8 shadow-sm">
          <p className="text-sm font-medium text-muted-foreground">Authenticated session</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Phase 2 is connected</h1>
          <p className="mt-3 text-muted-foreground">
            Signed in as {backendUser?.email ?? user?.email}. The browser session is reaching
            FastAPI with a verified Supabase bearer token.
          </p>
          {backendUser && (
            <p className="mt-5 break-all rounded-lg bg-muted p-3 font-mono text-xs">
              User ID: {backendUser.id}
            </p>
          )}
          {error && <p className="mt-5 text-sm text-destructive">{error}</p>}
        </div>
      </section>
    </main>
  )
}
