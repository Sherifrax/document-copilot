import type { ReactNode } from 'react'

type AuthLayoutProps = {
  title: string
  description: string
  children: ReactNode
}

export function AuthLayout({ title, description, children }: AuthLayoutProps) {
  return (
    <main className="grid min-h-svh place-items-center bg-muted/40 px-4 py-12">
      <section className="w-full max-w-sm rounded-2xl border bg-card p-7 text-card-foreground shadow-sm">
        <div className="mb-7">
          <p className="mb-2 text-sm font-medium text-muted-foreground">Document Copilot</p>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{description}</p>
        </div>
        {children}
      </section>
    </main>
  )
}
