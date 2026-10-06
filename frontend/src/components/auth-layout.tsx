import type { ReactNode } from 'react'

import { BrandMark } from '@/components/brand-mark'

type AuthLayoutProps = {
  title: string
  description: string
  children: ReactNode
}

export function AuthLayout({ title, description, children }: AuthLayoutProps) {
  return (
    <main className="grid min-h-svh bg-background lg:grid-cols-[minmax(18rem,40%)_minmax(0,1fr)]">
      <header className="flex items-center gap-3 border-b bg-ink px-5 py-3 text-primary-foreground lg:hidden">
        <BrandMark inverted />
        <div>
          <p className="text-sm font-semibold tracking-tight">Document Copilot</p>
          <p className="text-xs text-primary-foreground/70">Driftwood Capital</p>
        </div>
      </header>

      <section className="relative hidden flex-col justify-between bg-ink px-10 py-10 text-primary-foreground lg:flex">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage:
              'linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)',
            backgroundSize: '2.25rem 2.25rem',
          }}
        />
        <div className="relative flex items-center gap-3">
          <BrandMark inverted />
          <div>
            <p className="text-sm font-semibold tracking-tight">Document Copilot</p>
            <p className="text-xs text-primary-foreground/70">Driftwood Capital</p>
          </div>
        </div>
        <div className="relative max-w-sm">
          <p className="font-serif text-[2rem] leading-snug tracking-tight">
            Read the filing. Then write the thesis.
          </p>
          <p className="mt-4 max-w-[36ch] text-sm leading-6 text-primary-foreground/75">
            Ask the corpus in plain English. Every claim comes back with the page you can check.
          </p>
        </div>
      </section>

      <section className="flex items-start justify-center px-5 py-10 sm:items-center sm:px-8 lg:px-12">
        <div className="w-full max-w-[22rem]">
          <h1 className="font-serif text-3xl tracking-tight">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
          <div className="mt-8">{children}</div>
        </div>
      </section>
    </main>
  )
}
