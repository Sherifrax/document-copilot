import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { AuthField } from '@/components/auth-field'
import { AuthLayout } from '@/components/auth-layout'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'

type LocationState = { from?: { pathname?: string } }

export function LoginPage() {
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    const form = new FormData(event.currentTarget)
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: String(form.get('email')),
      password: String(form.get('password')),
    })

    setIsSubmitting(false)
    if (signInError) {
      setError(signInError.message)
      return
    }

    const state = location.state as LocationState | null
    navigate(state?.from?.pathname ?? '/', { replace: true })
  }

  return (
    <AuthLayout title="Sign in" description="Use your Driftwood email to open the filing desk.">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <AuthField label="Email" name="email" type="email" autoComplete="email" />
        <AuthField
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        New here?{' '}
        <Link className="font-medium text-foreground underline underline-offset-4" to="/signup">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  )
}
