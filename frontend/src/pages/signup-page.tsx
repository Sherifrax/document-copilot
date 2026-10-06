import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { AuthField } from '@/components/auth-field'
import { AuthLayout } from '@/components/auth-layout'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'

export function SignupPage() {
  const [error, setError] = useState<string | null>(null)
  const [confirmationSent, setConfirmationSent] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    const form = new FormData(event.currentTarget)
    const { data, error: signUpError } = await supabase.auth.signUp({
      email: String(form.get('email')),
      password: String(form.get('password')),
    })

    setIsSubmitting(false)
    if (signUpError) {
      setError(signUpError.message)
      return
    }
    setConfirmationSent(data.session === null)
  }

  return (
    <AuthLayout
      title="Create an account"
      description="Analysts sign in with email. Confirm the message we send before you start."
    >
      {confirmationSent ? (
        <div className="space-y-4 text-sm leading-6">
          <p>
            Check your inbox and confirm your email. After that, you can sign in and ask the
            filings.
          </p>
          <Button asChild variant="outline" className="w-full" size="lg">
            <Link to="/login">Back to sign in</Link>
          </Button>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={handleSubmit}>
          <AuthField label="Email" name="email" type="email" autoComplete="email" />
          <AuthField
            label="Password"
            name="password"
            type="password"
            autoComplete="new-password"
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button className="w-full" size="lg" disabled={isSubmitting}>
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </Button>
        </form>
      )}
      {!confirmationSent && (
        <p className="mt-6 text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link className="font-medium text-foreground underline underline-offset-4" to="/login">
            Sign in
          </Link>
        </p>
      )}
    </AuthLayout>
  )
}
