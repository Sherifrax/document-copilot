import { LogOut, Plus, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { BrandMark } from '@/components/brand-mark'
import { Button } from '@/components/ui/button'
import type { ChatThread } from '@/lib/chat'
import { cn } from '@/lib/utils'

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
})

type ThreadSidebarProps = {
  threads: ChatThread[]
  isLoading: boolean
  error: string | null
  isCreating: boolean
  onCreate: () => void
  onSignOut: () => void
  onNavigate?: () => void
  onClose?: () => void
  className?: string
}

export function ThreadSidebar({
  threads,
  isLoading,
  error,
  isCreating,
  onCreate,
  onSignOut,
  onNavigate,
  onClose,
  className,
}: ThreadSidebarProps) {
  return (
    <aside className={cn('flex h-full min-h-0 flex-col bg-ink text-primary-foreground', className)}>
      <div className="border-b border-white/10 px-4 py-4 sm:px-5">
        <div className="flex items-start justify-between gap-2">
          <NavLink
            className="flex min-w-0 items-center gap-2.5 font-semibold tracking-tight"
            onClick={onNavigate}
            to="/chat"
          >
            <BrandMark inverted />
            <span className="min-w-0">
              <span className="block truncate">Document Copilot</span>
              <span className="block text-xs font-normal text-primary-foreground/65">
                Driftwood Capital
              </span>
            </span>
          </NavLink>
          {onClose && (
            <Button
              aria-label="Close conversations"
              className="shrink-0 text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
              onClick={onClose}
              size="icon"
              variant="ghost"
            >
              <X />
            </Button>
          )}
        </div>
        <Button
          className="mt-4 w-full bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/16"
          disabled={isCreating || isLoading}
          onClick={onCreate}
        >
          <Plus data-icon="inline-start" />
          {isCreating ? 'Creating…' : 'New conversation'}
        </Button>
      </div>

      <nav
        aria-label="Conversations"
        className="min-h-0 flex-1 overflow-y-auto px-2 py-3"
      >
        {isLoading ? (
          <p className="px-3 py-3 text-sm text-primary-foreground/65">Loading conversations…</p>
        ) : threads.length === 0 ? (
          <p className="px-3 py-3 text-sm leading-6 text-primary-foreground/65">
            Conversations you start will collect here.
          </p>
        ) : (
          <ul className="space-y-0.5">
            {threads.map((thread) => (
              <li key={thread.id}>
                <NavLink
                  className={({ isActive }) =>
                    cn(
                      'block rounded-md px-3 py-2.5 text-sm transition-colors',
                      isActive
                        ? 'bg-primary-foreground/12'
                        : 'hover:bg-primary-foreground/8',
                    )
                  }
                  onClick={onNavigate}
                  to={`/chat/${thread.id}`}
                >
                  <span className="block truncate font-medium">{thread.title}</span>
                  <span className="mt-0.5 block text-xs text-primary-foreground/60">
                    {dateFormatter.format(new Date(thread.updated_at))}
                  </span>
                </NavLink>
              </li>
            ))}
          </ul>
        )}
      </nav>

      <div className="border-t border-white/10 p-3">
        {error && <p className="mb-2 px-2 text-xs text-red-200">{error}</p>}
        <Button
          className="w-full justify-start text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
          variant="ghost"
          onClick={onSignOut}
        >
          <LogOut data-icon="inline-start" />
          Sign out
        </Button>
      </div>
    </aside>
  )
}
