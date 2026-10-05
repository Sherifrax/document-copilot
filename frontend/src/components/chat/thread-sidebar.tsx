import { LogOut, MessageSquare, Plus } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import type { ChatThread } from '@/lib/chat'

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
}

export function ThreadSidebar({
  threads,
  isLoading,
  error,
  isCreating,
  onCreate,
  onSignOut,
}: ThreadSidebarProps) {
  return (
    <aside className="flex max-h-[35svh] min-h-0 flex-col border-b bg-card md:max-h-none md:border-r md:border-b-0">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3 md:block md:space-y-4 md:px-5 md:py-5">
        <NavLink className="flex items-center gap-2 font-semibold tracking-tight" to="/chat">
          <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
            <MessageSquare className="size-4" />
          </span>
          Document Copilot
        </NavLink>
        <div className="flex items-center gap-1 md:block">
          <Button className="md:w-full" disabled={isCreating || isLoading} onClick={onCreate}>
            <Plus data-icon="inline-start" />
            {isCreating ? 'Creating…' : 'New conversation'}
          </Button>
          <Button
            aria-label="Sign out"
            className="md:hidden"
            size="icon"
            title="Sign out"
            variant="ghost"
            onClick={onSignOut}
          >
            <LogOut />
          </Button>
        </div>
      </div>

      <nav className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden p-2 md:overflow-y-auto" aria-label="Conversations">
        {isLoading ? (
          <p className="px-3 py-4 text-sm text-muted-foreground">Loading conversations…</p>
        ) : threads.length === 0 ? (
          <p className="px-3 py-4 text-sm leading-6 text-muted-foreground">
            Your conversations will appear here.
          </p>
        ) : (
          <ul className="flex gap-1 md:block md:space-y-1">
            {threads.map((thread) => (
              <li className="min-w-56 md:min-w-0" key={thread.id}>
                <NavLink
                  className={({ isActive }) =>
                    `block rounded-lg px-3 py-2.5 text-sm transition-colors ${
                      isActive ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
                    }`
                  }
                  to={`/chat/${thread.id}`}
                >
                  <span className="block truncate font-medium">{thread.title}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    {dateFormatter.format(new Date(thread.updated_at))}
                  </span>
                </NavLink>
              </li>
            ))}
          </ul>
        )}
      </nav>

      <div className="hidden border-t p-3 md:block">
        {error && <p className="mb-2 px-2 text-xs text-destructive">{error}</p>}
        <Button className="w-full justify-start" variant="ghost" onClick={onSignOut}>
          <LogOut data-icon="inline-start" />
          Sign out
        </Button>
      </div>
      {error && <p className="px-4 pb-3 text-xs text-destructive md:hidden">{error}</p>}
    </aside>
  )
}
